import os, sys, time, logging

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.response import error_response, http_status_to_error_code, ErrorCode, success_response
from app.core.middleware import unified_response_middleware
from app.api import auth, chat, stations, tasks, upload, voice

settings = get_settings()
logger = logging.getLogger("pump_station")

BANNER = """
╔══════════════════════════════════════════════════════╗
║     智水调度 - 泵站能效优化调度系统  v1.0.0          ║
║     Backend: FastAPI + MySQL + Qwen3 LLM             ║
╚══════════════════════════════════════════════════════╝"""


@asynccontextmanager
async def lifespan(application: FastAPI):
    print(BANNER)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[启动] 数据库连接成功，9 张表已就绪")
    except Exception as e:
        logger.error(
            f"\n{'='*55}\n"
            f"  [启动失败] 数据库连接错误！\n"
            f"  请检查 backend/.env 中的 MySQL 配置\n"
            f"  错误: {e}\n"
            f"{'='*55}"
        )
    logger.info(f"[启动] LLM 模型: {settings.LLM_MODEL_NAME}")
    logger.info(f"[启动] LLM 地址: {settings.LLM_API_BASE_URL}")
    logger.info(f"[启动] 文件上传目录: {settings.UPLOAD_DIR}")
    yield
    logger.info("[关闭] 服务已停止")


app = FastAPI(title="泵站能效优化调度系统", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def wrap_unified_response(request: Request, call_next):
    return await unified_response_middleware(request, call_next)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    path = request.url.path
    # 静态资源不记录
    if path.startswith("/uploads"):
        return response

    status = response.status_code
    method = request.method

    if status >= 500:
        level = "ERROR"
    elif status >= 400:
        level = "WARN "
    else:
        level = "INFO "

    logger.info(f"[{level}] {method:6s} {path} -> {status} ({duration_ms:.0f}ms)")
    return response


os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/v1", tags=["对话"])
app.include_router(stations.router, prefix="/api/v1/stations", tags=["泵站"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["调度任务"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["文件上传"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["语音"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    code, message = http_status_to_error_code(exc.status_code, detail)
    body = error_response(code, message)
    body["detail"] = detail  # 兼容旧前端
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(f"[异常] {request.method} {request.url.path}\n{tb}")
    body = error_response(ErrorCode.SRV_001, "服务器内部错误")
    body["detail"] = str(exc)
    return JSONResponse(status_code=500, content=body)


@app.get("/api/health")
async def health():
    return success_response({"status": "ok", "celery": settings.USE_CELERY})


if __name__ == "__main__":
    import uvicorn

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "pump_station": {"handlers": ["default"], "level": "INFO"},
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["default"], "level": "WARNING"},
        },
    }

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=log_config,
    )
