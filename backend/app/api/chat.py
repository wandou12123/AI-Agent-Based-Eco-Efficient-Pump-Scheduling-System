import json
import logging
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user, require_operator
from app.models.models import User, Conversation, Message, PumpStation, PumpUnit, ScheduleTask
from app.schemas.chat import (
    ConversationOut, MessageOut, SendMessageRequest,
    RenameConversationRequest, DocxAnalysisRequest, ToolChatRequest,
)
from app.services.docx_parser import parse_docx_text
from app.agents.orchestrator import run_chat_agent, run_docx_agent
from app.agents.tool_agent import run_tool_agent, parse_extract_params
from app.services.audit import write_audit_log
from app.services.tool_helpers import try_rule_based_reply
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()
logger = logging.getLogger("pump_station")


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.is_deleted == False)
        .order_by(desc(Conversation.updated_at))
    )
    convs = result.scalars().all()
    logger.info(f"[对话] 用户 {user.username} 获取会话列表, 共 {len(convs)} 条")
    return convs


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    conv = Conversation(user_id=user.id, title="新对话")
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    await write_audit_log(db, user.id, "conversation.create", {"conversation_id": conv.id})
    logger.info(f"[对话] 用户 {user.username} 创建新会话 #{conv.id}")
    return conv


@router.patch("/conversations/{conv_id}", response_model=ConversationOut)
async def rename_conversation(
    conv_id: int,
    req: RenameConversationRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conv_id, Conversation.user_id == user.id
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(404, "会话不存在")
    conv.title = req.title.strip()[:200]
    await db.flush()
    await db.refresh(conv)
    await write_audit_log(db, user.id, "conversation.rename", {"conversation_id": conv_id, "title": conv.title})
    logger.info(f"[对话] 会话 #{conv_id} 重命名为「{conv.title}」")
    return conv


@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: int,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    user_id = user.id
    db.expunge_all()

    result = await db.execute(
        text("UPDATE conversations SET is_deleted = 1 WHERE id = :cid AND user_id = :uid"),
        {"cid": conv_id, "uid": user_id},
    )
    if result.rowcount == 0:
        raise HTTPException(404, "会话不存在")
    await db.commit()
    async with AsyncSessionLocal() as audit_db:
        await write_audit_log(audit_db, user_id, "conversation.delete", {"conversation_id": conv_id})
        await audit_db.commit()
    logger.info(f"[对话] 软删除会话 #{conv_id} (数据库中保留)")
    return {"ok": True}


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conv_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "会话不存在")
    msgs = await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )
    msg_list = msgs.scalars().all()
    logger.info(f"[对话] 获取会话 #{conv_id} 历史消息, 共 {len(msg_list)} 条")
    return msg_list


@router.post("/chat/send")
async def send_message(
    req: SendMessageRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"[对话] 用户 {user.username} 发送消息: {req.content[:60]}...")

    if req.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id, Conversation.user_id == user.id
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(404, "会话不存在")
    else:
        conv = Conversation(user_id=user.id, title=req.content[:30] if req.content else "新对话")
        db.add(conv)
        await db.flush()
        logger.info(f"[对话] 自动创建会话 #{conv.id}")

    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.content,
        msg_type=req.msg_type,
        file_url=req.file_url,
    )
    db.add(user_msg)
    await db.flush()

    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = [{"role": m.role, "content": m.content or ""} for m in history_result.scalars().all() if m.role in ("user", "assistant")]

    doc_context = None
    if req.msg_type == "docx" and req.file_url:
        file_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(req.file_url))
        doc_context = parse_docx_text(file_path)
        if doc_context:
            logger.info(f"[对话] 附加文书上下文, 长度={len(doc_context)}字")

    conv_id = conv.id
    await db.commit()

    async def generate():
        full_reply = []
        try:
            stream = await run_chat_agent(history, req.content, doc_context=doc_context, stream=True)
            async for chunk in stream:
                full_reply.append(chunk)
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[对话] LLM 流式调用异常: {e}")
            fallback = f"\n\n[提示] 大模型暂时不可用，请稍后重试。（LLM_001）"
            full_reply.append(fallback)
            yield f"data: {json.dumps({'content': fallback}, ensure_ascii=False)}\n\n"

        reply_text = "".join(full_reply)
        logger.info(f"[对话] AI 回复完成, 长度={len(reply_text)}字, 写入会话 #{conv_id}")

        async with AsyncSessionLocal() as new_db:
            assistant_msg = Message(
                conversation_id=conv_id,
                role="assistant",
                content=reply_text,
                msg_type="text",
            )
            new_db.add(assistant_msg)
            await new_db.commit()

        yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/chat/docx-analyze")
