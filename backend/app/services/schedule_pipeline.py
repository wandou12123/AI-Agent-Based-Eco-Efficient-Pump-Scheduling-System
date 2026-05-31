"""调度优化流水线（同步，供 API 与 Celery Worker 共用）"""
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import ScheduleTask, SchedulePlan, PumpUnit
from app.services.optimization import optimize_schedule, validate_safety
from app.services.audit import write_audit_log_sync

logger = logging.getLogger("pump_station")


def _template_explanation(plan_result: dict) -> str:
    return (
        f"【算法优化完成】总流量 {plan_result.get('total_flow', 0)} m³/h，"
        f"总功率 {plan_result.get('total_energy_kwh', 0)} kW。"
        f"可行性：{'满足' if plan_result.get('feasible') else '未完全满足'}目标流量。"
        f"（大模型解释暂不可用，已降级为模板说明）"
    )


def _run_llm_agents(plan_result: dict, units_data: list, objective: str, safety: dict) -> tuple[str, str]:
    """在 Celery 同步上下文中调用 LLM Agent（asyncio.run）"""
    import asyncio
    from app.agents.orchestrator import run_optimization_agent, run_safety_agent

    units_meta = json.dumps(units_data, ensure_ascii=False)
    try:
        llm_result = asyncio.run(run_optimization_agent(
            plan=plan_result,
            units_meta=units_meta,
            user_objective=objective or "最小化能耗",
        ))
        explanation = llm_result.get("explanation") or _template_explanation(plan_result)
    except Exception as e:
        logger.warning(f"[流水线] LLM 解释降级: {e}")
        explanation = _template_explanation(plan_result)

    try:
        safety_summary = asyncio.run(run_safety_agent(safety))
    except Exception:
        safety_summary = "安全校验完成，详见 checks 列表。"

    return explanation, safety_summary


def execute_optimize_pipeline(db: Session, task_id: int, user_id: int) -> dict[str, Any]:
    """
    同步执行完整优化流水线（详设 §5.3）。
    状态：parsing → optimizing → validating → done/failed
    """
    task = db.execute(
        select(ScheduleTask).where(ScheduleTask.id == task_id, ScheduleTask.user_id == user_id)
    ).scalar_one_or_none()
    if not task:
        raise ValueError("任务不存在")

    task.status = "parsing"
    db.flush()

    constraints = task.constraints_json or {}
    station_id = constraints.get("station_id", 1)

    units = db.execute(select(PumpUnit).where(PumpUnit.station_id == station_id)).scalars().all()
    units_data = [
        {
            "id": u.id,
            "unit_name": u.unit_name,
            "rated_power_kw": float(u.rated_power_kw or 0),
            "rated_flow": float(u.rated_flow or 0),
            "meta_json": u.meta_json,
        }
        for u in units
    ]

    if not units_data:
        task.status = "failed"
        write_audit_log_sync(db, user_id, "task.optimize.failed", {"task_id": task_id, "reason": "no_units"})
        db.commit()
        raise ValueError("该泵站暂无机组数据，无法优化")

    task.status = "optimizing"
    db.flush()

    target_flow = constraints.get("min_flow", 200)
    max_units = constraints.get("max_units_running")
    plan_result = optimize_schedule(units_data, target_flow, max_units)

    task.status = "validating"
    db.flush()

    safety = validate_safety(plan_result, constraints)
    explanation, safety_summary = _run_llm_agents(
        plan_result, units_data, task.objective_text or "", safety
    )

    task.status = "failed" if not plan_result.get("feasible") else "done"
    plan_with_safety = {**plan_result, "safety": safety, "safety_summary": safety_summary}

    plan_record = SchedulePlan(
        task_id=task.id,
        plan_json=plan_with_safety,
        energy_kwh=plan_result.get("total_energy_kwh", 0),
        explanation=explanation,
    )
    db.add(plan_record)
    write_audit_log_sync(
        db, user_id, "task.optimize",
        {"task_id": task_id, "feasible": plan_result.get("feasible"), "safety_passed": safety["passed"]},
    )
    db.commit()

    return {
        "task_id": task.id,
        "status": task.status,
        "plan": plan_with_safety,
        "explanation": explanation,
        "safety": safety,
        "safety_summary": safety_summary,
    }
