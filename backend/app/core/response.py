"""统一 API 响应与错误码（详设 §3.1、§7.2）"""
from typing import Any, Optional


class ErrorCode:
    AUTH_001 = "AUTH_001"  # Token 无效/过期
    AUTH_002 = "AUTH_002"  # 密码错误
    CHAT_001 = "CHAT_001"  # 会话不存在
    TASK_001 = "TASK_001"  # 任务不存在
    TASK_002 = "TASK_002"  # 无机组无法优化
    LLM_001 = "LLM_001"  # 上游 LLM 不可用
    SRV_001 = "SRV_001"  # 未预期错误


def success_response(data: Any = None) -> dict:
    """构造统一成功响应体 { success, data }"""
    return {"success": True, "data": data}


def error_response(code: str, message: str) -> dict:
    """构造统一错误响应体 { success, error: { code, message } }"""
    return {"success": False, "error": {"code": code, "message": message}}


def http_status_to_error_code(status: int, detail: str) -> tuple[str, str]:
    """将 HTTP 状态码与 detail 映射为业务错误码"""
    detail_lower = detail.lower()
    if status == 401:
        if "密码" in detail or "凭证" in detail:
            return ErrorCode.AUTH_002, detail
        return ErrorCode.AUTH_001, detail
    if status == 404:
        if "会话" in detail:
            return ErrorCode.CHAT_001, detail
        if "任务" in detail:
            return ErrorCode.TASK_001, detail
        return ErrorCode.TASK_001, detail
    if status == 422 and "机组" in detail:
        return ErrorCode.TASK_002, detail
    if status in (502, 504):
        return ErrorCode.LLM_001, detail
    return ErrorCode.SRV_001, detail
