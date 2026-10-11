import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.orchestrator import run_orchestrator
from app.api.deps import get_current_tenant
from app.db.session import SessionLocal, get_db
from app.models.chat import ChatSession
from app.models.tenant import Tenant
from app.schemas.chat import ChatResponse
from app.schemas.chat_session import (
    ChatMessageOut,
    ChatSessionCreateIn,
    ChatSessionDetail,
    ChatSessionListOut,
    ChatSessionOut,
    SessionMessageIn,
)
from app.services.chat_sessions import (
    append_assistant_message,
    append_user_message,
    create_session,
    delete_session,
    get_session,
    list_sessions,
    load_history_for_llm,
)

router = APIRouter(prefix="/chat/sessions", tags=["chat-sessions"])


def _to_summary(session: ChatSession) -> ChatSessionOut:
    return ChatSessionOut.model_validate(session)


@router.get("", response_model=ChatSessionListOut)
def list_chat_sessions(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ChatSessionListOut:
    sessions = list_sessions(db, tenant)
    return ChatSessionListOut(items=[_to_summary(s) for s in sessions], total=len(sessions))


@router.post("", response_model=ChatSessionOut, status_code=201)
def create_chat_session(
    payload: ChatSessionCreateIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ChatSessionOut:
    session = create_session(db, tenant, title=payload.title)
    return _to_summary(session)


@router.get("/{session_id}", response_model=ChatSessionDetail)
def get_chat_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ChatSessionDetail:
    session = get_session(db, tenant, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    base = ChatSessionDetail.model_validate(session)
    base.messages = [ChatMessageOut.model_validate(m) for m in session.messages]
    return base


@router.delete("/{session_id}", status_code=204)
def delete_chat_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    ok = delete_session(db, tenant, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return None


def _run_orchestrator_in_thread(session_id: uuid.UUID, tenant_id: uuid.UUID, message: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if session is None:
            raise RuntimeError("Session disappeared during execution")
        history = load_history_for_llm(db, session_id, max_messages=6)
        if history and history[-1].get("role") == "user":
            history = history[:-1]
        result = run_orchestrator(db, tenant_id, message, history=history)
        append_assistant_message(db, session, result)
        return result
    finally:
        db.close()


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _normalize_response(response: dict[str, Any]) -> dict[str, Any]:
    recs = response.get("recommendations", []) or []
    normalized: list[dict[str, Any]] = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        normalized.append(
            {
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "estimatedMonthlySavings": float(
                    r.get("estimatedMonthlySavings", r.get("estimated_monthly_savings", 0)) or 0
                ),
                "risk": r.get("risk", "MEDIUM"),
            }
        )
    return {**response, "recommendations": normalized}


def _chunk_text(text: str, words_per_chunk: int = 4) -> list[str]:
    words = text.split(" ")
    chunks: list[str] = []
    for i in range(0, len(words), words_per_chunk):
        chunk = " ".join(words[i : i + words_per_chunk])
        if i + words_per_chunk < len(words):
            chunk += " "
        chunks.append(chunk)
    return chunks


async def _stream_events(
    session_id: uuid.UUID,
    tenant_id: uuid.UUID,
    message: str,
) -> AsyncIterator[str]:
    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if session is None or session.tenant_id != tenant_id:
            yield _sse("error", {"message": "Chat session not found"})
            return

        user_message = append_user_message(db, session, message)
        yield _sse(
            "user_ack",
            {
                "messageId": str(user_message.id),
                "sessionTitle": session.title,
            },
        )
    finally:
        db.close()

    yield _sse("planning", {})

    try:
        result = await asyncio.to_thread(_run_orchestrator_in_thread, session_id, tenant_id, message)
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})
        return

    yield _sse("plan", {"steps": result.get("plan", [])})
    await asyncio.sleep(0.05)

    for tc in result.get("tool_calls", []):
        yield _sse(
            "tool",
            {
                "id": tc.get("id", ""),
                "name": tc.get("name", ""),
                "args": tc.get("args", {}),
                "resultSummary": tc.get("result_summary", ""),
                "durationMs": int(tc.get("duration_ms", 0) or 0),
            },
        )
        await asyncio.sleep(0.08)

    response = result.get("response", {}) or {}
    answer = response.get("answer", "")

    yield _sse("answer_start", {})
    for chunk in _chunk_text(answer):
        yield _sse("token", {"text": chunk})
        await asyncio.sleep(0.02)
    yield _sse("answer_end", {})

    yield _sse(
        "done",
        {
            "response": _normalize_response(response),
            "source": result.get("source", "rules"),
            "intent": result.get("intent", "generic"),
            "llmError": result.get("llm_error"),
        },
    )


@router.post("/{session_id}/stream")
async def stream_chat_session(
    session_id: uuid.UUID,
    payload: SessionMessageIn,
    tenant: Tenant = Depends(get_current_tenant),
) -> StreamingResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message is required")

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        _stream_events(session_id, tenant.id, message),
        media_type="text/event-stream",
        headers=headers,
    )


@router.post("/{session_id}/messages", response_model=ChatResponse)
def post_session_message(
    session_id: uuid.UUID,
    payload: SessionMessageIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ChatResponse:
    session = get_session(db, tenant, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message is required")

    append_user_message(db, session, message)
    result = run_orchestrator(db, tenant.id, message)
    append_assistant_message(db, session, result)

    response = result.get("response", {}) or {}
    return ChatResponse(
        answer=response.get("answer", ""),
        plan=result.get("plan", []),
        tool_calls=result.get("tool_calls", []),
        findings=response.get("findings", []),
        evidence=response.get("evidence", []),
        recommendations=response.get("recommendations", []),
        confidence=float(response.get("confidence", 0.5)),
        requires_human_review=bool(response.get("requires_human_review", False)),
        follow_ups=response.get("follow_ups"),
        intent=result.get("intent", "generic"),
        source=result.get("source", "rules"),
        llm_error=result.get("llm_error"),
    )