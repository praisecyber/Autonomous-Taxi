import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from taxi.api import create_app
from taxi.auth import PASSWORDS
from taxi.deployment import Deployment
from taxi.manage import create_admin
from taxi.provisioning import provision_accounts
from taxi.storage import Store
from .test_accounts import accounts as accounts, session, PASSWORD


def test_provisioned_passwords_are_private_and_must_change(tmp_path, monkeypatch):
    monkeypatch.setenv("TAXI_MODE", "simulation")
    db, credentials = tmp_path / "taxi.sqlite3", tmp_path / "private" / "credentials.json"
    manifest = [
        {"username": "PROBIX", "role": "admin"},
        {"username": "probix.member4", "role": "diagnostics"},
    ]
    result = provision_accounts(db, manifest, credentials)
    assert result[0] == {"username": "probix", "role": "admin"}
    assert credentials.stat().st_mode & 0o777 == 0o600
    private = json.loads(credentials.read_text())["accounts"]
    initial = private[0]["temporary_password"]
    with sqlite3.connect(db) as connection:
        row = connection.execute(
            "SELECT password_hash,must_change_password FROM users WHERE username='probix'"
        ).fetchone()
        assert PASSWORDS.verify(initial, row[0]) and row[1] == 1 and initial != row[0]
    with pytest.raises(ValueError):
        provision_accounts(db, manifest, tmp_path / "duplicate.json")
    assert not (tmp_path / "duplicate.json").exists()
    with TestClient(create_app(str(db), run_loop=False)) as client:
        login = client.post("/api/auth/login", json={"username": "probix", "password": initial})
        assert login.status_code == 200 and login.json()["user"]["must_change_password"] == 1
        csrf = {"X-Taxi-CSRF": login.json()["csrf_token"]}
        assert client.get("/api/admin/users").status_code == 403
        assert client.get("/api/auth/me").status_code == 200
        assert (
            client.post(
                "/api/auth/password",
                headers=csrf,
                json={"current_password": initial, "new_password": "new-strong-password"},
            ).status_code
            == 204
        )
        assert client.get("/api/auth/me").status_code == 401
        fresh = client.post(
            "/api/auth/login", json={"username": "probix", "password": "new-strong-password"}
        )
        assert fresh.json()["user"]["must_change_password"] == 0
        assert client.get("/api/admin/users").status_code == 200
        assert "temporary_password" not in client.get("/api/admin/users").text


def test_diagnostics_role_cannot_read_private_trips_or_issue_commands(accounts):
    client, admin, _, _ = accounts
    response = client.post(
        "/api/admin/users",
        headers=admin,
        json={"username": "technician", "password": PASSWORD, "role": "diagnostics"},
    )
    assert response.status_code == 201
    technician, passenger = session(client, "technician"), session(client, "alice")
    trip = client.post("/api/trips", headers=passenger, json={"destination": "B"}).json()
    for path in [
        "/api/trips",
        "/api/trips/" + trip["id"],
        "/api/events",
        "/api/admin/users",
        "/api/admin/configuration",
    ]:
        assert client.get(path, headers=technician).status_code == 403
    for path in [
        "/api/operator/stop",
        "/api/operator/rearm",
        "/api/simulation/reset",
        "/api/trips/" + trip["id"] + "/cancel",
    ]:
        assert client.post(path, headers=technician).status_code == 403
    assert (
        client.post(
            "/api/operator/start", headers=technician, json={"destination": "B"}
        ).status_code
        == 403
    )
    assert client.get("/api/status", headers=technician).json()["trip"] is None
    with client.websocket_connect("/ws/telemetry", headers={"Cookie": technician["Cookie"]}) as ws:
        assert ws.receive_json()["trip"] is None


