"""多 Agent 编排：调度员 / 能效分析 / 安全校验 / 文书分析（详设 §5.5）"""
import json
import logging
import os
from typing import AsyncGenerator, Dict, List, Optional

from app.services.llm_client import chat_completion, chat_completion_full
from app.services.docx_parser import parse_docx_text

logger = logging.getLogger("pump_station")
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def _load_prompt(name: str) -> str:
    path = os.path.join(PROMPTS_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


SYSTEM_PROMPT = _load_prompt("system_prompt.md")


def _build_chat_messages(
    history: List[Dict],
    user_message: str,
    doc_context: Optional[str] = None,
) -> List[Dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if doc_context:
        messages.append({
            "role": "system",
            "content": f"用户上传了一份文书，以下是文书内容：\n\n{doc_context[:8000]}",
        })
    for msg in history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


async def run_chat_agent(
    history: List[Dict],
    user_message: str,
    doc_context: Optional[str] = None,
    stream: bool = False,
) -> AsyncGenerator[str, None] | str:
    """
    对话编排入口，组装上下文并调用 LLM，支持流式/非流式并做异常映射。

    Args:
        history: 历史消息 [{role, content}, ...]
        user_message: 当前用户输入
        doc_context: 可选文书上下文（已限长）
        stream: True 时返回 AsyncGenerator 逐段输出

    Returns:
        stream=True 时 AsyncGenerator[str]；否则完整回复 str
    """
    messages = _build_chat_messages(history, user_message, doc_context)
    if stream:
        return chat_completion(messages, stream=True)
    return await chat_completion_full(messages)


def _render_prompt(template: str, **kwargs) -> str:
    """安全替换占位符，避免模板内 JSON 花括号与 str.format 冲突"""
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


async def run_optimization_agent(
    plan: Dict,
    units_meta: str,
    user_objective: str,
) -> Dict:
    """
    基于已求解的数值方案生成人读解释，不负责生成开停机决策。

    Args:
        plan: optimize_schedule 输出的数值方案（含 plan/total_flow/feasible）
        units_meta: 机组元数据 JSON 字符串
        user_objective: 用户调度目标描述

    Returns:
        {"explanation": str, ...}；LLM 不可用时由调用方降级
    """
    template = _load_prompt("optimization_prompt.md")
    prompt = _render_prompt(
        template,
        station_info=units_meta,
        operating_data=json.dumps(plan, ensure_ascii=False),
        objective=user_objective,
        constraints="（约束已在数值方案中满足，请基于给定 plan 解释，勿自造开停机表）",
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    result_text = await chat_completion_full(messages)
    try:
        start = result_text.find("{")
        end = result_text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(result_text[start:end])
            if "explanation" not in parsed:
                parsed["explanation"] = result_text
            return parsed
    except json.JSONDecodeError:
        pass
    return {"explanation": result_text}


async def run_safety_agent(validation_result: Dict) -> str:
    """
    将规则校验结果转为用户可读风险提示，不改变校验判定。

    Args:
        validation_result: validate_safety 返回的 {passed, checks}

    Returns:
        自然语言安全摘要；LLM 失败时返回模板化说明
    """
    if validation_result.get("passed"):
        return "安全校验通过：方案满足功率、台数与流量阈值要求。"

    failed = [c for c in validation_result.get("checks", []) if not c.get("passed")]
    summary_lines = ["安全校验未完全通过，请关注以下项："]
    for item in failed:
        summary_lines.append(f"- {item.get('item')}: {item.get('detail')}")

    try:
        template = _load_prompt("safety_prompt.md")
        prompt = _render_prompt(
            template,
            plan=json.dumps(validation_result, ensure_ascii=False),
            safety_thresholds="见校验结果",
            operating_data="暂无",
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        result_text = await chat_completion_full(messages)
        try:
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(result_text[start:end])
                return parsed.get("suggestion") or parsed.get("explanation") or result_text
        except json.JSONDecodeError:
            pass
        return result_text
    except Exception as e:
        logger.warning(f"[Agent] run_safety_agent LLM 降级: {e}")
        return "\n".join(summary_lines)


async def run_docx_agent(
    doc_text: str,
    mode: str = "qa",
    question: str = "",
) -> str:
    """
    解析文书文本并限长入模，用于问答或参数提取，需防提示注入。

    Args:
        doc_text: 已清洗的 docx 纯文本
        mode: qa | summarize | extract
        question: qa 模式下的用户问题

    Returns:
        模型生成的分析文本
    """
    template = _load_prompt("docx_analysis_prompt.md")
    prompt = _render_prompt(
        template,
        document_content=doc_text[:8000],
        mode=mode,
        question=question,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return await chat_completion_full(messages)


async def run_docx_agent_from_file(
    file_path: str,
    mode: str = "qa",
    question: str = "",
) -> str:
    """从文件路径解析 docx 后调用 run_docx_agent"""
    doc_text = parse_docx_text(file_path)
    if not doc_text:
        raise ValueError("无法提取文书内容")
    return await run_docx_agent(doc_text, mode=mode, question=question)
