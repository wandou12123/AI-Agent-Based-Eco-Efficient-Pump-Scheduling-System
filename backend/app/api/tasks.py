import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User, ScheduleTask, SchedulePlan, PumpUnit
from app.schemas.task import TaskCreate, TaskOut, PlanOut
from app.services.audit import write_audit_log
from app.services.schedule_pipeline import execute_optimize_pipeline
from app.core.sync_database import SyncSessionLocal

router = APIRouter()
logger = logging.getLogger("pump_station")
settings = get_settings()


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
    constraints = dict(req.constraints_json or {})
    if req.station_id:
        constraints["station_id"] = req.station_id

    task = ScheduleTask(
        user_id=user.id,
        conversation_id=req.conversation_id,
        objective_text=req.objective_text,
        constraints_json=constraints,
        status="created",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    await write_audit_log(db, user.id, "task.create", {"task_id": task.id, "constraints": constraints})
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
    result = await db.execute(
        select(ScheduleTask).where(ScheduleTask.id == task_id, ScheduleTask.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "任务不存在")
    plans = await db.execute(select(SchedulePlan).where(SchedulePlan.task_id == task_id))
    return plans.scalars().all()


@router.post("/{task_id}/optimize")
async def run_optimize(
    task_id: int,
    async_mode: bool = Query(False, description="true 时使用 Celery 异步队列"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    触发优化流水线。
    - async_mode=false（默认）：同步执行并返回完整结果
    - async_mode=true 且 USE_CELERY=true：提交 Celery 任务，返回 job_id 供轮询
    """
    result = await db.execute(
        select(ScheduleTask).where(ScheduleTask.id == task_id, ScheduleTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "任务不存在")

    use_async = async_mode and settings.USE_CELERY

    if use_async:
        from app.worker.tasks import optimize_schedule_task

        job = optimize_schedule_task.delay(task_id, user.id)
        task.status = "parsing"
        await db.flush()
        await write_audit_log(db, user.id, "task.optimize.queued", {"task_id": task_id, "job_id": job.id})
        return {
            "async": True,
            "job_id": job.id,
            "task_id": task_id,
            "status": "parsing",
            "message": "优化任务已提交队列，请轮询 /tasks/{task_id}/optimize/status",
        }

    sync_db = SyncSessionLocal()
    try:
        pipeline_result = execute_optimize_pipeline(sync_db, task_id, user.id)
    except ValueError as e:
        raise HTTPException(422, str(e))
    finally:
        sync_db.close()

    await db.refresh(task)
    return {"async": False, **pipeline_result}


@router.get("/{task_id}/optimize/status")
async def get_optimize_status(
    task_id: int,
    job_id: str = Query(..., description="Celery job_id"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """轮询 Celery 优化任务状态"""
    result = await db.execute(
        select(ScheduleTask).where(ScheduleTask.id == task_id, ScheduleTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "任务不存在")

    from celery.result import AsyncResult
    from app.worker.celery_app import celery_app

    job = AsyncResult(job_id, app=celery_app)
    state = job.state

    if state == "PENDING":
        return {"job_id": job_id, "state": "pending", "task_id": task_id, "status": task.status}
    if state == "PROGRESS":
        return {"job_id": job_id, "state": "running", "meta": job.info, "task_id": task_id, "status": task.status}
    if state == "SUCCESS":
        return {"job_id": job_id, "state": "done", "result": job.result, "task_id": task_id, "status": task.status}
    if state == "FAILURE":
        return {"job_id": job_id, "state": "failed", "error": str(job.info), "task_id": task_id, "status": task.status}

    return {"job_id": job_id, "state": state.lower(), "task_id": task_id, "status": task.status}
