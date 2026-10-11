import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant, get_current_user, require_permission
from app.services.permissions import Permission
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.commitment import CommitmentRecommendation
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.commitment import (
    CommitmentApprovalOut,
    CommitmentDecisionIn,
    CommitmentListOut,
    CommitmentOut,
    CommitmentRecommendationList,
    CommitmentRecommendationOut,
    CoverageSummary,
)
from app.services.commitments import (
    account_name_map,
    apply_decision,
    coverage_snapshot,
    get_recommendation,
    list_commitments,
    list_recommendations,
)

router = APIRouter(prefix="/commitments", tags=["commitments"])


def _commitment_to_out(commitment, account_name: str) -> CommitmentOut:
    base = CommitmentOut.model_validate(commitment)
    base.account_name = account_name
    return base


def _recommendation_to_out(rec: CommitmentRecommendation, account_name: str) -> CommitmentRecommendationOut:
    base = CommitmentRecommendationOut.model_validate(rec)
    base.account_name = account_name
    base.history = [CommitmentApprovalOut.model_validate(a) for a in sorted(rec.approvals, key=lambda x: x.created_at)]
    return base


@router.get("/summary", response_model=CoverageSummary)
def commitment_summary(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
) -> CoverageSummary:
    snap = coverage_snapshot(db, tenant.id, provider)
    potential = 0.0
    recs = list_recommendations(db, tenant.id, status="pending", provider=provider)
    for r in recs:
        potential += float(r.estimated_monthly_savings)
    return CoverageSummary(
        total_monthly_spend=snap["total_monthly_spend"],
        eligible_monthly_spend=snap["eligible_monthly_spend"],
        covered_monthly_spend=snap["covered_monthly_spend"],
        uncovered_monthly_spend=snap["uncovered_monthly_spend"],
        coverage_pct=snap["coverage_pct"],
        active_commitments=snap["active_commitments"],
        expiring_within_60_days=snap["expiring_within_60_days"],
        average_utilization_pct=snap["average_utilization_pct"],
        realized_monthly_savings=snap["realized_monthly_savings"],
        potential_monthly_savings=round(potential, 2),
        on_demand_risk_pct=snap["on_demand_risk_pct"],
    )


@router.get("", response_model=CommitmentListOut)
def list_commitments_endpoint(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
) -> CommitmentListOut:
    rows = list_commitments(db, tenant.id, provider)
    names = account_name_map(db, tenant.id, {r.cloud_account_id for r in rows})
    items = [_commitment_to_out(r, names.get(r.cloud_account_id, "")) for r in rows]
    return CommitmentListOut(items=items, total=len(items))


@router.get("/recommendations", response_model=CommitmentRecommendationList)
def list_recommendations_endpoint(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    status: str | None = Query(default="pending"),
    provider: str | None = Query(default=None),
) -> CommitmentRecommendationList:
    rows = list_recommendations(db, tenant.id, status=status, provider=provider)
    names = account_name_map(db, tenant.id, {r.cloud_account_id for r in rows})
    items = [_recommendation_to_out(r, names.get(r.cloud_account_id, "")) for r in rows]

    totals = {
        "pending": sum(1 for r in items if r.status == "pending"),
        "approved": sum(1 for r in items if r.status == "approved"),
        "rejected": sum(1 for r in items if r.status == "rejected"),
        "deferred": sum(1 for r in items if r.status == "deferred"),
        "pending_savings": round(sum(r.estimated_monthly_savings for r in items if r.status == "pending"), 2),
        "approved_savings": round(sum(r.estimated_monthly_savings for r in items if r.status == "approved"), 2),
    }

    return CommitmentRecommendationList(items=items, total=len(items), totals=totals)


@router.get("/recommendations/{recommendation_id}", response_model=CommitmentRecommendationOut)
def get_recommendation_endpoint(
    recommendation_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> CommitmentRecommendationOut:
    rec = get_recommendation(db, tenant.id, recommendation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Commitment recommendation not found")
    names = account_name_map(db, tenant.id, {rec.cloud_account_id})
    return _recommendation_to_out(rec, names.get(rec.cloud_account_id, ""))


