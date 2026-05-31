"""大模型客户端封装（OpenAI 兼容 API，支持通义千问 DashScope）"""
import asyncio
import logging
import time
from typing import AsyncGenerator, Dict, List

from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger("pump_station")
_client = None
MAX_RETRIES = 2
REQUEST_TIMEOUT = 60.0


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        logger.info(f"[LLM] 初始化客户端 -> {settings.LLM_API_BASE_URL} (模型: {settings.LLM_MODEL_NAME})")
        _client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE_URL,
            timeout=REQUEST_TIMEOUT,
        )
    return _client


def _normalize_messages(messages: List[Dict]) -> List[Dict]:
    """合并连续同 role 消息，适配 OpenAI chat/completions 格式"""
    merged: List[Dict] = []
    for msg in messages:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n\n" + msg["content"]
        else:
            merged.append({"role": msg["role"], "content": msg["content"]})
    if not merged or merged[0]["role"] != "user":
        merged.insert(0, {"role": "user", "content": "请继续。"})
    return merged


async def chat_completion(messages: List[Dict], stream: bool = True) -> AsyncGenerator[str, None]:
    """
    统一封装上游模型 HTTP 调用、超时与流式解析（DashScope / OpenAI 兼容）。

    Args:
        messages: [{role, content}, ...] 含 system/user/assistant
        stream: True 时逐 token yield

    Yields:
        文本片段；失败时抛出异常（映射为 LLM_001）
    """
    settings = get_settings()
    client = _get_client()
    chat_msgs = _normalize_messages(messages)

    user_msg = ""
    for m in reversed(chat_msgs):
        if m["role"] == "user":
            user_msg = m["content"][:80]
            break

    logger.info(f"[LLM] >>> 发送请求 | 消息数={len(chat_msgs)} | 流式={stream} | 用户消息: {user_msg}")
    start = time.time()
    token_count = 0

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            if stream:
                response = await client.chat.completions.create(
                    model=settings.LLM_MODEL_NAME,
                    messages=chat_msgs,
                    max_tokens=4096,
                    temperature=0.7,
                    stream=True,
                )
                async for chunk in response:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        token_count += 1
                        yield delta
            else:
                response = await client.chat.completions.create(
                    model=settings.LLM_MODEL_NAME,
                    messages=chat_msgs,
                    max_tokens=4096,
                    temperature=0.7,
                    stream=False,
                )
                content = response.choices[0].message.content or ""
                token_count = len(content)
                yield content

            elapsed = time.time() - start
            logger.info(f"[LLM] <<< 响应完成 | 耗时={elapsed:.1f}s | tokens≈{token_count}")
            return
        except Exception as e:
            last_error = e
            elapsed = time.time() - start
            logger.error(f"[LLM] !!! 调用失败(第{attempt + 1}次) | 耗时={elapsed:.1f}s | 错误: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(1.0 * (attempt + 1))

    raise last_error


async def chat_completion_full(messages: List[Dict]) -> str:
    """非流式调用大模型，返回完整文本"""
    parts = []
    async for chunk in chat_completion(messages, stream=False):
        parts.append(chunk)
    return "".join(parts)
