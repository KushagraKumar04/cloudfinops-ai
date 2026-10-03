import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.chat import (
    ChatEvidence,
    ChatFinding,
    ChatRecommendationRef,
    ChatToolCall,
)


class ChatMessageOut(CamelModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    response_payload: dict[str, Any] = Field(default_factory=dict)
    plan: list[str] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "rules"
    intent: str = "generic"
    created_at: datetime


class ChatSessionOut(CamelModel):
    id: uuid.UUID
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionOut):
    messages: list[ChatMessageOut] = Field(default_factory=list)


class ChatSessionCreateIn(CamelModel):
    title: str | None = None


class ChatSessionListOut(CamelModel):
    items: list[ChatSessionOut]
    total: int


class SessionMessageIn(CamelModel):
    message: str = Field(min_length=1, max_length=2000)