@pytest.mark.parametrize(
    "override",
    [
        {"TAXI_SECURE_COOKIES": "0"},
        {"TAXI_ALLOW_LEGACY_TOKEN": "1"},
        {"TAXI_ALLOWED_HOSTS": ""},
        {"TAXI_ALLOWED_HOSTS": "*"},
    ],
)
def test_production_fails_closed_on_insecure_settings(monkeypatch, override):
    settings = {
        "TAXI_DEPLOYMENT": "production",
        "TAXI_SECURE_COOKIES": "1",
        "TAXI_ALLOW_LEGACY_TOKEN": "0",
        "TAXI_ALLOWED_HOSTS": "probix.localhost",
    }
    settings.update(override)
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        Deployment.from_environment()


def test_production_requires_admin_and_enforces_https_host_cookie(tmp_path, monkeypatch):
    for key, value in {
        "TAXI_DEPLOYMENT": "production",
        "TAXI_MODE": "simulation",
        "TAXI_SECURE_COOKIES": "1",
        "TAXI_ALLOW_LEGACY_TOKEN": "0",
        "TAXI_ALLOWED_HOSTS": "probix.localhost",
    }.items():
        monkeypatch.setenv(key, value)
    db = tmp_path / "production.sqlite3"
    with pytest.raises(RuntimeError, match="enabled admin"):
        with TestClient(create_app(str(db), run_loop=False)):
            pass
    create_admin(db, "administrator", PASSWORD)
    with TestClient(
        create_app(str(db), run_loop=False), base_url="https://probix.localhost"
    ) as client:
        assert client.get("/api/health").status_code == 200
        assert (
            client.post(
                "http://probix.localhost/api/auth/login",
                json={"username": "administrator", "password": PASSWORD},
            ).status_code
            == 403
        )
        assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
        assert (
            client.get("/api/trips", headers={"Authorization": "Bearer local-dev-only"}).status_code
            == 401
        )
        login = client.post(
            "/api/auth/login", json={"username": "administrator", "password": PASSWORD}
        )
        assert login.status_code == 200
        assert "secure" in {part.strip().lower() for part in login.headers["set-cookie"].split(";")}
        assert client.get("/api/admin/users").status_code == 200
        assert (
            client.get(
                "http://probix.localhost/api/auth/me", headers={"X-Forwarded-Proto": "https"}
            ).status_code
            == 403
        )


def test_second_backend_and_offline_provisioning_are_blocked(accounts, tmp_path):
    client, _, _, path = accounts
    with pytest.raises(RuntimeError, match="Database in use"):
        with TestClient(create_app(str(path), run_loop=False)):
            pass
    with pytest.raises(RuntimeError, match="Database in use"):
        provision_accounts(
            path, [{"username": "newadmin", "role": "admin"}], tmp_path / "never.json"
        )
    assert not (tmp_path / "never.json").exists()
    assert client.get("/api/health").json()["ok"]


def test_schema_v1_migration_preserves_owners_sessions_and_config(tmp_path):
    path = tmp_path / "v1.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript("""CREATE TABLE users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','operator','passenger')),
            enabled INTEGER NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE trips(id TEXT PRIMARY KEY,origin TEXT,destination TEXT,status TEXT,
            created_at TEXT,updated_at TEXT,owner_id TEXT REFERENCES users(id));
            CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),expires_at REAL);
            CREATE TABLE events(id INTEGER PRIMARY KEY,at TEXT,kind TEXT,detail TEXT);
            CREATE TABLE configuration(id INTEGER PRIMARY KEY,version INTEGER,payload TEXT);
            INSERT INTO users VALUES('owner','old-user','hash','passenger',1,'before');
            INSERT INTO trips VALUES('history','A','B','COMPLETED','before','before','owner');
            INSERT INTO sessions VALUES('sessionhash','owner',9999999999);
            INSERT INTO configuration VALUES(1,7,'{}');
            PRAGMA user_version=1;""")
    store = Store(str(path), recover=False)
    assert store.db.execute("PRAGMA user_version").fetchone()[0] == 2
    assert store.db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert store.db.execute("SELECT owner_id,status FROM trips").fetchone()[:] == (
        "owner",
        "COMPLETED",
    )
    assert store.db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
    assert store.db.execute("SELECT version FROM configuration").fetchone()[0] == 7
    assert store.db.execute("SELECT must_change_password FROM users").fetchone()[0] == 0
    store.close()
