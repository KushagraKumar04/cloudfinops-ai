import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )

    role: Mapped[str] = mapped_column(String(16), index=True)
    content: Mapped[str] = mapped_column(String(8000), default="")

    response_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    plan: Mapped[list[str]] = mapped_column(JSON, default=list)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    source: Mapped[str] = mapped_column(String(16), default="rules")
    intent: Mapped[str] = mapped_column(String(32), default="generic")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, server_default=func.now()
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


from app.models.chat import ChatSession  # noqa: E402