async def analyze_docx(
    req: DocxAnalysisRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    file_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(req.file_url))
    logger.info(f"[文书] 用户 {user.username} 请求分析文书: {req.file_url} (模式={req.mode})")

    doc_text = parse_docx_text(file_path)
    if not doc_text:
        raise HTTPException(400, "无法提取文书内容")

    user_msg = Message(
        conversation_id=req.conversation_id,
        role="user",
        content=f"[文书分析] mode={req.mode} file={req.file_url}" + (f" question={req.question}" if req.question else ""),
        msg_type="docx",
        file_url=req.file_url,
    )
    db.add(user_msg)
    await db.flush()

    try:
        logger.info(f"[文书] 提取文书内容 {len(doc_text)} 字, 调用 LLM...")
        result = await run_docx_agent(doc_text, mode=req.mode, question=req.question)
        logger.info(f"[文书] 分析完成, 结果 {len(result)} 字")
    except Exception as e:
        logger.error(f"[文书] LLM 分析失败: {e}")
        raise HTTPException(502, f"文书分析失败: {e}")

    assistant_msg = Message(
        conversation_id=req.conversation_id,
        role="assistant",
        content=result,
        msg_type="text",
    )
    db.add(assistant_msg)
    await write_audit_log(db, user.id, "docx.analyze", {"mode": req.mode, "file_url": req.file_url})

    response: dict = {"content": result, "conversation_id": req.conversation_id}

    if req.mode == "extract" and req.auto_create_task:
        params = parse_extract_params(result)
        if params:
            station_id = params.get("station_id", 1)
            constraints = {
                "station_id": station_id,
                "min_flow": params.get("min_flow", 200),
            }
            if params.get("max_units_running"):
                constraints["max_units_running"] = params["max_units_running"]

            task = ScheduleTask(
                user_id=user.id,
                conversation_id=req.conversation_id,
                objective_text=params.get("objective_text", "最小化能耗"),
                constraints_json=constraints,
                status="created",
            )
            db.add(task)
            await db.flush()
            await db.refresh(task)
            await write_audit_log(db, user.id, "task.create.from_docx", {"task_id": task.id, "params": params})
            response["extracted_params"] = params
            response["task_id"] = task.id
            response["task_created"] = True
            result += f"\n\n---\n已自动创建调度任务 #{task.id}，请前往「调度优化」页面执行优化。"
            assistant_msg.content = result

    await db.commit()
    response["content"] = result
    return response


