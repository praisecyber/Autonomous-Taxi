import json
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from taxi.api import create_app
from taxi.auth import COOKIE, PASSWORDS, digest
from taxi.manage import copy_database, create_admin
from taxi.storage import Store

PASSWORD = "test-password-at-least-12"


def session(client, username, password=PASSWORD):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    token = client.cookies.get(COOKIE)
    headers = {"Cookie": f"{COOKIE}={token}", "X-Taxi-CSRF": response.json()["csrf_token"]}
    client.cookies.clear()
    return headers


@pytest.fixture
def accounts(tmp_path, monkeypatch):
    monkeypatch.setenv("TAXI_MODE", "simulation")
    monkeypatch.setenv("TAXI_ALLOW_LEGACY_TOKEN", "1")
    monkeypatch.setenv("TAXI_SECURE_COOKIES", "0")
    path = tmp_path / "accounts.sqlite3"
    create_admin(path, "administrator", PASSWORD)
    app = create_app(str(path), operator_token="local-test-token", run_loop=False)
    with TestClient(app) as c:
        # The timer is intentionally disabled in API tests; use a deterministic clock
        # so password hashing cannot make the synthetic sensors expire between calls.
        app.state.core.clock = lambda: 10.0
        app.state.core.last_sensor = app.state.core.last_link = app.state.core.last_tick = 10.0
        headers = session(c, "administrator")
        for username, role in [
            ("alice", "passenger"),
            ("bob", "passenger"),
            ("driver", "operator"),
        ]:
            assert (
                c.post(
                    "/api/admin/users",
                    headers=headers,
                    json={"username": username, "password": PASSWORD, "role": role},
                ).status_code
                == 201
            )
        yield c, headers, app, path


def test_password_storage_cookie_and_validation(accounts):
    c, admin, app, _ = accounts
    row = app.state.store.db.execute("SELECT * FROM users WHERE username='alice'").fetchone()
    assert row["password_hash"].startswith("$argon2id$")
    assert PASSWORDS.verify(PASSWORD, row["password_hash"])
    r = c.post("/api/auth/login", json={"username": "ALICE", "password": PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    token = c.cookies.get(COOKIE)
    assert app.state.store.db.execute(
        "SELECT 1 FROM sessions WHERE token_hash=?", (digest(token),)
    ).fetchone()
    assert not app.state.store.db.execute(
        "SELECT 1 FROM sessions WHERE token_hash=?", (token,)
    ).fetchone()
    c.cookies.clear()
    r = c.post(
        "/api/admin/users",
        headers=admin,
        json={"username": "invalid user", "password": "private-short", "role": "admin"},
    )
    assert r.status_code == 422 and "private-short" not in r.text
    assert "password_hash" not in c.get("/api/admin/users", headers=admin).text


def test_login_errors_rate_limit_and_origin(accounts):
    c, _, app, _ = accounts
    app.state.auth.failures.clear()
    for username in ["not-found", "alice"] * 5:
        assert (
            c.post("/api/auth/login", json={"username": username, "password": "bad"}).status_code
            == 401
        )
    assert (
        c.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}).status_code
        == 429
    )
    app.state.auth.failures.clear()
    assert (
        c.post(
            "/api/auth/login",
            headers={"Origin": "https://elsewhere.test"},
            json={"username": "alice", "password": PASSWORD},
        ).status_code
        == 403
    )


def test_csrf_logout_and_expiry(accounts):
    c, _, app, _ = accounts
    alice = session(c, "alice")
    assert (
        c.post(
            "/api/trips", headers={"Cookie": alice["Cookie"]}, json={"destination": "B"}
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/api/trips",
            headers={**alice, "Origin": "https://evil.test"},
            json={"destination": "B"},
        ).status_code
        == 403
    )
    assert c.get("/api/auth/me", headers=alice).status_code == 200
    assert c.post("/api/auth/logout", headers=alice).status_code == 204
    assert c.get("/api/auth/me", headers=alice).status_code == 401
    alice = session(c, "alice")
    with app.state.store.db:
        app.state.store.db.execute(
            "UPDATE sessions SET expires_at=? WHERE token_hash=?",
            (time.time() - 1, digest(alice["Cookie"].split("=", 1)[1])),
        )
    assert c.get("/api/trips", headers=alice).status_code == 401


