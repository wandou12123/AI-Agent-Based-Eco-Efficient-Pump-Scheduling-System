"""Celery 异步任务"""
import json
import logging

from app.worker.celery_app import celery_app
from app.core.sync_database import SyncSessionLocal
from app.services.schedule_pipeline import execute_optimize_pipeline

logger = logging.getLogger("pump_station")


@celery_app.task(bind=True, name="optimize_schedule_task")
def optimize_schedule_task(self, task_id: int, user_id: int):
    """异步执行调度优化流水线，结果写入 Redis backend"""
    db = SyncSessionLocal()
    try:
        self.update_state(state="PROGRESS", meta={"step": "optimizing", "task_id": task_id})
        result = execute_optimize_pipeline(db, task_id, user_id)
        return result
    except Exception as e:
        logger.error(f"[Celery] 优化任务 #{task_id} 失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()
