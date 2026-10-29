"""Deterministic simulation supervisor; never sends physical motor commands."""

import math
import time
import uuid
from .navigation import POINTS, route
from .configuration import load_configuration


class Conflict(ValueError):
    pass


class Supervisor:
    MAX_SPEED = 0.8  # simulation metres/second; NOT a physical vehicle limit
    STALE_AFTER = 0.5
    OBSTACLE_LIMIT = 0.6  # simulation-only threshold

    def __init__(self, store, clock=time.monotonic):
        self.store, self.clock = store, clock
        self.config = load_configuration(store)
        self.mode = "simulation"
        self.state = "READY"
        self.position = list(POINTS["A"])
        self.current_stop = "A"
        self.speed = 0.0
        self.trip = None
        self.path = []
        self.target_index = 0
        self.reason = None
        self.obstacle = False
        self.sensor_failed = False
        self.link_failed = False
        self.last_sensor = self.last_link = self.last_tick = clock()
        self.sequence = 0
        self.store.event("boot", {"mode": self.mode, "state": self.state})

    def start(self, destination, owner_id=None):
        if self.state != "READY":
            raise Conflict("Vehicle must be READY")
        if not self.current_stop:
            raise Conflict("Position is between stops; reset simulation before a new trip")
        if self.obstacle or self.sensor_failed or self.link_failed:
            raise Conflict("Clear simulated hazards before starting")
        now = self.clock()
        if now - min(self.last_sensor, self.last_link) > self.STALE_AFTER:
            raise Conflict("Waiting for fresh simulated telemetry")
        self.path = route(
            self.current_stop, destination, self.config["stops"], self.config["edges"]
        )
        self.trip = {
            "id": uuid.uuid4().hex,
            "origin": self.current_stop,
            "destination": destination,
            "status": "ACTIVE",
            "owner_id": owner_id,
        }
        self.target_index = 1
        self.state = "ACTIVE"
        self.reason = None
        self.last_tick = now
        self.store.trip(self.trip)
        self.store.event("mission_accepted", self.trip)
        return dict(self.trip)

    def stop(self, reason="operator_stop", terminal="CANCELLED", fault=False):
        # Repeated stop requests cannot clear an already-latched fault.
        latched = self.state == "FAULT"
        self.speed = 0.0
        if self.trip and self.trip["status"] == "ACTIVE":
            self.trip["status"] = terminal
            self.store.trip(self.trip)
        if not latched:
            self.state = "FAULT" if fault else "STOPPED"
            self.reason = reason
        self.store.event("stop", {"reason": self.reason, "state": self.state})

    def rearm(self):
        if self.state not in {"FAULT", "STOPPED", "COMPLETE"}:
            raise Conflict("No stopped state to rearm")
        now = self.clock()
        if (
            self.obstacle
            or self.sensor_failed
            or self.link_failed
            or now - min(self.last_sensor, self.last_link) > self.STALE_AFTER
        ):
            raise Conflict("Clear hazards and wait for fresh telemetry")
        self.state, self.reason = "READY", None
        self.store.event("rearm", {"current_stop": self.current_stop})

    def reset(self):
        if self.state == "ACTIVE":
            raise Conflict("Stop the trip before resetting the simulation")
        if self.obstacle or self.sensor_failed or self.link_failed:
            raise Conflict("Clear simulated hazards first")
        self.position, self.current_stop = list(POINTS["A"]), "A"
        self.speed, self.state, self.reason = 0.0, "READY", None
        self.path, self.trip = [], None
        self.last_sensor = self.last_link = self.last_tick = self.clock()
        self.store.event("simulation_reset", {"stop": "A"})

    def step(self):
        now = self.clock()
        dt = now - self.last_tick
        self.last_tick = now
        if not self.sensor_failed:
            self.last_sensor = now
        if not self.link_failed:
            self.last_link = now
        if self.state != "ACTIVE":
            self.speed = 0.0
            return
        reason = None
        if dt > self.STALE_AFTER or dt < 0:
            reason = "supervisor_timing_fault"
        elif self.obstacle:
            reason = "obstacle_detected"
        elif now - self.last_sensor > self.STALE_AFTER:
            reason = "sensor_stale"
        elif now - self.last_link > self.STALE_AFTER:
            reason = "link_timeout"
        if reason:
            self.stop(reason, "FAULTED", fault=True)
            return
        dt = min(dt, 0.1)
        goal = POINTS[self.path[self.target_index]]
        distance = math.dist(self.position, goal)
        movement = min(distance, self.MAX_SPEED * dt)
        self.speed = movement / dt if dt > 0 else 0.0
        if distance:
            self.position = [p + (g - p) * movement / distance for p, g in zip(self.position, goal)]
        self.sequence += 1
        if movement > 0:
            self.current_stop = None
        if distance - movement < 1e-8:
            self.target_index += 1
            if self.target_index >= len(self.path):
                self.speed, self.state = 0.0, "COMPLETE"
                self.current_stop = self.trip["destination"]
                self.trip["status"] = "COMPLETED"
                self.store.trip(self.trip)
                self.store.event("arrival", self.trip)

    def snapshot(self):
        now = self.clock()
        return {
            "mode": self.mode,
            "state": self.state,
            "reason": self.reason,
            "position": {"x": self.position[0], "y": self.position[1]},
            "current_stop": self.current_stop,
            "speed_mps": self.speed,
            "trip": dict(self.trip) if self.trip else None,
            "route": list(self.path),
            "sequence": self.sequence,
            "motor_output_enabled": False,
            "telemetry": {
                "source": "simulated",
                "obstacle": self.obstacle,
                "sensor_age_s": max(0.0, now - self.last_sensor),
                "link_age_s": max(0.0, now - self.last_link),
                "sensor_failed": self.sensor_failed,
                "link_failed": self.link_failed,
            },
        }
