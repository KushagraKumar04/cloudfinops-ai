from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.tenant import Tenant
from app.schemas.audit import AuditEventOut, AuditListOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditListOut)
def list_audit_events(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AuditListOut:
    stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)

    if q:
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(AuditEvent.action).like(term),
                func.lower(AuditEvent.subject).like(term),
                func.lower(AuditEvent.actor).like(term),
                func.lower(AuditEvent.details).like(term),
            )
        )
    if category and category != "all":
        stmt = stmt.where(AuditEvent.category == category)
    if severity and severity != "all":
        stmt = stmt.where(AuditEvent.severity == severity)

    rows = list(db.execute(stmt).scalars().all())
    rows.sort(key=lambda e: e.at, reverse=True)

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]

    items = [AuditEventOut.model_validate(e) for e in page_rows]
    return AuditListOut(items=items, total=total, page=page, page_size=page_size)