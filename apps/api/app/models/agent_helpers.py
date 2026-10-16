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
        response=result.get("response", {}),
        model=usage.get("model", "rule-based-fallback"),
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        estimated_cost=usage.get("estimated_cost_usd", 0),
        latency_ms=sum(int(tc.get("duration_ms", 0)) for tc in result.get("tool_calls", [])),
    )
    db.add(run)
    db.flush()

    for tc in result.get("tool_calls", []):
        db.add(
            ToolCall(
                agent_run_id=run.id,
                name=tc.get("name", ""),
                args=tc.get("args", {}),
                result_summary=tc.get("result_summary", ""),
                duration_ms=int(tc.get("duration_ms", 0)),
            )
        )

    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            at=datetime.now(UTC),
            category="recommendation",
            severity="info",
            actor="ai-analyst",
            action="Chat run completed",
            subject=f"intent={result.get('intent', 'generic')}",
            details=question[:200],
            event_metadata=[
                {"key": "intent", "value": str(result.get("intent", "generic"))},
                {"key": "tool_count", "value": str(len(result.get("tool_calls", [])))},
            ],
        )
    )
    db.commit()
    return run