import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_tenant
from app.services.notifications import dispatch_event
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.cloud_account import CloudAccount
from app.models.execution import Approval
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.tenant import Tenant
from app.schemas.recommendation import (
    DecisionIn,
    EvidenceOut,
    HistoryEntry,
    ImpactOut,
    RecommendationListOut,
    RecommendationOut,
    RecommendationTotals,
    StateKV,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _build_history(rec: Recommendation) -> list[HistoryEntry]:
    events: list[HistoryEntry] = [
        HistoryEntry(at=rec.created_at, actor="finops-engine", action="Recommendation created")
    ]
    for a in sorted(rec.approvals, key=lambda x: x.created_at):
        label = {
            "approve": "Approved",
            "reject": "Rejected",
            "defer": "Deferred",
        }.get(a.decision, a.decision.capitalize())
        events.append(HistoryEntry(at=a.created_at, actor=a.approver, action=label, reason=a.reason))
    return events


def _to_out(rec: Recommendation, resource: Resource | None, account: CloudAccount | None) -> RecommendationOut:
    base = RecommendationOut.model_validate(rec)
    if resource is not None:
        base.resource_name = resource.name
        base.resource_type = resource.type
        base.provider = resource.provider
        base.region = resource.region
        base.environment = resource.environment
    if account is not None:
        base.account_name = account.name
    base.impact = ImpactOut(**(rec.impact or {}))
    base.evidence = [EvidenceOut(**{"label": e.label, "value": e.value, "source": e.source}) for e in rec.evidence]
    base.current_state = [StateKV(**kv) for kv in (rec.current_state or [])]
    base.proposed_state = [StateKV(**kv) for kv in (rec.proposed_state or [])]
    base.history = _build_history(rec)
    return base


def _load_recommendation(db: Session, tenant_id: uuid.UUID, rec_id: uuid.UUID) -> Recommendation:
    stmt = (
        select(Recommendation)
        .options(selectinload(Recommendation.evidence), selectinload(Recommendation.approvals))
        .where(Recommendation.id == rec_id, Recommendation.tenant_id == tenant_id)
    )
    rec = db.execute(stmt).scalar_one_or_none()
    if rec is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


@router.get("", response_model=RecommendationListOut)
def list_recommendations(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    q: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    type: str | None = Query(default=None),
    risk: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort_key: str = Query(default="createdAt"),
    sort_dir: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> RecommendationListOut:
    base = (
        select(Recommendation)
        .options(selectinload(Recommendation.evidence), selectinload(Recommendation.approvals))
        .where(Recommendation.tenant_id == tenant.id)
    )

    if q:
        term = f"%{q.strip().lower()}%"
        base = base.where(
            or_(
                func.lower(Recommendation.title).like(term),
                func.lower(Recommendation.summary).like(term),
                func.lower(Recommendation.type_label).like(term),
            )
        )
    if risk and risk != "all":
        base = base.where(Recommendation.risk == risk)
    if status and status != "all":
        base = base.where(Recommendation.status == status)
    if type and type != "all":
        base = base.where(Recommendation.type == type)

    rows = list(db.execute(base).scalars().all())

    resource_ids = {r.resource_id for r in rows}
    resources: dict[uuid.UUID, Resource] = {}
    accounts: dict[uuid.UUID, CloudAccount] = {}
    if resource_ids:
        for r in db.execute(select(Resource).where(Resource.id.in_(resource_ids))).scalars().all():
            resources[r.id] = r
        account_ids = {r.cloud_account_id for r in resources.values()}
        if account_ids:
            for a in db.execute(select(CloudAccount).where(CloudAccount.id.in_(account_ids))).scalars().all():
                accounts[a.id] = a

    if provider and provider != "all":
        rows = [r for r in rows if resources.get(r.resource_id) and resources[r.resource_id].provider == provider]

    if q:
        term = q.strip().lower()
        rows = [
            r
            for r in rows
            if term in r.title.lower()
            or term in r.summary.lower()
            or term in r.type_label.lower()
            or (resources.get(r.resource_id) and term in resources[r.resource_id].name.lower())
        ]

    risk_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "BLOCKED": 3}
    reverse = sort_dir == "desc"
    if sort_key == "estimatedMonthlySavings":
        rows.sort(key=lambda r: float(r.estimated_monthly_savings), reverse=reverse)
    elif sort_key == "risk":
        rows.sort(key=lambda r: risk_rank.get(r.risk, 0), reverse=reverse)
    elif sort_key == "confidence":
        rows.sort(key=lambda r: float(r.confidence), reverse=reverse)
    else:
        rows.sort(key=lambda r: r.created_at, reverse=reverse)

    all_rows = rows
    total = len(all_rows)
    start = (page - 1) * page_size
    page_rows = all_rows[start : start + page_size]

    items = [
        _to_out(r, resources.get(r.resource_id), accounts.get(resources[r.resource_id].cloud_account_id) if resources.get(r.resource_id) else None)
        for r in page_rows
    ]

    totals = RecommendationTotals(
        pending=sum(1 for r in all_rows if r.status == "pending"),
        approved=sum(1 for r in all_rows if r.status == "approved"),
        rejected=sum(1 for r in all_rows if r.status == "rejected"),
        deferred=sum(1 for r in all_rows if r.status == "deferred"),
        savings_pending=round(sum(float(r.estimated_monthly_savings) for r in all_rows if r.status == "pending"), 2),
        savings_approved=round(sum(float(r.estimated_monthly_savings) for r in all_rows if r.status == "approved"), 2),
    )

    return RecommendationListOut(items=items, total=total, page=page, page_size=page_size, totals=totals)


@router.get("/{recommendation_id}", response_model=RecommendationOut)
def get_recommendation(
    recommendation_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RecommendationOut:
    rec = _load_recommendation(db, tenant.id, recommendation_id)
    resource = db.get(Resource, rec.resource_id)
    account = db.get(CloudAccount, resource.cloud_account_id) if resource else None
    return _to_out(rec, resource, account)


def _decide(
    db: Session,
    tenant: Tenant,
    recommendation_id: uuid.UUID,
    decision: str,
    reason: str | None,
) -> RecommendationOut:
    rec = _load_recommendation(db, tenant.id, recommendation_id)

    if rec.status != "pending":
        raise HTTPException(status_code=409, detail=f"Recommendation is {rec.status}")
    if rec.risk == "BLOCKED":
        raise HTTPException(status_code=409, detail="Recommendation is blocked by policy")

    status_map = {"approve": "approved", "reject": "rejected", "defer": "deferred"}
    new_status = status_map[decision]

    db.add(
        Approval(
            recommendation_id=rec.id,
            approver="demo.user@acme.io",
            decision=decision,
            reason=reason,
        )
    )
    rec.status = new_status
    rec.updated_at = datetime.now(UTC)

    db.add(
        AuditEvent(
            tenant_id=tenant.id,
            at=datetime.now(UTC),
            category="recommendation",
            severity="info",
            actor="demo.user@acme.io",
            action=decision.capitalize(),
            subject=f"{rec.id} · {rec.title}",
            details=reason or f"{decision}d via API",
            event_metadata=[
                {"key": "recommendation_id", "value": str(rec.id)},
                {"key": "decision", "value": decision},
            ],
        )
    )
    db.commit()
    db.refresh(rec)

    if decision == "approve" and rec.risk == "HIGH":
        dispatch_event(
            db,
            tenant.id,
            "recommendation.high_risk",
            "warning",
            f"High-risk recommendation approved: {rec.title}",
            f"Approver: demo.user@acme.io\nRecommendation: {rec.id}\nRisk: {rec.risk}\n"
            f"Estimated savings: ${float(rec.estimated_monthly_savings):,.2f}/mo",
            {"recommendation_id": str(rec.id), "risk": rec.risk},
        )

    resource = db.get(Resource, rec.resource_id)
    account = db.get(CloudAccount, resource.cloud_account_id) if resource else None
    return _to_out(rec, resource, account)


@router.post("/{recommendation_id}/approve", response_model=RecommendationOut)
def approve_recommendation(
    recommendation_id: uuid.UUID,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RecommendationOut:
    return _decide(db, tenant, recommendation_id, "approve", payload.reason)


@router.post("/{recommendation_id}/reject", response_model=RecommendationOut)
def reject_recommendation(
    recommendation_id: uuid.UUID,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RecommendationOut:
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Reason is required for rejection")
    return _decide(db, tenant, recommendation_id, "reject", payload.reason)


@router.post("/{recommendation_id}/defer", response_model=RecommendationOut)
def defer_recommendation(
    recommendation_id: uuid.UUID,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> RecommendationOut:
    return _decide(db, tenant, recommendation_id, "defer", payload.reason)