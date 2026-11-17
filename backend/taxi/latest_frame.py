"""Bounded software-only perception input seam, in the host monotonic clock domain.

No network/device driver or actuator is connected by this module. Producers and
consumers share a process; cross-process adapters must translate clocks explicitly.
"""

from dataclasses import dataclass
import math
import threading
import time


@dataclass(frozen=True)
class Frame:
    payload: bytes
    source: str
    sequence: int
    captured_at: float
    received_at: float


class LatestFrameBuffer:
    """One immutable frame, overwrite-oldest; stale/invalid input is unavailable."""

    def __init__(self, *, max_age_s=0.5, max_bytes=1_048_576, clock=time.monotonic):
        if (isinstance(max_age_s, bool) or not isinstance(max_age_s, (int, float))
                or not math.isfinite(max_age_s) or max_age_s <= 0):
            raise ValueError("max_age_s must be finite and positive")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        self.max_age_s, self.max_bytes, self.clock = max_age_s, max_bytes, clock
        self._lock = threading.Lock()
        self._frame = None
        self._sequence = -1
        self._overwritten = 0

    def publish(self, payload, *, source, sequence, captured_at):
        with self._lock:
            now = self.clock()
            valid_time = (not isinstance(captured_at, bool)
                          and isinstance(captured_at, (int, float))
                          and math.isfinite(captured_at)
                          and 0 <= now - captured_at <= self.max_age_s)
            if (type(payload) is not bytes or not 0 < len(payload) <= self.max_bytes
                    or source not in ("simulated", "recorded")
                    or type(sequence) is not int or sequence <= self._sequence
                    or sequence < 0 or not valid_time):
                self._frame = None
                raise ValueError("Invalid, stale, future or out-of-order software frame")
            if self._frame is not None:
                self._overwritten += 1
            self._frame = Frame(payload, source, sequence, captured_at, now)
            self._sequence = sequence

    def latest(self, *, consume=False):
        with self._lock:
            frame = self._frame
            if frame is None:
                return None
            age = self.clock() - frame.captured_at
            if not 0 <= age <= self.max_age_s:
                self._frame = None
                return None
            if consume:
                self._frame = None
            return frame

    @property
    def overwritten(self):
        with self._lock:
            return self._overwritten

    def reset(self):
        """Explicitly begin a new software producer session; never resume a mission."""
        with self._lock:
            self._frame = None
            self._sequence = -1
            self._overwritten = 0
