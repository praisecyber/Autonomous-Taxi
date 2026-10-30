"""Read-only PC HTTPS readiness check; never logs in or changes application data."""

import argparse
import json
import ssl
import socket
from contextlib import contextmanager
import urllib.request
from urllib.parse import urlsplit


@contextmanager
def local_name(hostname):
    # .localhost is reserved for loopback, but some OS resolvers do not implement it.
    original = socket.getaddrinfo
    def resolve(host, *args, **kwargs):
        if host == hostname and (host == "localhost" or host.endswith(".localhost")):
            host = "127.0.0.1"
        return original(host, *args, **kwargs)
    socket.getaddrinfo = resolve
    try:
        yield
    finally:
        socket.getaddrinfo = original


def check(origin, ca_file=None):
    parsed = urlsplit(origin)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or
            parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("Use an HTTPS origin only, without credentials, path or query")
    origin = origin.rstrip("/")
    context = ssl.create_default_context(cafile=ca_file)
    # Direct connection is only appropriate for this explicitly selected local PC.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context)
    )
    results = []
    for path in ("/api/health", "/account", "/passenger", "/operator", "/admin",
                 "/diagnostics", "/static/shared.css", "/openapi.json", "/docs"):
        with local_name(parsed.hostname), opener.open(origin + path, timeout=10) as response:
            if response.geturl() != origin + path:
                raise ValueError("Unexpected redirect; check the configured HTTPS origin")
            if response.status != 200 or response.headers.get("X-Content-Type-Options") != "nosniff":
                raise ValueError("Unexpected status or missing content-type protection")
            body = response.read()
            if path == "/api/health":
                health = json.loads(body)
                if not health.get("ok") or health.get("mode") != "simulation":
                    raise ValueError("Backend is not a healthy simulation service")
            results.append(path)
    return {"origin": origin, "tls_verified": True, "read_only": True,
            "checked_paths": results,
            "authenticated_flows_verified": False, "websocket_verified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="https://probix.localhost:8443")
    parser.add_argument("--ca", help="Public CA certificate; never a private key")
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.origin, args.ca), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f"PC check failed: {error}\n")
