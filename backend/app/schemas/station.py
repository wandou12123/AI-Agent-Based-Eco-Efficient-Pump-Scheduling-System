from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class StationCreate(BaseModel):
    name: str
    location: Optional[str] = None
    meta_json: Optional[Any] = None


class StationOut(BaseModel):
    id: int
    name: str
    location: Optional[str] = None
    meta_json: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UnitCreate(BaseModel):
    unit_name: str
    rated_power_kw: Optional[float] = None
    rated_flow: Optional[float] = None
    meta_json: Optional[Any] = None


class UnitOut(BaseModel):
    id: int
    station_id: int
    unit_name: Optional[str] = None
    rated_power_kw: Optional[float] = None
    rated_flow: Optional[float] = None
    meta_json: Optional[Any] = None

    class Config:
        from_attributes = True


class OperatingPointOut(BaseModel):
    id: int
    station_id: int
    flow: Optional[float] = None
    head: Optional[float] = None
    power: Optional[float] = None
    voltage: Optional[float] = None
    current_amp: Optional[float] = None
    energy_wh: Optional[float] = None
    ts: datetime

    class Config:
        from_attributes = True
