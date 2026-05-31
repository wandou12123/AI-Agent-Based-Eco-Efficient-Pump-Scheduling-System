"""同步数据库会话（Celery Worker 专用）"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()
sync_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=5)
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)


def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
