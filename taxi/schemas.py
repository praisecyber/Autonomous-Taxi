from pydantic import BaseModel
from enum import Enum
from typing import Optional
import time

class TripState(str, Enum):
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    FAULT = "fault_stop"
    COMPLETE = "complete"

class OperatorCommand(BaseModel):
    action: str  # "stop" or "rearm"
    operator_id: str

class TripStatus(BaseModel):
    trip_id: str
    state: TripState
    current_speed: float
    fault_reason: Optional[str] = None

class TelemetryFrame(BaseModel):
    timestamp: float
    front_distance_m: float
    camera_status: str