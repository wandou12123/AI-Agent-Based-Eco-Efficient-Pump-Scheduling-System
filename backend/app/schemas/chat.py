from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: int
    role: str
    content: Optional[str] = None
    msg_type: str = "text"
    file_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    conversation_id: Optional[int] = None
    content: str
    msg_type: str = "text"
    file_url: Optional[str] = None
    doc_mode: Optional[str] = None  # "qa" or "extract" for docx


class RenameConversationRequest(BaseModel):
    title: str


class DocxAnalysisRequest(BaseModel):
    conversation_id: int
    file_url: str
    mode: str = "qa"       # "qa" or "extract"
    question: str = ""
    auto_create_task: bool = False  # extract 模式下自动创建调度任务


class ToolChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    content: str
