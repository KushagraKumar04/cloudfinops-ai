import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.chat import ChatSession
from app.models.chat_message import ChatMessage
from app.models.tenant import Tenant


def _title_from_first_message(text: str) -> str:
    clean = " ".join(text.strip().split())
    if len(clean) <= 60:
        return clean or "New conversation"
    return clean[:57] + "..."


def create_session(db: Session, tenant: Tenant, title: str | None = None) -> ChatSession:
    session = ChatSession(
        tenant_id=tenant.id,
        title=(title or "New conversation").strip() or "New conversation",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session, tenant: Tenant, limit: int = 50) -> list[ChatSession]:
    stmt = (
        select(ChatSession)
        .where(ChatSession.tenant_id == tenant.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_session(db: Session, tenant: Tenant, session_id: uuid.UUID) -> ChatSession | None:
    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.tenant_id == tenant.id)
    )
    return db.execute(stmt).scalar_one_or_none()


def delete_session(db: Session, tenant: Tenant, session_id: uuid.UUID) -> bool:
    session = db.get(ChatSession, session_id)
    if session is None or session.tenant_id != tenant.id:
        return False
    db.delete(session)
    db.commit()
    return True


def append_user_message(db: Session, session: ChatSession, content: str) -> ChatMessage:
    message = ChatMessage(session_id=session.id, role="user", content=content)
    db.add(message)
    session.message_count = (session.message_count or 0) + 1
    session.updated_at = datetime.now(UTC)
    if session.title == "New conversation" or not session.title:
        session.title = _title_from_first_message(content)
    db.commit()
    db.refresh(message)
    return message


def append_assistant_message(
    db: Session,
    session: ChatSession,
    result: dict,
) -> ChatMessage:
    response = result.get("response", {}) or {}
    message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response.get("answer", ""),
        response_payload=response,
        plan=result.get("plan", []),
        tool_calls=result.get("tool_calls", []),
        source=result.get("source", "rules"),
        intent=result.get("intent", "generic"),
    )
    db.add(message)
    session.message_count = (session.message_count or 0) + 1
    session.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(message)
    return message


def load_history_for_llm(
    db: Session,
    session_id: uuid.UUID,
    max_messages: int = 6,
) -> list[dict[str, str]]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(max_messages)
    )
    rows = list(db.execute(stmt).scalars().all())
    rows.reverse()
    out: list[dict[str, str]] = []
    for r in rows:
        if r.role not in {"user", "assistant"}:
            continue
        text = r.content or ""
        if not text:
            continue
        out.append({"role": r.role, "content": text[:1500]})
    return out


def session_summary(db: Session, tenant: Tenant) -> dict[str, int]:
    count_stmt = select(func.count(ChatSession.id)).where(ChatSession.tenant_id == tenant.id)
    total = int(db.execute(count_stmt).scalar() or 0)
    return {"total": total}