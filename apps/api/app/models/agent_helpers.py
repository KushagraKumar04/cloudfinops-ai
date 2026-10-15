import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.chat import AgentRun, ToolCall


def persist_agent_run(db: Session, tenant_id: uuid.UUID, question: str, result: dict) -> AgentRun:
    usage = result.get("usage", {}) or {}
    run = AgentRun(
        session_id=None,
        user_message=question,
        plan=result.get("plan", []),
