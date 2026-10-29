# Protocol v0.1 and future motion contract

## Implemented bench protocol

UART: 115200 baud, 8N1, newline-terminated ASCII. Arduino receive frames have a maximum of 79 non-newline bytes. Oversized frames are discarded through the next newline. The ESP32 retains at most 255 characters per telemetry line; oversized lines are discarded. Processing per loop is bounded.

Requests:

```text
PING\n
STOP\n
```

Responses include JSON lines: pong, rejection, or disarmed telemetry with uptime_ms, motion_enabled=false, sensors_ready=false and reason. No distance or IMU value is invented. Motion requests are always rejected. There is no ARM command, command heartbeat or active-motor watchdog because outputs cannot be enabled in this version.

ESP32 local HTTP requires X-Device-Token:
- GET /capture → one image/jpeg frame.
- GET /telemetry → text/plain bench state and unvalidated UART line.
- POST /stop → request STOP on configured UART; returns 503 if UART disabled.

There is no physical safety assurance from HTTP or its response. These endpoints use plaintext on an isolated bench network; protect them appropriately before another deployment.

## Future movement protocol — design requirements, NOT implemented

Before accepting motion commands, implement and test:

1. Versioned, bounded frame schema with message type, session identifier, monotonic sequence and integrity validation. Define physical units and ranges for the actual drivetrain.
2. End-to-end freshness. A TTL measured only from Arduino receive time is insufficient: an old queued command must never acquire a new lifetime on late arrival. Use a tested challenge/response or synchronized-clock age scheme with bounded uncertainty.
3. Arduino-owned command watchdog, local obstacle stop and hardware disable interface. Invalid frames and generic heartbeats must not renew movement authority.
4. Latched fault/rearm handshake; no automatic rearm on connection or boot. Flush old pending movement on every session change.
5. Separate command receipt, accepted target, applied output, actual velocity and confirmed stopped state.
6. Tests for duplicates, old sessions, reordered frames, partial/oversized frames, stale camera/sensors, board reset, Wi-Fi loss and a stalled laptop.

Choose physical thresholds from measurements, not the simulator constants. Keep physical emergency-stop wiring independent of every protocol.
