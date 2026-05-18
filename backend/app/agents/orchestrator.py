"""多 Agent 编排：调度员 / 能效分析 / 安全校验"""
import json
import os
from typing import List, Dict, Optional

from app.services.llm_client import chat_completion_full
from app.services.optimization import optimize_schedule
from app.services.docx_parser import extract_text_from_docx

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def _load_prompt(name: str) -> str:
    path = os.path.join(PROMPTS_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


SYSTEM_PROMPT = _load_prompt("system_prompt.md")


async def run_chat_agent(
    history: List[Dict],
    user_message: str,
    doc_context: Optional[str] = None,
) -> str:
    """通用对话 Agent：带泵站专家人设的对话"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if doc_context:
        messages.append({
            "role": "system",
            "content": f"用户上传了一份文书，以下是文书内容：\n\n{doc_context[:8000]}",
        })

    for msg in history[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})
    return await chat_completion_full(messages)


async def run_optimization_agent(
    station_info: str,
    operating_data: str,
    objective: str,
    constraints: str,
) -> Dict:
    """能效优化 Agent：制定调度方案"""
    template = _load_prompt("optimization_prompt.md")
    prompt = template.format(
        station_info=station_info,
        operating_data=operating_data,
        objective=objective,
        constraints=constraints,
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
            return json.loads(result_text[start:end])
    except json.JSONDecodeError:
        pass
    return {"explanation": result_text, "plan": [], "total_energy_kwh": 0}


async def run_safety_agent(plan: str, safety_thresholds: str, operating_data: str) -> Dict:
    """安全校验 Agent：校验方案"""
    template = _load_prompt("safety_prompt.md")
    prompt = template.format(
        plan=plan,
        safety_thresholds=safety_thresholds,
        operating_data=operating_data,
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
            return json.loads(result_text[start:end])
    except json.JSONDecodeError:
        pass
    return {"passed": False, "suggestion": result_text}


async def run_docx_agent(doc_text: str, mode: str = "qa", question: str = "") -> str:
    """文书分析 Agent"""
    template = _load_prompt("docx_analysis_prompt.md")
    prompt = template.format(
        document_content=doc_text[:8000],
        mode=mode,
        question=question,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return await chat_completion_full(messages)
