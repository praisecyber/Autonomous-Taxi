from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
from taxi.schemas import OperatorCommand, TripStatus, TripState
from taxi.supervisor import mission_supervisor
from pydantic import BaseModel

router = APIRouter(prefix="/api/operator", tags=["Operator"])

@router.post("/stop", response_model=TripStatus)
async def issue_software_stop(command: OperatorCommand):
    if command.action != "stop":
        raise HTTPException(status_code=400, detail="Invalid command")
    
    # Trigger the latched fault in the supervisor
    mission_supervisor.trigger_fault("Operator manual stop")
    
    return TripStatus(
        trip_id="TRIP_123", 
        state=mission_supervisor.state, 
        current_speed=0.0, 
        fault_reason="Operator manual stop"
    )

@router.post("/rearm", response_model=TripStatus)
async def issue_rearm(command: OperatorCommand):
    if command.action != "rearm":
        raise HTTPException(status_code=400, detail="Invalid command")
    
    success = mission_supervisor.rearm_vehicle()
    if not success:
        raise HTTPException(status_code=400, detail="Cannot rearm: vehicle not in fault state or checks failed")
    
    return TripStatus(
        trip_id=mission_supervisor.active_trip_id or 'None', 
        state=mission_supervisor.state, 
        current_speed=0.0, 
        fault_reason="Operator manual stop"
    )

class MissionRequest(BaseModel):
    start: str
    destination: str

@router.post("/start", response_model=TripStatus)
async def start_mission_endpoint(req: MissionRequest):
    success = mission_supervisor.start_mission(req.start, req.destination)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot start: vehicle not ready or invalid route")
    
    return TripStatus(
        trip_id=mission_supervisor.active_trip_id,
        state=mission_supervisor.state,
        current_speed=mission_supervisor.current_speed,
        fault_reason=None
    )

@router.websocket("/ws/telemetry")
async def telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Progress the physical movement simulation[cite: 18, 37]
            mission_supervisor.update_movement(delta_time=0.5)
            
            payload = {
                "trip_id": mission_supervisor.active_trip_id or "None",
                "state": mission_supervisor.state.value,
                "current_speed": mission_supervisor.current_speed,
                "distance_remaining": getattr(mission_supervisor, 'distance_remaining', 0.0),
                "fault_reason": mission_supervisor.state.name if mission_supervisor.state == TripState.FAULT else None
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print("Operator dashboard disconnected")