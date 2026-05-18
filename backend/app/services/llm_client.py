"""大模型客户端封装（Anthropic Messages API 格式）"""
import time
import logging
from typing import AsyncGenerator, List, Dict
from anthropic import AsyncAnthropic
from app.core.config import get_settings

logger = logging.getLogger("pump_station")
_client = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        settings = get_settings()
        logger.info(f"[LLM] 初始化客户端 -> {settings.LLM_API_BASE_URL} (模型: {settings.LLM_MODEL_NAME})")
        _client = AsyncAnthropic(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE_URL,
        )
    return _client


def _split_system_and_messages(messages: List[Dict]):
    """将 OpenAI 格式的 messages 拆分为 Anthropic 的 system + messages"""
    system_parts = []
    chat_messages = []
    for m in messages:
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            chat_messages.append({"role": m["role"], "content": m["content"]})

    if not chat_messages or chat_messages[0]["role"] != "user":
        chat_messages.insert(0, {"role": "user", "content": "请继续。"})

    merged = []
    for msg in chat_messages:
        if merged and merged[-1]["role"] == msg["role"]:
            merged[-1]["content"] += "\n\n" + msg["content"]
        else:
            merged.append(msg)

    return "\n\n".join(system_parts), merged


async def chat_completion(messages: List[Dict], stream: bool = True) -> AsyncGenerator[str, None]:
    """流式调用大模型，逐 token 返回"""
    settings = get_settings()
    client = _get_client()

    msg_count = len(messages)
    user_msg = ""
    for m in reversed(messages):
        if m["role"] == "user":
            user_msg = m["content"][:80]
            break

    logger.info(f"[LLM] >>> 发送请求 | 消息数={msg_count} | 流式={stream} | 用户消息: {user_msg}")
    start = time.time()
    token_count = 0

    system_prompt, chat_msgs = _split_system_and_messages(messages)

    try:
        if stream:
            async with client.messages.stream(
                model=settings.LLM_MODEL_NAME,
                max_tokens=4096,
                system=system_prompt,
                messages=chat_msgs,
                temperature=0.7,
            ) as response:
                async for text in response.text_stream:
                    token_count += 1
                    yield text
        else:
            response = await client.messages.create(
                model=settings.LLM_MODEL_NAME,
                max_tokens=4096,
                system=system_prompt,
                messages=chat_msgs,
                temperature=0.7,
            )
            content = response.content[0].text if response.content else ""
            token_count = len(content)
            yield content

        elapsed = time.time() - start
        logger.info(f"[LLM] <<< 响应完成 | 耗时={elapsed:.1f}s | tokens≈{token_count}")
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"[LLM] !!! 调用失败 | 耗时={elapsed:.1f}s | 错误: {e}")
        raise


async def chat_completion_full(messages: List[Dict]) -> str:
    """非流式调用大模型，返回完整文本"""
    settings = get_settings()
    client = _get_client()

    msg_count = len(messages)
    logger.info(f"[LLM] >>> 发送请求(非流式) | 消息数={msg_count}")
    start = time.time()

    system_prompt, chat_msgs = _split_system_and_messages(messages)

    try:
        response = await client.messages.create(
            model=settings.LLM_MODEL_NAME,
            max_tokens=4096,
            system=system_prompt,
            messages=chat_msgs,
            temperature=0.7,
        )
        result = response.content[0].text if response.content else ""
        elapsed = time.time() - start
        logger.info(f"[LLM] <<< 响应完成 | 耗时={elapsed:.1f}s | 长度={len(result)}字")
        return result
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"[LLM] !!! 调用失败 | 耗时={elapsed:.1f}s | 错误: {e}")
        raise