def test_passenger_ownership_and_operator_integration(accounts):
    c, admin, app, _ = accounts
    alice, bob, driver = session(c, "alice"), session(c, "bob"), session(c, "driver")
    for path in ["/api/admin/users", "/api/admin/reports", "/api/events"]:
        assert c.get(path, headers=alice).status_code == 403
    assert c.post("/api/operator/stop", headers=alice).status_code == 403
    assert c.post("/api/trips", headers=admin, json={"destination": "B"}).status_code == 403
    trip = c.post("/api/trips", headers=alice, json={"destination": "B"}).json()
    trip_id = trip["id"]
    assert c.get("/api/trips", headers=bob).json() == []
    assert c.get("/api/trips/" + trip_id, headers=bob).status_code == 404
    assert c.post("/api/trips/" + trip_id + "/cancel", headers=bob).status_code == 404
    assert c.get("/api/status", headers=bob).json()["trip"] is None
    assert c.get("/api/status").json()["trip"] is None
    assert c.get("/api/status", headers=alice).json()["trip"]["id"] == trip_id
    assert c.get("/api/trips/" + trip_id, headers=driver).status_code == 200
    assert c.get("/api/admin/users", headers=driver).status_code == 403
    assert c.post("/api/trips/" + trip_id + "/cancel", headers=alice).status_code == 200
    assert c.get("/api/trips/" + trip_id, headers=alice).json()["status"] == "CANCELLED"
    assert c.post("/api/trips/" + trip_id + "/cancel", headers=alice).status_code == 409
    assert c.post("/api/simulation/reset", headers=driver).status_code == 200
    assert c.post("/api/trips", headers=driver, json={"destination": "C"}).status_code == 201
    assert c.post("/api/operator/stop", headers=driver).status_code == 200
    assert c.get("/api/trips", headers=admin).json()[0]["owner_id"] is None
    assert app.state.core.state == "STOPPED"


def test_legacy_is_operator_only_and_can_be_disabled(accounts):
    c, _, app, _ = accounts
    legacy = {"Authorization": "Bearer local-test-token"}
    assert c.get("/api/trips", headers=legacy).status_code == 200
    assert c.get("/api/admin/users", headers=legacy).status_code == 403
    app.state.auth.legacy_enabled = False
    assert c.get("/api/trips", headers=legacy).status_code == 401
    assert c.post("/api/operator/stop", headers=legacy).status_code == 401


def test_user_management_revocation_self_protection_and_duplicates(accounts):
    c, admin, app, _ = accounts
    alice = session(c, "alice")
    users = c.get("/api/admin/users", headers=admin).json()["items"]
    user = next(u for u in users if u["username"] == "alice")
    me = next(u for u in users if u["username"] == "administrator")
    assert (
        c.patch(
            "/api/admin/users/" + me["id"],
            headers=admin,
            json={"role": "passenger", "enabled": False},
        ).status_code
        == 409
    )
    assert (
        c.post(
            "/api/admin/users",
            headers=admin,
            json={"username": "ALICE", "password": PASSWORD, "role": "admin"},
        ).status_code
        == 409
    )
    r = c.patch(
        "/api/admin/users/" + user["id"], headers=admin, json={"role": "operator", "enabled": False}
    )
    assert r.status_code == 200
    assert c.get("/api/trips", headers=alice).status_code == 401
    assert (
        c.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}).status_code
        == 401
    )
    assert (
        app.state.store.db.execute(
            "SELECT count(*) FROM sessions WHERE user_id=?", (user["id"],)
        ).fetchone()[0]
        == 0
    )


def test_password_change_revokes_every_session(accounts):
    c, _, _, _ = accounts
    first, second = session(c, "alice"), session(c, "alice")
    assert (
        c.post(
            "/api/auth/password",
            headers=first,
            json={"current_password": "wrong", "new_password": "new-long-password"},
        ).status_code
        == 401
    )
    assert (
        c.post(
            "/api/auth/password",
            headers=first,
            json={"current_password": PASSWORD, "new_password": "new-long-password"},
        ).status_code
        == 204
    )
    for old in (first, second):
        assert c.get("/api/auth/me", headers=old).status_code == 401
    assert session(c, "alice", "new-long-password")


