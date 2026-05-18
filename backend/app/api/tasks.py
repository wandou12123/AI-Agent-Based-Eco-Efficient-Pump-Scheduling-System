import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    User, ScheduleTask, SchedulePlan, PumpStation, PumpUnit, OperatingPoint,
)
from app.schemas.task import TaskCreate, TaskOut, PlanOut
from app.services.optimization import optimize_schedule, validate_safety
from app.agents.orchestrator import run_optimization_agent, run_safety_agent

router = APIRouter()


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScheduleTask).where(ScheduleTask.user_id == user.id).order_by(desc(ScheduleTask.created_at))
    )
    return result.scalars().all()


@router.post("", response_model=TaskOut)
async def create_task(
    req: TaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = ScheduleTask(
        user_id=user.id,
        conversation_id=req.conversation_id,
        objective_text=req.objective_text,
        constraints_json=req.constraints_json,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScheduleTask).where(ScheduleTask.id == task_id, ScheduleTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.get("/{task_id}/plans", response_model=list[PlanOut])
async def get_task_plans(task_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SchedulePlan).where(SchedulePlan.task_id == task_id))
    return result.scalars().all()


@router.post("/{task_id}/optimize")
async def run_optimize(
    task_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """触发优化：先算法求解，再 LLM 生成解释，最后安全校验"""
    result = await db.execute(
        select(ScheduleTask).where(ScheduleTask.id == task_id, ScheduleTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "任务不存在")

    task.status = "parsing"
    await db.flush()

    constraints = task.constraints_json or {}
    station_id = constraints.get("station_id", 1)

    # Fetch units
    units_result = await db.execute(select(PumpUnit).where(PumpUnit.station_id == station_id))
    units = units_result.scalars().all()
    units_data = [
        {"id": u.id, "unit_name": u.unit_name,
         "rated_power_kw": float(u.rated_power_kw or 0),
         "rated_flow": float(u.rated_flow or 0),
         "meta_json": u.meta_json}
        for u in units
    ]

    if not units_data:
        task.status = "failed"
        await db.flush()
        raise HTTPException(422, "该泵站暂无机组数据，无法优化")

    task.status = "optimizing"
    await db.flush()

    target_flow = constraints.get("min_flow", 200)
    max_units = constraints.get("max_units_running")
    plan_result = optimize_schedule(units_data, target_flow, max_units)

    # LLM 生成解释
    try:
        llm_result = await run_optimization_agent(
            station_info=json.dumps(units_data, ensure_ascii=False),
            operating_data="暂无实时工况",
            objective=task.objective_text or "最小化能耗",
            constraints=json.dumps(constraints, ensure_ascii=False),
        )
        explanation = llm_result.get("explanation", "")
    except Exception:
        explanation = f"算法优化完成：总流量{plan_result['total_flow']}m³/h，总功率{plan_result['total_energy_kwh']}kW"

    task.status = "validating"
    await db.flush()

    # Safety validation
    safety = validate_safety(plan_result, constraints)

    if safety["passed"]:
        task.status = "done"
    else:
        task.status = "done"  # still save the plan with warnings

    plan_record = SchedulePlan(
        task_id=task.id,
        plan_json=plan_result,
        energy_kwh=plan_result.get("total_energy_kwh", 0),
        explanation=explanation,
    )
    db.add(plan_record)
    await db.flush()

    return {
        "task_id": task.id,
        "status": task.status,
        "plan": plan_result,
        "explanation": explanation,
        "safety": safety,
    }
