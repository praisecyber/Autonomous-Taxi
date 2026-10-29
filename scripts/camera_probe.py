"""Read one authenticated JPEG from the bench ESP32; never sends movement commands."""

import argparse
import os
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument("url", help="Example: http://192.168.1.50")
parser.add_argument("--output", default="runtime/camera.jpg")
args = parser.parse_args()
url = urlparse(args.url)
if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
    parser.error("Provide a plain http(s) camera base URL")
token = os.environ.get("ESP32_DEVICE_TOKEN")
if not token:
    parser.error("Set ESP32_DEVICE_TOKEN in your shell first")
request = urllib.request.Request(
    args.url.rstrip("/") + "/capture", headers={"X-Device-Token": token}
)
with urllib.request.urlopen(request, timeout=5) as response:
    if response.headers.get_content_type() != "image/jpeg":
        raise SystemExit("Camera did not return image/jpeg")
    image = response.read(2_000_001)
if len(image) > 2_000_000 or not image.startswith(b"\xff\xd8"):
    raise SystemExit("Invalid or oversized JPEG")
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(image)
print(f"Saved camera image: {output}")
