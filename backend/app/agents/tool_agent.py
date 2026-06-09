"""多 Agent 工具调用编排（详设 §5.5.5）"""
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from app.services.llm_client import chat_completion_full
from app.agents.orchestrator import SYSTEM_PROMPT

logger = logging.getLogger("pump_station")
MAX_TOOL_ROUNDS = 3

TOOL_CALL_PATTERN = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def _tool_schemas() -> str:
    return """
可用工具（以 JSON 调用，包裹在 <tool_call>...</tool_call> 中）：
1. list_stations - 列出所有泵站，参数 {}
2. get_station_units - 获取泵站机组，参数 {"station_id": int}
3. create_schedule_task - 创建调度任务，参数 {"station_id": int, "objective_text": str, "min_flow": float}
4. run_optimize - 触发优化，参数 {"task_id": int}
5. create_and_optimize_schedule - 创建任务并立即优化（等价调度页「执行优化」），参数 {"station_id": int, "min_flow": float, "objective_text": str}

若无需工具，直接回答用户。需要工具时先输出 <tool_call>{"name":"...", "arguments":{...}}</tool_call>，等待工具结果后再总结。
"""


async def run_tool_agent(
    user_message: str,
    history: List[Dict],
    tool_handlers: Dict[str, Callable],
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> str:
    """
    规划-工具-再规划循环：LLM 决定调用工具或直接回复。

    Args:
        user_message: 用户输入
        history: 对话历史
        tool_handlers: 工具名 → async/sync callable(arguments) -> Any
        max_rounds: 最大工具调用轮次

    Returns:
        最终 assistant 回复文本
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + _tool_schemas()},
    ]
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    for round_idx in range(max_rounds):
        reply = await chat_completion_full(messages)
        match = TOOL_CALL_PATTERN.search(reply)
        if not match:
            return reply

        try:
            call = json.loads(match.group(1))
        except json.JSONDecodeError:
            return reply

        tool_name = call.get("name", "")
        arguments = call.get("arguments", {})
        handler = tool_handlers.get(tool_name)

        if not handler:
            tool_result = {"error": f"未知工具: {tool_name}"}
        else:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(handler):
                    tool_result = await handler(arguments)
                else:
                    tool_result = handler(arguments)
            except Exception as e:
                logger.warning(f"[ToolAgent] 工具 {tool_name} 执行失败: {e}")
                tool_result = {"error": str(e)}

        messages.append({"role": "assistant", "content": reply})
        messages.append({
            "role": "user",
            "content": f"[工具 {tool_name} 返回]\n{json.dumps(tool_result, ensure_ascii=False, default=str)}",
        })
        logger.info(f"[ToolAgent] 第{round_idx + 1}轮调用 {tool_name}")

    final = await chat_completion_full(messages)
    return final


def parse_extract_params(llm_text: str) -> Optional[dict]:
    """
    从文书 extract 模式 LLM 输出中解析调度参数 JSON。
    期望字段：station_id, min_flow, objective_text, max_units_running
    """
    try:
        start = llm_text.find("{")
        end = llm_text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(llm_text[start:end])
            if isinstance(data, dict) and ("min_flow" in data or "station_id" in data):
                return data
    except json.JSONDecodeError:
        pass

    params: dict = {}
    flow_match = re.search(r"(\d+(?:\.\d+)?)\s*m³/h", llm_text)
    if flow_match:
        params["min_flow"] = float(flow_match.group(1))
    if "最小化" in llm_text or "能耗" in llm_text:
        params["objective_text"] = "最小化能耗"
    return params if params else None
