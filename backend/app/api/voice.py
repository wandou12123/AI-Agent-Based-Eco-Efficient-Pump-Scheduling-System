import os
import logging
import tempfile
import httpx
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.models import User

router = APIRouter()
settings = get_settings()
logger = logging.getLogger("pump_station")


@router.post("/transcribe")
async def transcribe_voice(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """接收音频文件，调用 Whisper API 转写为文字"""
    if not file.content_type or not file.content_type.startswith("audio/"):
        if file.content_type not in ("video/webm", "application/octet-stream"):
            raise HTTPException(400, f"不支持的文件类型: {file.content_type}")

    audio_data = await file.read()
    if len(audio_data) < 100:
        raise HTTPException(400, "音频文件过小，请重新录制")

    logger.info(
        f"[语音] 用户 {user.username} 上传音频: "
        f"{file.filename} ({file.content_type}, {len(audio_data)} bytes)"
    )

    suffix = _guess_suffix(file.content_type, file.filename)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = tmp.name

    try:
        text = await _call_whisper_api(tmp_path, file.filename or f"audio{suffix}")
    finally:
        os.unlink(tmp_path)

    logger.info(f"[语音] 转写完成: {text[:80]}...")
    return {"text": text}


def _guess_suffix(content_type: str | None, filename: str | None) -> str:
    mapping = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "video/webm": ".webm",
    }
    if content_type and content_type in mapping:
        return mapping[content_type]
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1]
    return ".webm"


async def _call_whisper_api(file_path: str, filename: str) -> str:
    """调用 OpenAI-compatible Whisper API 进行语音转写"""
    api_base = settings.LLM_API_BASE_URL.rstrip("/")
    api_key = settings.LLM_API_KEY

    # base_url 已含 /v1 时不再重复拼接
    if api_base.endswith("/v1"):
        whisper_url = f"{api_base}/audio/transcriptions"
    else:
        whisper_url = f"{api_base}/v1/audio/transcriptions"

    logger.info(f"[语音] 调用 Whisper API: {whisper_url}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(file_path, "rb") as f:
            try:
                response = await client.post(
                    whisper_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                    },
                    files={"file": (filename, f, "application/octet-stream")},
                    data={"model": "whisper-1"},
                )
            except httpx.ConnectError as e:
                logger.error(f"[语音] Whisper API 连接失败: {e}")
                raise HTTPException(502, "语音转写服务不可用，请使用文字输入")

    if response.status_code != 200:
        logger.error(f"[语音] Whisper API 返回 {response.status_code}: {response.text[:300]}")
        raise HTTPException(502, f"语音转写失败 (HTTP {response.status_code})，请使用文字输入")

    result = response.json()
    text = result.get("text", "").strip()
    if not text:
        raise HTTPException(400, "未识别到语音内容，请重新录制")

    return text
