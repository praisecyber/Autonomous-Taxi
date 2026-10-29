"""Offline operational drill: real backup -> isolated restore -> verified TLS/API -> restore again.

Never prints passwords, session cookies or keys; source records stay unchanged.
"""

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import secrets
import socket
import sqlite3
import ssl
import subprocess
import sys
import time
from pathlib import Path

import httpx
from websockets.asyncio.client import connect
from taxi.locking import DatabaseLease
from taxi.manage import copy_database


def port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def summary(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        return {
            "schema": db.execute("PRAGMA user_version").fetchone()[0],
            "accounts": db.execute(
                "SELECT username,role,enabled,must_change_password FROM users ORDER BY username"
            ).fetchall(),
            "trips": db.execute("SELECT id,status,owner_id FROM trips ORDER BY id").fetchall(),
            "configuration": db.execute("SELECT version,payload FROM configuration").fetchall(),
            "sessions": db.execute("SELECT count(*) FROM sessions").fetchone()[0],
        }


def private_log(path):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w")


@contextlib.contextmanager
def localhost_name(hostname):
    original = socket.getaddrinfo

    def resolve(host, *args, **kwargs):
        return original("127.0.0.1" if host == hostname else host, *args, **kwargs)

    socket.getaddrinfo = resolve
    try:
        yield
    finally:
        socket.getaddrinfo = original


def run(args):
    root = Path(__file__).resolve().parents[1]
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    credentials = json.loads(Path(args.credentials).read_text())["accounts"]
    hostname = "probix.localhost"
    backend_port = port()
    http_port = port()
    https_port = port()
    while len({backend_port, http_port, https_port}) != 3:
        http_port, https_port = port(), port()
    api_origin = f"http://127.0.0.1:{backend_port}"
    origin = f"https://{hostname}:{https_port}"
    processes = []
    logs = []
    clients = []
    checks = []

    def start_backend(database):
        log = private_log(output / f"backend-{len(logs)}.log")
        logs.append(log)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "taxi.api:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(backend_port),
                "--workers",
                "1",
                "--proxy-headers",
                "--forwarded-allow-ips",
                "127.0.0.1",
            ],
            cwd=root,
            env={
                **os.environ,
                "TAXI_DATA_DIR": str(database.parent),
                "TAXI_MODE": "simulation",
                "TAXI_DEPLOYMENT": "production",
                "TAXI_ALLOWED_HOSTS": hostname,
                "TAXI_SECURE_COOKIES": "1",
                "TAXI_ALLOW_LEGACY_TOKEN": "0",
            },
            stdout=log,
            stderr=log,
        )
        processes.append(process)
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Drill backend failed; inspect its private log")
            try:
                with httpx.Client(trust_env=False) as client:
                    if (
                        client.get(
                            api_origin + "/api/health", headers={"Host": hostname}
                        ).status_code
                        == 200
                    ):
                        return process
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        raise RuntimeError("Drill backend did not become healthy")

    try:
        with DatabaseLease(source), localhost_name(hostname):
            original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
            before = summary(source)
            backup = output / "backup.sqlite3"
            restored = output / "restored" / "taxi.sqlite3"
            copy_database(source, backup)
            copy_database(backup, restored, restore=True)
            baseline = summary(restored)
            for field in ("accounts", "configuration"):
                assert baseline[field] == before[field], field
            expected = [
                (tid, "INTERRUPTED" if status == "ACTIVE" else status, owner)
                for tid, status, owner in before["trips"]
            ]
            assert baseline["trips"] == expected
            assert baseline["sessions"] == 0
            checks.append(
                "backup/restore preserved accounts, owners, terminal history and configuration; FK/integrity checks passed"
            )
            backend = start_backend(restored)
            log = private_log(output / "caddy.log")
            logs.append(log)
            caddy = subprocess.Popen(
                [
                    str(Path(args.caddy).resolve()),
                    "run",
                    "--config",
                    "deploy/Caddyfile.local",
                    "--adapter",
                    "caddyfile",
                ],
                cwd=root,
                env={
                    **os.environ,
                    "XDG_DATA_HOME": str(output / "caddy-data"),
                    "XDG_CONFIG_HOME": str(output / "caddy-config"),
                    "TAXI_DOMAIN": hostname,
                    "TAXI_HTTPS_PORT": str(https_port),
                    "TAXI_HTTP_PORT": str(http_port),
                    "TAXI_FRONTEND_ROOT": str(root / "frontend/public"),
                    "TAXI_API_UPSTREAM": f"127.0.0.1:{backend_port}",
                },
                stdout=log,
                stderr=log,
            )
            processes.append(caddy)
            ca = output / "caddy-data" / "caddy" / "pki" / "authorities" / "local" / "root.crt"
            for _ in range(150):
                if caddy.poll() is not None:
                    raise RuntimeError("Caddy failed; inspect its private log")
                if ca.exists():
                    context = ssl.create_default_context(cafile=str(ca))
                    try:
                        with httpx.Client(verify=context, trust_env=False) as client:
                            if client.get(origin + "/api/health").status_code == 200:
                                break
                    except httpx.HTTPError:
                        pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Verified local HTTPS did not become ready")
            with httpx.Client(verify=context, trust_env=False) as client:
                for path in (
                    "/",
                    "/passenger",
                    "/operator",
                    "/admin",
                    "/diagnostics",
                    "/account",
                    "/docs",
                    "/openapi.json",
                    "/static/shared.css",
                    "/docs/assets/swagger-ui-bundle.js",
                ):
                    response = client.get(origin + path)
                    assert response.status_code == 200, path
                    assert response.headers["x-content-type-options"] == "nosniff"
                assert client.get(origin + "/backend/taxi/auth.py").status_code == 404
                assert (
                    client.get(
                        origin + "/api/trips", headers={"Authorization": "Bearer local-dev-only"}
                    ).status_code
                    == 401
                )
            with httpx.Client(trust_env=False) as client:
                redirect = client.get(f"http://{hostname}:{http_port}/account")
                assert (
                    redirect.status_code == 308
                    and redirect.headers["location"] == origin + "/account"
                )
                assert (
                    client.post(
                        api_origin + "/api/auth/login", headers={"Host": hostname}, json={}
                    ).status_code
                    == 403
                )
            checks.append(
                "TLS chain and hostname verified with the local CA; HTTP redirects; secure headers; pages/API/Swagger reachable"
            )
            sessions = {}
            rotated = {}
            for record in credentials:
                client = httpx.Client(
                    base_url=origin, verify=context, trust_env=False, headers={"Origin": origin}
                )
                clients.append(client)
                login = client.post(
                    "/api/auth/login",
                    json={"username": record["username"], "password": record["temporary_password"]},
                )
                assert login.status_code == 200
                assert login.json()["user"]["must_change_password"] == 1
                flags = {part.strip().lower() for part in login.headers["set-cookie"].split(";")}
                assert {"secure", "httponly", "samesite=strict"} <= flags
                assert client.get("/api/trips").status_code == 403
                new_password = secrets.token_urlsafe(24)
                response = client.post(
                    "/api/auth/password",
                    headers={"X-Taxi-CSRF": login.json()["csrf_token"]},
                    json={
                        "current_password": record["temporary_password"],
                        "new_password": new_password,
                    },
                )
                assert response.status_code == 204
                assert client.get("/api/auth/me").status_code == 401
                login = client.post(
                    "/api/auth/login",
                    json={"username": record["username"], "password": new_password},
                )
                assert login.status_code == 200 and not login.json()["user"]["must_change_password"]
                sessions[record["username"]] = (client, {"X-Taxi-CSRF": login.json()["csrf_token"]})
                rotated[record["username"]] = new_password
            checks.append(
                "all five real account credentials authenticated over verified TLS; forced rotation and old-session revocation passed on the isolated copy"
            )
            admin, ah = sessions["probix"]
            passenger, ph = sessions["probix.member1"]
            operator, oh = sessions["probix.member2"]
            diagnostic, dh = sessions["probix.member4"]
            for client in (passenger, operator, diagnostic):
                assert client.get("/api/admin/users").status_code == 403
            assert admin.post("/api/operator/stop", headers=ah).status_code == 403
            for path in ("/api/trips", "/api/events"):
                assert diagnostic.get(path).status_code == 403
            assert diagnostic.post("/api/operator/stop", headers=dh).status_code == 403
            config = admin.get("/api/admin/configuration").json()
            trip = passenger.post("/api/trips", headers=ph, json={"destination": "B"})
            assert trip.status_code == 201
            trip_id = trip.json()["id"]
            assert operator.get("/api/trips/" + trip_id).status_code == 200
            assert diagnostic.get("/api/trips/" + trip_id).status_code == 403
            assert admin.put("/api/admin/configuration", headers=ah, json=config).status_code == 409
            assert admin.get("/api/admin/records/trips", params={"q": trip_id}).json()["total"] == 1

            async def telemetry():
                async with connect(
                    f"wss://{hostname}:{https_port}/ws/telemetry",
                    ssl=context,
                    origin=origin,
                    additional_headers={
                        "Cookie": "taxi_session=" + passenger.cookies.get("taxi_session")
                    },
                    proxy=None,
                ) as ws:
                    data = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    assert (
                        data["telemetry"]["source"] == "simulated"
                        and not data["motor_output_enabled"]
                    )
                    assert data["trip"]["id"] == trip_id

            asyncio.run(telemetry())
            assert operator.post("/api/operator/stop", headers=oh).status_code == 200
            assert passenger.get("/api/trips/" + trip_id).json()["status"] == "CANCELLED"
            assert operator.post("/api/simulation/reset", headers=oh).status_code == 200
            assert admin.put("/api/admin/configuration", headers=ah, json=config).status_code == 200
            assert admin.put("/api/admin/configuration", headers=ah, json=config).status_code == 409
            checks.append(
                "role separation, owned trip, admin reporting/configuration gates, terminal cancellation and WSS through Caddy passed"
            )
            old_cookie = admin.cookies.get("taxi_session")
            backend.terminate()
            backend.wait(timeout=10)
            with sqlite3.connect(restored) as db:
                retained_sessions = db.execute("SELECT count(*) FROM sessions").fetchone()[0]
            assert retained_sessions >= 5
            second = output / "authenticated-backup.sqlite3"
            recovered = output / "recovery-check" / "taxi.sqlite3"
            copy_database(restored, second)
            copy_database(second, recovered, restore=True)
            assert summary(recovered)["sessions"] == 0
            backend = start_backend(recovered)
            with httpx.Client(
                base_url=origin, verify=context, trust_env=False, headers={"Origin": origin}
            ) as client:
                assert (
                    client.get(
                        "/api/auth/me", headers={"Cookie": "taxi_session=" + old_cookie}
                    ).status_code
                    == 401
                )
                login = client.post(
                    "/api/auth/login", json={"username": "probix", "password": rotated["probix"]}
                )
                assert login.status_code == 200
                assert (
                    client.post(
                        "/api/auth/logout", headers={"X-Taxi-CSRF": login.json()["csrf_token"]}
                    ).status_code
                    == 204
                )
            checks.append(
                f"second operational restore revoked {retained_sessions} stored sessions; stale cookie rejected and fresh admin login succeeded"
            )
            assert hashlib.sha256(source.read_bytes()).hexdigest() == original_digest
            checks.append(
                "live source database remained byte-for-byte unchanged throughout the drill"
            )
            report = {
                "hostname": hostname,
                "scope": "isolated local HTTPS; not public deployment",
                "checks": checks,
                "source_counts": {
                    "accounts": len(before["accounts"]),
                    "trips": len(before["trips"]),
                    "sessions": before["sessions"],
                },
                "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
                "schema": baseline["schema"],
                "credentials_in_report": False,
                "public_certificate_issued": False,
            }
            (output / "report.json").write_text(json.dumps(report, indent=2))
            print(json.dumps(report, indent=2))
    finally:
        for client in clients:
            client.close()
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        for log in logs:
            log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--credentials", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--caddy", default="runtime/tools/caddy")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
