from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from taxi.supervisor import MissionSupervisor

app = FastAPI(title="Autonomous Taxi Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supervisor = MissionSupervisor()

class TripRequest(BaseModel):
    start_node: str
    destination_node: str

class ObstacleAlert(BaseModel):
    object_name: str
    confidence: float

@app.post("/api/passenger/book")
def book_passenger_trip(request: TripRequest):
    result = supervisor.book_trip(request.start_node, request.destination_node)
    if result["success"]:
        return {"status": "ACTIVE", "route": result["route"], "distance_meters": round(result["distance"], 2)}
    raise HTTPException(status_code=400, detail=result["error"])

@app.get("/api/vehicle/telemetry")
def get_telemetry():
    return {"state": supervisor.state, "current_position": supervisor.current_position, "fault_reason": supervisor.fault_reason}

@app.post("/api/vehicle/obstacle")
def report_obstacle(alert: ObstacleAlert):
    if supervisor.state == "ACTIVE":
        reason = f"{alert.object_name} blocking path"
        supervisor.trigger_pause(reason)
        return {"success": True, "status": "PAUSED", "message": reason}
    return {"success": True}

# --- This is the critical endpoint that wakes the car back up ---
@app.post("/api/vehicle/clear")
def report_clear():
    if supervisor.state == "PAUSED":
        supervisor.resume_movement()
        return {"success": True, "status": "ACTIVE"}
    return {"success": True}