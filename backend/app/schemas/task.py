from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class TaskCreate(BaseModel):
    station_id: int
    objective_text: str
    constraints_json: Optional[Any] = None
    conversation_id: Optional[int] = None


class TaskOut(BaseModel):
    id: int
    user_id: int
    conversation_id: Optional[int] = None
    objective_text: Optional[str] = None
    constraints_json: Optional[Any] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: int
    task_id: int
    plan_json: Optional[Any] = None
    energy_kwh: Optional[float] = None
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
