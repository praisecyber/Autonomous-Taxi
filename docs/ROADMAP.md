# Build with probix — milestone plan

## M0 · Delivered foundation
- Python package, validated backend, dashboard, SQLite history and read-only telemetry.
- A → B / C shortest-route simulation, latched faults, explicit recovery.
- Tests for arrival, cancellation, stale inputs, startup and authorization.
- ESP32 JPEG/telemetry bench starter and Arduino disarmed parser starter.

## M1 · Confirm hardware and read real telemetry
Fill HARDWARE.md with actual boards, pins, driver, steering and sensors. Compile both targets. Implement real sensor drivers with timestamps, validity and bounded timeouts. Add read-only Python adapter, parser and freshness tests. Keep physical output disabled.

Suggested Codex prompt:
> Read AGENTS.md and docs. Implement a read-only adapter for the confirmed ESP32 telemetry format, with malformed/stale-data tests. Preserve simulation and do not enable motors.

## M2 · Establish independent local stop behavior
Implement confirmed driver output and hardware-disable interface on the bench. Add Arduino watchdog and obstacle rules derived from measured stopping behavior. Validate STOP vs coasting/braking. Define and test motion-authority freshness through both relays. Do not start autonomous navigation yet.

## M3 · Vision and localization
Collect and label camera recordings with appropriate permissions. Detect route markers and path boundaries. Benchmark YOLOX Tiny against RT-DETRv2-S using the exact licences/weights you select; no weights are included here. Add encoders or a tested localization method for progress between markers. Do not treat monocular relative depth as stopping-distance ground truth.

## M4 · Low-speed controlled-course driving
Connect tested perception, localization and controller to the proven communication/safety layer. Start with stop-and-review obstacle handling. Test loss of camera, localization, serial, Wi-Fi and laptop process. Report measured response and stopping limits for declared conditions.

## M5 · Passenger/fleet features
Separate passenger and operator roles, pickup workflow, accessibility, notifications, battery measurements, maintenance records and dispatch. Passenger carrying and public-road operation need separate system validation and applicable approvals.

## Suggested completion evidence per milestone
Document trigger, expected behavior, actual result, logs and remaining gaps. Compilation is not a hardware test; a simulation pass is not physical-driving validation.
