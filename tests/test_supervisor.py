import time
from taxi.schemas import TripState, TelemetryFrame
from taxi.supervisor import MissionSupervisor

def test_mission_lifecycle_and_fault_latch():
    # Initialize a fresh supervisor
    supervisor = MissionSupervisor()
    assert supervisor.state == TripState.READY
    
    # 1. Test normal start
    success = supervisor.start_mission("Engineering", "Library")
    assert success is True
    assert supervisor.state == TripState.ACTIVE
    
    # 2. Test fault latching (safety rule: clearing hazard never resumes trip)[cite: 30, 37]
    supervisor.trigger_fault("Simulated obstacle")
    assert supervisor.state == TripState.FAULT
    
    # 3. Test explicit rearm requirement[cite: 30, 37]
    rearm_success = supervisor.rearm_vehicle()
    assert rearm_success is True
    assert supervisor.state == TripState.READY

def test_telemetry_freshness_boundary():
    supervisor = MissionSupervisor()
    
    # Test valid fresh telemetry (within 0.5s)[cite: 6, 12, 30]
    fresh_frame = TelemetryFrame(timestamp=time.time(), front_distance_m=2.0, camera_status="ok")
    assert supervisor.add_telemetry(fresh_frame) is True
    
    # Test stale telemetry rejection (older than 0.5s)[cite: 6, 12, 30]
    stale_frame = TelemetryFrame(timestamp=time.time() - 1.0, front_distance_m=2.0, camera_status="ok")
    assert supervisor.add_telemetry(stale_frame) is False
    assert supervisor.state == TripState.FAULT