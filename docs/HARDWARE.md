# Hardware confirmation and bench setup

No hardware is connected to the development environment. The firmware is a starting point, not hardware-tested vehicle control.

| Item | Starter assumption | Must confirm |
|---|---|---|
| Camera board | AI Thinker ESP32-CAM / OV2640 | Exact module, PSRAM, camera pin map |
| Controller | Uno bench target | Uno, Nano, Mega or other model |
| Driver | None | L298N, TB6612FNG or another driver |
| Steering | None | Differential motors or steering servo |
| Motion feedback | None | Encoders, speed, steering feedback |
| Ultrasonics / IMU | Not implemented | Models, pins, timeouts, calibration |
| Emergency stop | Not implemented in firmware | Independent hardware disable and braking behavior |
| UART | Disabled on ESP32 by default | RX/TX pins, level shifting and boot-pin constraints |

## ESP32-CAM bench build

Install PlatformIO, open firmware/esp32_cam, and copy src/config.example.h to src/secrets.h. Set 2.4 GHz Wi-Fi credentials and a long device token. Keep relay pins -1 until wiring is confirmed. The AI Thinker camera pin map is embedded in main.cpp and must match the actual module.

```bash
pio run
pio run -t upload
pio device monitor
```

Build versions are specified in platformio.ini. Compilation requires downloading the toolchain/framework. The pinned Espressif platform uses the Arduino-ESP32 2.x camera API. If you upgrade the platform, check camera struct/API compatibility.

Read the printed IP, then on Windows:

```powershell
$env:ESP32_DEVICE_TOKEN = 'YOUR_DEVICE_TOKEN'
.\.venv\Scripts\python.exe scripts\camera_probe.py http://192.168.1.50
```

Replace the IP with the board's IP. The probe saves runtime/camera.jpg and makes no movement request. Never place the token in the URL.

The ESP32 currently captures one JPEG per request. /telemetry returns plain text with the last unvalidated UART line and its age. Before the first line, NO_TELEMETRY is reported; age=0 alone does not mean health. /stop only acknowledges sending a serial request; it does not confirm physical stopping.

## Arduino bench build

Open firmware/arduino, verify or change the board target, then use the same pio commands. The bench firmware accepts newline-terminated PING and STOP, rejects other commands, and reports sensors_ready=false and motion_enabled=false. No motor GPIO is assigned. USB serial is shared with pins 0/1 on an Uno; avoid programmer/relay contention.

## Before wiring

Confirm a stable supply, shared signal reference, UART level shifting when a 5 V Arduino transmits to the 3.3 V ESP32, and camera/SD/boot-pin conflicts. Do not power motors from GPIO. Test physical disable with motor power isolated before considering actuation. Adding a driver requires a board-specific implementation and measured stopping behavior; there is no hidden switch enabling motors in this release.