def test_admin_server_filters_pagination_and_reports(accounts):
    c, admin, app, _ = accounts
    for index in range(31):
        app.state.store.trip(
            {
                "id": f"trip-{index:03}",
                "origin": "A",
                "destination": "B",
                "status": "COMPLETED" if index % 2 else "CANCELLED",
            }
        )
    first = c.get("/api/admin/records/trips?limit=10", headers=admin).json()
    second = c.get("/api/admin/records/trips?limit=10&offset=10", headers=admin).json()
    assert first["total"] == 31 and len(first["items"]) == 10
    assert not ({r["id"] for r in first["items"]} & {r["id"] for r in second["items"]})
    filtered = c.get("/api/admin/records/trips?status=COMPLETED&q=trip-00", headers=admin).json()
    assert filtered["total"] == 5 and all(t["status"] == "COMPLETED" for t in filtered["items"])
    assert c.get("/api/admin/records/trips?q=%25", headers=admin).json()["items"] == []
    assert c.get("/api/admin/records/trips?limit=1000", headers=admin).status_code == 422
    assert c.get("/api/admin/records/events?event_kind=boot", headers=admin).json()["total"] == 1
    report = c.get("/api/admin/reports", headers=admin).json()
    assert report["trips_by_status"] == {"CANCELLED": 16, "COMPLETED": 15}
    assert report["events_by_kind"]["user_created"] == 3
    assert c.get("/api/admin/users?limit=2&offset=2", headers=admin).json()["total"] == 4
    assert c.get("/api/admin/reports", headers=admin).headers["cache-control"] == "no-store"


def test_configuration_gate_validation_version_and_restart(accounts):
    c, admin, app, path = accounts
    config = c.get("/api/admin/configuration", headers=admin).json()
    invalid = {**config, "edges": {**config["edges"], "A": []}}
    assert c.put("/api/admin/configuration", headers=admin, json=invalid).status_code == 422
    invalid = {**config, "stops": {"Z": "Unknown"}}
    assert c.put("/api/admin/configuration", headers=admin, json=invalid).status_code == 422
    config["stops"]["B"] = "New library name"
    r = c.put("/api/admin/configuration", headers=admin, json=config)
    assert r.status_code == 200 and r.json()["version"] == 1
    assert c.put("/api/admin/configuration", headers=admin, json=config).status_code == 409
    assert c.get("/api/stops").json()["stops"]["B"] == "New library name"
    driver = session(c, "driver")
    c.post("/api/trips", headers=driver, json={"destination": "B"})
    assert c.put("/api/admin/configuration", headers=admin, json=r.json()).status_code == 409
    assert app.state.core.trip["status"] == "ACTIVE"
    from taxi.configuration import load_configuration

    store = Store(str(path), recover=False)
    assert load_configuration(store)["version"] == 1
    store.close()


def test_websocket_does_not_expose_other_passenger_trip(accounts):
    c, _, _, _ = accounts
    alice, bob = session(c, "alice"), session(c, "bob")
    trip = c.post("/api/trips", headers=alice, json={"destination": "B"}).json()
    with c.websocket_connect("/ws/telemetry", headers={"Cookie": bob["Cookie"]}) as ws:
        assert ws.receive_json()["trip"] is None
    with c.websocket_connect("/ws/telemetry", headers={"Cookie": alice["Cookie"]}) as ws:
        assert ws.receive_json()["trip"]["id"] == trip["id"]
        c.post("/api/auth/logout", headers=alice)
        assert ws.receive_json()["trip"] is None


