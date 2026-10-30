"""Start one local/LAN PC HTTPS proxy and one loopback backend on Windows or Linux."""

import argparse
import ipaddress
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def configuration(args):
    address = ipaddress.ip_address(args.lan_address) if args.lan_address else None
    if address is not None and (
        address.version != 4 or not any(address in network for network in (
            ipaddress.ip_network("10.0.0.0/8"), ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16")
        ))
    ):
        raise ValueError("LAN address must be this PC's private IPv4 address")
    ports = [args.backend_port, args.https_port, args.http_port]
    if len(set(ports)) != 3 or any(not 1024 <= p <= 65535 for p in ports):
        raise ValueError("Use three different unprivileged ports (1024–65535)")
    data = Path(args.data_dir).resolve()
    if not (data / "taxi.sqlite3").is_file():
        raise ValueError("Database missing: restore existing data or provision accounts first")
    caddy = Path(args.caddy).resolve()
    if not caddy.is_file():
        raise ValueError("Install a verified Caddy executable and pass its path with --caddy")
    hostname, bind = (str(address), str(address)) if address else ("probix.localhost", "127.0.0.1")
    environment = os.environ.copy()
    environment.update({
        "TAXI_DOMAIN": hostname, "TAXI_LISTEN_ADDRESS": bind,
        "TAXI_DEPLOYMENT": "production", "TAXI_MODE": "simulation",
        "TAXI_SECURE_COOKIES": "1", "TAXI_ALLOW_LEGACY_TOKEN": "0",
        "TAXI_ALLOWED_HOSTS": hostname, "TAXI_DATA_DIR": str(data),
        "TAXI_HTTPS_PORT": str(args.https_port), "TAXI_HTTP_PORT": str(args.http_port),
        "TAXI_API_UPSTREAM": f"127.0.0.1:{args.backend_port}",
        "TAXI_FRONTEND_ROOT": (ROOT / "frontend/public").as_posix(),
        "XDG_DATA_HOME": (data / "tls-pc/data").as_posix(),
        "XDG_CONFIG_HOME": (data / "tls-pc/config").as_posix(),
    })
    return environment, caddy, data, hostname, bind


def available(address, port):
    with socket.socket() as listener:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        listener.bind((address, port))


def run(args):
    environment, caddy, data, hostname, bind = configuration(args)
    for address, port in (("127.0.0.1", args.backend_port), (bind, args.https_port),
                          (bind, args.http_port)):
        available(address, port)
    logs = data / "tls-pc"
    logs.mkdir(mode=0o700, parents=True, exist_ok=True)
    children, streams = [], []
    def shutdown(*_):
        raise KeyboardInterrupt

    old_handler = signal.signal(signal.SIGTERM, shutdown)
    try:
        validation = subprocess.run(
            [str(caddy), "validate", "--config", "deploy/Caddyfile.pc", "--adapter", "caddyfile"],
            cwd=ROOT, env=environment, capture_output=True, text=True,
        )
        if validation.returncode:
            raise RuntimeError("Caddy configuration validation failed")
        if args.check:
            print("PC configuration, executable and port checks passed; no server started.")
            return
        commands = [
            [sys.executable, "-m", "uvicorn", "taxi.api:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(args.backend_port), "--workers", "1",
             "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"],
            [str(caddy), "run", "--config", "deploy/Caddyfile.pc", "--adapter", "caddyfile"],
        ]
        for command, name in zip(commands, ("backend", "caddy")):
            fd = os.open(logs / (name + ".log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            stream = os.fdopen(fd, "a")
            streams.append(stream)
            children.append(subprocess.Popen(command, cwd=ROOT, env=environment,
                                             stdout=stream, stderr=stream))
        print(f"Starting PC HTTPS: https://{hostname}:{args.https_port}/account", flush=True)
        print(f"Public CA certificate after startup: {logs}/data/caddy/pki/authorities/local/root.crt", flush=True)
        print("Trust that public certificate on clients; keep private CA keys private. Ctrl+C stops both processes.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.25)
        raise RuntimeError(f"A server exited; inspect private logs in {logs}")
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for stream in streams:
            stream.close()
        signal.signal(signal.SIGTERM, old_handler)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--lan-address", help="This PC's private IPv4 address; omit for loopback only")
    result.add_argument("--data-dir", default=str(ROOT / "runtime"))
    result.add_argument("--caddy", default=str(ROOT / "runtime/tools" / ("caddy.exe" if os.name == "nt" else "caddy")))
    result.add_argument("--backend-port", type=int, default=8000)
    result.add_argument("--https-port", type=int, default=8443)
    result.add_argument("--http-port", type=int, default=8080)
    result.add_argument("--check", action="store_true")
    return result


if __name__ == "__main__":
    options = parser()
    try:
        run(options.parse_args())
    except (ValueError, RuntimeError, OSError) as error:
        options.exit(1, f"PC startup failed: {error}\n")
