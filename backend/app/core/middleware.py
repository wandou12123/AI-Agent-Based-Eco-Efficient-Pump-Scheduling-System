"""统一成功响应中间件（详设 Backlog B-02）"""
import json
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response

from app.core.response import success_response

SKIP_PREFIXES = ("/uploads", "/docs", "/openapi.json", "/redoc")
SKIP_PATHS = ("/api/health",)


async def unified_response_middleware(request: Request, call_next: Callable) -> Response:
    """将 /api/v1 成功 JSON 响应包装为 { success, data }"""
    path = request.url.path

    if any(path.startswith(p) for p in SKIP_PREFIXES) or path in SKIP_PATHS:
        return await call_next(request)
    if "/chat/send" in path:
        return await call_next(request)

    response = await call_next(request)

    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return response
    if response.status_code >= 400:
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    if not body:
        wrapped = success_response(None)
        return Response(
            content=json.dumps(wrapped, ensure_ascii=False),
            status_code=response.status_code,
            media_type="application/json",
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return Response(content=body, status_code=response.status_code, headers=dict(response.headers))

    if isinstance(payload, dict) and "success" in payload:
        return Response(content=body, status_code=response.status_code, media_type="application/json")

    wrapped = success_response(payload)
    headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
    return Response(
        content=json.dumps(wrapped, ensure_ascii=False),
        status_code=response.status_code,
        media_type="application/json",
        headers=headers,
    )
