from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supervisor import MissionSupervisor

router = APIRouter()
supervisor = MissionSupervisor()

class TripRequest(BaseModel):
    start_node: str
    destination_node: str

@router.post("/api/passenger/book")
def book_passenger_trip(request: TripRequest):
    # This automatically calls your navigation.py algorithm
    result = supervisor.book_trip(request.start_node, request.destination_node)
    
    if result["success"]:
        return {"status": "ACTIVE", "route": result["route"]}
    else:
        raise HTTPException(status_code=400, detail=result["error"])