@router.post("/chat/tool")
async def tool_chat(
    req: ToolChatRequest,
    user: User = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """多 Agent 工具调用对话：支持查泵站、建任务、触发优化"""
    if req.conversation_id:
        conv_check = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id, Conversation.user_id == user.id
            )
        )
        if not conv_check.scalar_one_or_none():
            raise HTTPException(404, "会话不存在")
        conv_id = req.conversation_id
    else:
        conv = Conversation(user_id=user.id, title=req.content[:30])
        db.add(conv)
        await db.flush()
        conv_id = conv.id

    user_msg = Message(conversation_id=conv_id, role="user", content=req.content, msg_type="text")
    db.add(user_msg)
    await db.flush()

    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conv_id).order_by(Message.created_at)
    )
    history = [{"role": m.role, "content": m.content or ""} for m in history_result.scalars().all() if m.role in ("user", "assistant")]

    async def _list_stations(_args):
        rows = (await db.execute(select(PumpStation))).scalars().all()
        return [{"id": s.id, "name": s.name, "location": s.location} for s in rows]

    async def _get_units(args):
        sid = args.get("station_id", 1)
        rows = (await db.execute(select(PumpUnit).where(PumpUnit.station_id == sid))).scalars().all()
        return [{"id": u.id, "name": u.unit_name, "power": float(u.rated_power_kw or 0), "flow": float(u.rated_flow or 0)} for u in rows]

    async def _create_task(args):
        constraints = {"station_id": args.get("station_id", 1), "min_flow": args.get("min_flow", 200)}
        task = ScheduleTask(
            user_id=user.id,
            conversation_id=conv_id,
            objective_text=args.get("objective_text", "最小化能耗"),
            constraints_json=constraints,
            status="created",
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return {"task_id": task.id, "status": task.status}

    async def _run_optimize(args):
        from app.core.sync_database import SyncSessionLocal
        from app.services.schedule_pipeline import execute_optimize_pipeline
        tid = args.get("task_id")
        sync_db = SyncSessionLocal()
        try:
            result = execute_optimize_pipeline(sync_db, tid, user.id)
            return {
                "task_id": tid,
                "status": result["status"],
                "feasible": result["plan"].get("feasible"),
                "total_energy_kwh": result["plan"].get("total_energy_kwh"),
            }
        finally:
            sync_db.close()

    async def _create_and_optimize(args):
        from app.core.sync_database import SyncSessionLocal
        from app.services.schedule_pipeline import execute_optimize_pipeline

        station_id = int(args.get("station_id", 1))
        min_flow = float(args.get("min_flow", 200))
        objective = args.get("objective_text", "最小化能耗")
        constraints = {"station_id": station_id, "min_flow": min_flow}
        task = ScheduleTask(
            user_id=user.id,
            conversation_id=conv_id,
            objective_text=objective,
            constraints_json=constraints,
            status="created",
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        await write_audit_log(
            db, user.id, "task.create.from_tool",
            {"task_id": task.id, "constraints": constraints},
        )
        await db.commit()

        sync_db = SyncSessionLocal()
        try:
            result = execute_optimize_pipeline(sync_db, task.id, user.id)
        except ValueError as e:
            return {"task_id": task.id, "status": "failed", "error": str(e)}
        finally:
            sync_db.close()

        return {
            "task_id": task.id,
            "status": result["status"],
            "feasible": result["plan"].get("feasible"),
            "total_energy_kwh": result["plan"].get("total_energy_kwh"),
            "explanation": result.get("explanation", ""),
        }

    tool_handlers = {
        "list_stations": _list_stations,
        "get_station_units": _get_units,
        "create_schedule_task": _create_task,
        "run_optimize": _run_optimize,
        "create_and_optimize_schedule": _create_and_optimize,
    }

    task_id_hint: int | None = None
    try:
        fast = await try_rule_based_reply(req.content, tool_handlers)
        if fast:
            reply, task_id_hint = fast
        else:
            reply = await run_tool_agent(req.content, history, tool_handlers)
            tid_m = re.search(r"任务\s*#(\d+)", reply)
            if tid_m:
                task_id_hint = int(tid_m.group(1))
    except Exception as e:
        logger.error(f"[ToolChat] 失败: {e}")
        raise HTTPException(502, f"工具 Agent 调用失败: {e}")

    assistant_msg = Message(conversation_id=conv_id, role="assistant", content=reply, msg_type="text")
    db.add(assistant_msg)
    await write_audit_log(db, user.id, "chat.tool", {"conversation_id": conv_id})
    await db.commit()

    resp = {"content": reply, "conversation_id": conv_id}
    if task_id_hint:
        resp["task_id"] = task_id_hint
    return resp
