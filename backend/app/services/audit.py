"""审计日志服务（详设 §4.2 audit_logs、Backlog B-01）"""
import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.models import AuditLog

logger = logging.getLogger("pump_station")


async def write_audit_log(
    db: AsyncSession,
    user_id: Optional[int],
    action: str,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    """
    在关键写操作路径写入审计记录（异步）。

    Args:
        db: 异步数据库会话
        user_id: 操作用户 ID，系统事件可为 None
        action: 动作标识，如 station.create / task.optimize
        payload: 附加上下文（不含密码、api_key 等敏感字段）
    """
    safe_payload = payload or {}
    log = AuditLog(user_id=user_id, action=action, payload_json=safe_payload)
    db.add(log)
    await db.flush()
    logger.info(f"[审计] user={user_id} action={action}")


def write_audit_log_sync(
    db: Session,
    user_id: Optional[int],
    action: str,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    """同步审计写入（Celery Worker 使用）"""
    safe_payload = payload or {}
    log = AuditLog(user_id=user_id, action=action, payload_json=safe_payload)
    db.add(log)
    db.flush()
    logger.info(f"[审计] user={user_id} action={action}")
