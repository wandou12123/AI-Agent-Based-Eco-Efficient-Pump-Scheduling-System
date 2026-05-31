from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_operator
from app.models.models import User, PumpStation, PumpUnit, OperatingPoint
from app.schemas.station import StationCreate, StationOut, UnitCreate, UnitOut, OperatingPointOut
from app.services.audit import write_audit_log

router = APIRouter()


@router.get("", response_model=list[StationOut])
async def list_stations(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(PumpStation).order_by(PumpStation.id))
    return result.scalars().all()


@router.post("", response_model=StationOut)
async def create_station(
    req: StationCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    station = PumpStation(name=req.name, location=req.location, meta_json=req.meta_json)
    db.add(station)
    await db.flush()
    await db.refresh(station)
    await write_audit_log(db, user.id, "station.create", {"station_id": station.id, "name": station.name})
    return station


@router.get("/{station_id}", response_model=StationOut)
async def get_station(station_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(PumpStation).where(PumpStation.id == station_id))
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(404, "泵站不存在")
    return station


@router.put("/{station_id}", response_model=StationOut)
async def update_station(
    station_id: int,
    req: StationCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PumpStation).where(PumpStation.id == station_id))
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(404, "泵站不存在")
    station.name = req.name
    station.location = req.location
    station.meta_json = req.meta_json
    await db.flush()
    await db.refresh(station)
    await write_audit_log(db, user.id, "station.update", {"station_id": station_id})
    return station


@router.delete("/{station_id}")
async def delete_station(
    station_id: int,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PumpStation).where(PumpStation.id == station_id))
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(404, "泵站不存在")
    await db.delete(station)
    await write_audit_log(db, user.id, "station.delete", {"station_id": station_id})
    return {"ok": True}


@router.get("/{station_id}/units", response_model=list[UnitOut])
async def list_units(station_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(PumpUnit).where(PumpUnit.station_id == station_id))
    return result.scalars().all()


@router.post("/{station_id}/units", response_model=UnitOut)
async def create_unit(
    station_id: int,
    req: UnitCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    unit = PumpUnit(
        station_id=station_id,
        unit_name=req.unit_name,
        rated_power_kw=req.rated_power_kw,
        rated_flow=req.rated_flow,
        meta_json=req.meta_json,
    )
    db.add(unit)
    await db.flush()
    await db.refresh(unit)
    await write_audit_log(db, user.id, "unit.create", {"station_id": station_id, "unit_id": unit.id})
    return unit


@router.put("/{station_id}/units/{unit_id}", response_model=UnitOut)
async def update_unit(
    station_id: int,
    unit_id: int,
    req: UnitCreate,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PumpUnit).where(PumpUnit.id == unit_id, PumpUnit.station_id == station_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(404, "机组不存在")
    unit.unit_name = req.unit_name
    unit.rated_power_kw = req.rated_power_kw
    unit.rated_flow = req.rated_flow
    unit.meta_json = req.meta_json
    await db.flush()
    await db.refresh(unit)
    await write_audit_log(db, user.id, "unit.update", {"station_id": station_id, "unit_id": unit_id})
    return unit


@router.delete("/{station_id}/units/{unit_id}")
async def delete_unit(
    station_id: int,
    unit_id: int,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PumpUnit).where(PumpUnit.id == unit_id, PumpUnit.station_id == station_id))
    unit = result.scalar_one_or_none()
    if not unit:
        raise HTTPException(404, "机组不存在")
    await db.delete(unit)
    await write_audit_log(db, user.id, "unit.delete", {"station_id": station_id, "unit_id": unit_id})
    return {"ok": True}


@router.get("/{station_id}/status", response_model=list[OperatingPointOut])
async def get_station_status(
    station_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(OperatingPoint)
        .where(OperatingPoint.station_id == station_id)
        .order_by(desc(OperatingPoint.ts))
        .limit(limit)
    )
    return result.scalars().all()
