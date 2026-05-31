"""Celery 应用配置（详设 Backlog B-06）"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pump_station",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    task_soft_time_limit=120,
    task_time_limit=180,
)
