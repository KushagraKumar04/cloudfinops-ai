import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.services.notifications import dispatch_event
from app.db.session import get_db
from app.models.execution import Execution
from app.models.tenant import Tenant
from app.schemas.execution import ExecutionCreateIn, ExecutionListOut, ExecutionOut
from app.services.executor import ExecutionError, create_execution, rollback_execution

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("", response_model=ExecutionListOut)
def list_executions(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    recommendation_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ExecutionListOut:
    stmt = select(Execution).where(Execution.tenant_id == tenant.id)
    if recommendation_id:
        stmt = stmt.where(Execution.recommendation_id == recommendation_id)
    rows = list(db.execute(stmt).scalars().all())
    rows.sort(key=lambda e: e.created_at, reverse=True)
    total = len(rows)
    start = (page - 1) * page_size
    items = [ExecutionOut.model_validate(e) for e in rows[start : start + page_size]]
    return ExecutionListOut(items=items, total=total)


@router.get("/{execution_id}", response_model=ExecutionOut)
def get_execution(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ExecutionOut:
    execution = db.get(Execution, execution_id)
    if execution is None or execution.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionOut.model_validate(execution)


@router.post("", response_model=ExecutionOut, status_code=201)
def create(
    payload: ExecutionCreateIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ExecutionOut:
    try:
        execution = create_execution(db, tenant, payload.recommendation_id, payload.mode)
    except ExecutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if execution.status == "blocked":
        reasons = execution.policy_result.get("reasons", []) if execution.policy_result else []
        dispatch_event(
            db,
            tenant.id,
            "policy.blocked",
            "warning",
            f"Execution blocked: {execution.action}",
            f"Recommendation {execution.recommendation_id} was blocked by policy.\n\n"
            + "\n".join(f"- {r}" for r in reasons),
            {"execution_id": str(execution.id), "action": execution.action},
        )

    return ExecutionOut.model_validate(execution)


@router.post("/{execution_id}/rollback", response_model=ExecutionOut)
def rollback(
    execution_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ExecutionOut:
    try:
        execution = rollback_execution(db, tenant, execution_id)
    except ExecutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ExecutionOut.model_validate(execution)