import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user
from app.models.models import User, Conversation, Message
from app.schemas.chat import (
    ConversationOut, MessageOut, SendMessageRequest,
    RenameConversationRequest, DocxAnalysisRequest,
)
from app.services.llm_client import chat_completion
from app.services.docx_parser import extract_text_from_docx
from app.agents.orchestrator import run_docx_agent, SYSTEM_PROMPT
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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = Conversation(user_id=user.id, title="新对话")
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    logger.info(f"[对话] 用户 {user.username} 创建新会话 #{conv.id}")
    return conv


@router.patch("/conversations/{conv_id}", response_model=ConversationOut)
async def rename_conversation(
    conv_id: int,
    req: RenameConversationRequest,
    user: User = Depends(get_current_user),
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
    logger.info(f"[对话] 会话 #{conv_id} 重命名为「{conv.title}」")
    return conv


@router.delete("/conversations/{conv_id}")
async def delete_conversation(
    conv_id: int,
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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

    # Build message history
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if req.msg_type == "docx" and req.file_url:
        import os
        file_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(req.file_url))
        doc_text = extract_text_from_docx(file_path)
        if doc_text:
            messages.append({
                "role": "system",
                "content": f"用户上传了一份文书，内容如下：\n\n{doc_text[:6000]}",
            })
            logger.info(f"[对话] 附加文书上下文, 长度={len(doc_text)}字")

    for msg in history:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content or ""})

    logger.info(f"[对话] 构建 LLM 请求: 系统提示+{len(history)}条历史 -> 共{len(messages)}条消息")

    conv_id = conv.id
    await db.commit()

    async def generate():
        full_reply = []
        try:
            async for chunk in chat_completion(messages, stream=True):
                full_reply.append(chunk)
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"[对话] LLM 流式调用异常: {e}")
            yield f"data: {json.dumps({'content': f'\\n\\n[错误] LLM 调用失败: {e}'}, ensure_ascii=False)}\n\n"

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
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import os
    file_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(req.file_url))
    logger.info(f"[文书] 用户 {user.username} 请求分析文书: {req.file_url} (模式={req.mode})")

    doc_text = extract_text_from_docx(file_path)
    if not doc_text:
        raise HTTPException(400, "无法提取文书内容")

    logger.info(f"[文书] 提取文书内容 {len(doc_text)} 字, 调用 LLM...")
    result = await run_docx_agent(doc_text, mode=req.mode, question=req.question)
    logger.info(f"[文书] 分析完成, 结果 {len(result)} 字")

    assistant_msg = Message(
        conversation_id=req.conversation_id,
        role="assistant",
        content=result,
        msg_type="text",
    )
    db.add(assistant_msg)
    await db.commit()

    return {"content": result, "conversation_id": req.conversation_id}
