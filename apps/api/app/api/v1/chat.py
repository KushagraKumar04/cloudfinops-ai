from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.orchestrator import run_orchestrator
from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.chat import (
    ChatEvidence,
    ChatFinding,
    ChatRecommendationRef,
    ChatRequest,
    ChatResponse,
    ChatToolCall,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ChatResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message is required")

    result = run_orchestrator(db, tenant.id, message)
    response = result["response"]

    tool_calls = [
        ChatToolCall(
            id=tc["id"],
            name=tc["name"],
            args=tc.get("args", {}),
            result_summary=tc.get("result_summary", ""),
            duration_ms=int(tc.get("duration_ms", 0)),
        )
        for tc in result.get("tool_calls", [])
    ]

    findings = [ChatFinding(**f) for f in response.get("findings", [])]
    evidence = [ChatEvidence(**e) for e in response.get("evidence", [])]
    recommendations = [
        ChatRecommendationRef(
            id=r["id"],
            title=r["title"],
            estimated_monthly_savings=float(r["estimated_monthly_savings"]),
            risk=r["risk"],
        )
        for r in response.get("recommendations", [])
    ]

    return ChatResponse(
        answer=response["answer"],
        plan=result.get("plan", []),
        tool_calls=tool_calls,
        findings=findings,
        evidence=evidence,
        recommendations=recommendations,
        confidence=float(response.get("confidence", 0.5)),
        requires_human_review=bool(response.get("requires_human_review", False)),
        follow_ups=response.get("follow_ups"),
        intent=result.get("intent", "generic"),
        source=result.get("source", "rules"),
        llm_error=result.get("llm_error"),
        run_id=str(result.get("run_id", "")),
    )