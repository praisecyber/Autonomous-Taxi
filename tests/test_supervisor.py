import pytest
from taxi.storage import Store
from taxi.supervisor import Supervisor, Conflict


class Clock:
    def __init__(self):
        self.now = 10.0

    def __call__(self):
        return self.now

    def advance(self, dt=0.05):
        self.now += dt


@pytest.fixture
def rig():
    store, clock = Store(":memory:"), Clock()
    core = Supervisor(store, clock)
    yield core, clock, store
    store.close()


def tick(core, clock, count=1):
    for _ in range(count):
        clock.advance()
        core.step()


def test_a_to_b_arrives_and_stops(rig):
    c, clock, store = rig
    c.start("B")
    tick(c, clock, 300)
    assert c.state == "COMPLETE"
    assert c.position == pytest.approx([10, 0])
    assert c.speed == 0 and c.current_stop == "B"
    assert store.trips()[0]["status"] == "COMPLETED"


def test_route_through_junction_to_c_and_return(rig):
    c, clock, _ = rig
    c.start("C")
    assert c.path == ["A", "J", "C"]
    tick(c, clock, 300)
    c.rearm()
    c.start("A")
    tick(c, clock, 300)
    assert c.current_stop == "A"


def test_obstacle_latches_until_explicit_rearm(rig):
    c, clock, _ = rig
    c.start("B")
    tick(c, clock, 3)
    c.obstacle = True
    tick(c, clock)
    assert c.state == "FAULT" and c.speed == 0
    assert c.trip["status"] == "FAULTED"
    with pytest.raises(Conflict):
        c.rearm()
    c.obstacle = False
    tick(c, clock, 3)
    assert c.state == "FAULT"
    c.stop()  # repeated stop cannot erase the fault reason
    assert c.state == "FAULT" and c.reason == "obstacle_detected"
    c.rearm()
    with pytest.raises(Conflict):
        c.start("B")  # between stops
    c.reset()
    c.start("B")


@pytest.mark.parametrize(
    "failure,reason", [("sensor_failed", "sensor_stale"), ("link_failed", "link_timeout")]
)
def test_stale_telemetry_stops(rig, failure, reason):
    c, clock, _ = rig
    c.start("B")
    setattr(c, failure, True)
    tick(c, clock, 12)
    assert c.state == "FAULT" and c.reason == reason and c.speed == 0
    setattr(c, failure, False)
    tick(c, clock)
    assert c.state == "FAULT"


def test_supervisor_stall_stops_before_moving(rig):
    c, clock, _ = rig
    c.start("B")
    clock.advance(2)
    c.step()
    assert c.position == [0, 0] and c.state == "FAULT"


def test_cancel_and_no_double_booking(rig):
    c, clock, store = rig
    c.start("B")
    with pytest.raises(Conflict):
        c.start("C")
    tick(c, clock)
    c.stop("trip_cancelled")
    position = list(c.position)
    tick(c, clock, 10)
    assert c.position == position and store.trips()[0]["status"] == "CANCELLED"


def test_invalid_stops_do_not_change_state(rig):
    c, _, _ = rig
    for dest in ["Z", "A"]:
        with pytest.raises(ValueError):
            c.start(dest)
    assert c.state == "READY" and c.trip is None


def test_restart_interrupts_active_trip(tmp_path):
    path = str(tmp_path / "test.sqlite3")
    store = Store(path)
    c = Supervisor(store)
    c.start("B")
    store.close()
    reopened = Store(path)
    assert reopened.trips()[0]["status"] == "INTERRUPTED"
    assert Supervisor(reopened).state == "READY"
    reopened.close()