def test_legacy_migration_and_backup_restore(tmp_path):
    original = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(original) as db:
        db.executescript("""CREATE TABLE trips(id TEXT PRIMARY KEY, origin TEXT NOT NULL,
            destination TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL);
            CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT NOT NULL,
            kind TEXT NOT NULL,detail TEXT NOT NULL);
            INSERT INTO trips VALUES('old','A','B','COMPLETED','then','then');
            INSERT INTO trips VALUES('running','A','C','ACTIVE','then','then');""")
    store = Store(str(original))
    old = store.db.execute("SELECT * FROM trips WHERE id='old'").fetchone()
    assert old["status"] == "COMPLETED" and old["owner_id"] is None
    assert (
        store.db.execute("SELECT status FROM trips WHERE id='running'").fetchone()[0]
        == "INTERRUPTED"
    )
    store.close()
    create_admin(original, "first-admin", PASSWORD)
    with pytest.raises(ValueError):
        create_admin(original, "other-admin", PASSWORD)
    with sqlite3.connect(original) as db:
        uid = db.execute("SELECT id FROM users").fetchone()[0]
        db.execute("INSERT INTO sessions VALUES('backup-session',?,?)", (uid, time.time() + 1000))
        db.execute("UPDATE trips SET status='ACTIVE' WHERE id='running'")
    backup, restored = tmp_path / "backup.sqlite3", tmp_path / "restored.sqlite3"
    copy_database(original, backup)
    copy_database(backup, restored, restore=True)
    with sqlite3.connect(restored) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert (
            db.execute("SELECT status FROM trips WHERE id='running'").fetchone()[0] == "INTERRUPTED"
        )
        assert db.execute("SELECT status FROM trips WHERE id='old'").fetchone()[0] == "COMPLETED"
        assert json.loads(
            db.execute("SELECT detail FROM events WHERE kind='restore'").fetchone()[0]
        )["sessions_revoked"]
    with pytest.raises(ValueError):
        copy_database(original, backup)
    with sqlite3.connect(original) as db:
        db.execute("PRAGMA user_version=99")
    with pytest.raises(ValueError):
        copy_database(original, tmp_path / "unsupported.sqlite3")
    with pytest.raises(ValueError):
        Store(str(original))


def test_account_installation_disables_demo_token_and_secure_cookie(tmp_path, monkeypatch):
    monkeypatch.setenv("TAXI_MODE", "simulation")
    monkeypatch.delenv("TAXI_ALLOW_LEGACY_TOKEN", raising=False)
    monkeypatch.setenv("TAXI_SECURE_COOKIES", "1")
    path = tmp_path / "secure.sqlite3"
    create_admin(path, "administrator", PASSWORD)
    with TestClient(create_app(str(path), run_loop=False), base_url="https://testserver") as c:
        assert (
            c.get("/api/trips", headers={"Authorization": "Bearer local-dev-only"}).status_code
            == 401
        )
        r = c.post("/api/auth/login", json={"username": "administrator", "password": PASSWORD})
        assert r.status_code == 200 and any(
            part.strip().lower() == "secure" for part in r.headers["set-cookie"].split(";")
        )
        assert c.get("/api/auth/me").status_code == 200
        assert (
            c.post(
                "/api/operator/stop", headers={"X-Taxi-CSRF": r.json()["csrf_token"]}
            ).status_code
            == 403
        )


def test_unowned_legacy_trips_and_owner_survives_updates(accounts):
    c, admin, app, _ = accounts
    app.state.store.trip({"id": "legacy", "origin": "A", "destination": "B", "status": "COMPLETED"})
    alice = session(c, "alice")
    assert c.get("/api/trips/legacy", headers=alice).status_code == 404
    assert c.get("/api/trips/legacy", headers=admin).status_code == 200
    created = c.post("/api/trips", headers=alice, json={"destination": "B"})
    assert created.status_code == 201
    tid = created.json()["id"]
    owner = c.get("/api/trips/" + tid, headers=alice).json()["owner_id"]
    c.post("/api/trips/" + tid + "/cancel", headers=alice)
    assert c.get("/api/trips/" + tid, headers=alice).json()["owner_id"] == owner
    app.state.store.trip(
        {"id": tid, "origin": "A", "destination": "B", "status": "CANCELLED", "owner_id": None}
    )
    assert c.get("/api/trips/" + tid, headers=alice).json()["owner_id"] == owner


def test_unauthenticated_admin_denial_and_invalid_road_segments(accounts):
    c, admin, _, _ = accounts
    for path in [
        "/api/admin/users",
        "/api/admin/reports",
        "/api/admin/configuration",
        "/api/admin/records/trips",
    ]:
        assert c.get(path).status_code == 401
    config = c.get("/api/admin/configuration", headers=admin).json()
    config["edges"]["A"].append("B")
    config["edges"]["B"].append("A")
    assert c.put("/api/admin/configuration", headers=admin, json=config).status_code == 422
    assert c.get("/api/admin/configuration", headers=admin).json()["version"] == 0


def test_bootstrap_validation_never_exposes_password(tmp_path):
    with pytest.raises(ValueError) as error:
        create_admin(tmp_path / "invalid.sqlite3", "admin", "my-private")
    assert "my-private" not in str(error.value)
