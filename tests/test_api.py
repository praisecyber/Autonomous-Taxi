import pytest
from fastapi.testclient import TestClient
from taxi.api import create_app

AUTH = {"Authorization": "Bearer test-operator-token"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("TAXI_MODE", "simulation")
    with TestClient(create_app(":memory:", "test-operator-token", run_loop=False)) as c:
        yield c


def test_dashboard_and_status(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    data = client.get("/api/status").json()
    assert data["mode"] == "simulation" and not data["motor_output_enabled"]


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
