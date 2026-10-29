import pytest
from fastapi.testclient import TestClient
from taxi.api import create_app

AUTH = {"Authorization": "Bearer test-operator-token"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TAXI_MODE", "simulation")
    with TestClient(create_app(":memory:", "test-operator-token", run_loop=False)) as c:
        yield c


def test_backend_is_api_only(client):
    for path in ("/", "/operator", "/admin", "/account", "/static/app.js"):
        assert client.get(path).status_code == 404
    data = client.get("/api/status").json()
    assert data["mode"] == "simulation" and not data["motor_output_enabled"]


def test_protected_records(client):
    for path in ("/api/trips", "/api/events"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer wrong-token"}).status_code == 401
        assert client.get(path, headers=AUTH).status_code == 200
    assert client.get("/api/trips", headers=AUTH).json() == []
    assert client.get("/api/events", headers=AUTH).json()[0]["kind"] == "boot"

    trip = client.post("/api/trips", json={"destination": "B"}, headers=AUTH).json()
    client.post(f"/api/trips/{trip['id']}/cancel", headers=AUTH)
    records = client.get("/api/trips", headers=AUTH).json()
    assert records[0]["id"] == trip["id"]
    assert records[0]["status"] == "CANCELLED"
    events = client.get("/api/events", headers=AUTH).json()
    assert events and all("detail" in event and "at" in event for event in events)


def test_authorization_and_trip_lifecycle(client):
    assert client.post("/api/trips", json={"destination": "B"}).status_code == 401
    trip = client.post("/api/trips", json={"destination": "B"}, headers=AUTH)
    assert trip.status_code == 201
    trip_id = trip.json()["id"]
    assert client.get(f"/api/trips/{trip_id}", headers=AUTH).json()["status"] == "ACTIVE"
    assert client.post("/api/trips", json={"destination": "C"}, headers=AUTH).status_code == 409
    assert client.post(f"/api/trips/{trip_id}/cancel", headers=AUTH).status_code == 200
    assert client.get(f"/api/trips/{trip_id}", headers=AUTH).json()["status"] == "CANCELLED"


def test_hazard_stop_and_recovery(client):
    client.post("/api/trips", json={"destination": "B"}, headers=AUTH)
    hazards = {"obstacle": True, "sensor_failed": False, "link_failed": False}
    state = client.post("/api/simulation/hazards", json=hazards, headers=AUTH).json()
    assert state["state"] == "FAULT" and state["speed_mps"] == 0
    assert client.post("/api/operator/rearm", headers=AUTH).status_code == 409
    hazards["obstacle"] = False
    client.post("/api/simulation/hazards", json=hazards, headers=AUTH)
    assert client.post("/api/operator/rearm", headers=AUTH).status_code == 200


def test_validation_and_websocket(client):
    assert client.post("/api/trips", json={"destination": "Z"}, headers=AUTH).status_code == 422
    assert (
        client.post("/api/trips", json={"destination": "B", "speed": 100}, headers=AUTH).status_code
        == 422
    )
    assert client.get("/api/trips/missing", headers=AUTH).status_code == 404
    with client.websocket_connect("/ws/telemetry") as ws:
        assert ws.receive_json()["telemetry"]["source"] == "simulated"


def test_hardware_start_is_rejected(monkeypatch):
    monkeypatch.setenv("TAXI_MODE", "hardware")
    with pytest.raises(RuntimeError, match="not implemented"):
        create_app(":memory:", "test-operator-token")
