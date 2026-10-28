import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.cloud_account import CloudAccount
from app.models.commitment import Commitment, CommitmentRecommendation
from app.models.cost import CostRecord

ELIGIBLE_SERVICES = {
    "AWS": ["EC2", "RDS", "EKS", "ElastiCache", "Redshift", "Lambda"],
    "Azure": ["Azure VMs", "Azure SQL", "Azure Disk", "App Service", "Functions"],
}

PROVIDER_DISCOUNT = {
    ("AWS", "reserved_instance", 12): 0.32,
    ("AWS", "reserved_instance", 36): 0.50,
    ("AWS", "savings_plan", 12): 0.17,
    ("AWS", "savings_plan", 36): 0.27,
    ("Azure", "reserved_vm", 12): 0.31,
    ("Azure", "reserved_vm", 36): 0.48,
}


def coverage_snapshot(
    db: Session, tenant_id: uuid.UUID, provider: str | None = None
) -> dict[str, float]:
    spend_stmt = select(
        func.coalesce(func.sum(CostRecord.cost), 0),
        CostRecord.service,
        CostRecord.provider,
    ).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.date >= date.today() - timedelta(days=29),
    )
    if provider and provider != "all":
        spend_stmt = spend_stmt.where(CostRecord.provider == provider)
    spend_stmt = spend_stmt.group_by(CostRecord.service, CostRecord.provider)

    total_spend = 0.0
    eligible_spend = 0.0
    per_provider_eligible: dict[str, float] = {}
    for total, service, prov in db.execute(spend_stmt).all():
        amount = float(total or 0)
        total_spend += amount
        if service in ELIGIBLE_SERVICES.get(prov, []):
            eligible_spend += amount
            per_provider_eligible[prov] = per_provider_eligible.get(prov, 0.0) + amount

    commitment_stmt = select(
        func.coalesce(func.sum(Commitment.monthly_cost), 0),
        func.coalesce(func.avg(Commitment.utilization_pct), 0),
        func.coalesce(func.sum(Commitment.monthly_savings), 0),
    ).where(
        Commitment.tenant_id == tenant_id,
        Commitment.status == "active",
    )
    if provider and provider != "all":
        commitment_stmt = commitment_stmt.where(Commitment.provider == provider)
    row = db.execute(commitment_stmt).one()
    covered_spend = float(row[0] or 0)
    avg_util = float(row[1] or 0)
    realized_savings = float(row[2] or 0)

    coverage_pct = (covered_spend / eligible_spend) if eligible_spend > 0 else 0.0
    uncovered = max(0.0, eligible_spend - covered_spend)

    expiring_stmt = select(func.count(Commitment.id)).where(
        Commitment.tenant_id == tenant_id,
        Commitment.status == "active",
        Commitment.end_date <= date.today() + timedelta(days=60),
    )
    if provider and provider != "all":
        expiring_stmt = expiring_stmt.where(Commitment.provider == provider)
    expiring_count = int(db.execute(expiring_stmt).scalar() or 0)

    active_count_stmt = select(func.count(Commitment.id)).where(
        Commitment.tenant_id == tenant_id,
        Commitment.status == "active",
    )
    if provider and provider != "all":
        active_count_stmt = active_count_stmt.where(Commitment.provider == provider)
    active_count = int(db.execute(active_count_stmt).scalar() or 0)

    return {
        "total_monthly_spend": round(total_spend, 2),
        "eligible_monthly_spend": round(eligible_spend, 2),
        "covered_monthly_spend": round(covered_spend, 2),
        "uncovered_monthly_spend": round(uncovered, 2),
        "coverage_pct": round(coverage_pct, 4),
        "active_commitments": active_count,
        "expiring_within_60_days": expiring_count,
        "average_utilization_pct": round(avg_util, 4),
        "realized_monthly_savings": round(realized_savings, 2),
        "on_demand_risk_pct": round(max(0.0, 1 - coverage_pct), 4),
        "per_provider_eligible": per_provider_eligible,
    }


def list_commitments(
    db: Session, tenant_id: uuid.UUID, provider: str | None = None
) -> list[Commitment]:
    stmt = select(Commitment).where(Commitment.tenant_id == tenant_id)
    if provider and provider != "all":
        stmt = stmt.where(Commitment.provider == provider)
    stmt = stmt.order_by(Commitment.end_date.asc())
    return list(db.execute(stmt).scalars().all())


def list_recommendations(
    db: Session,
    tenant_id: uuid.UUID,
    status: str | None = None,
    provider: str | None = None,
) -> list[CommitmentRecommendation]:
    stmt = (
        select(CommitmentRecommendation)
        .options(selectinload(CommitmentRecommendation.approvals))
        .where(CommitmentRecommendation.tenant_id == tenant_id)
    )
    if status and status != "all":
        stmt = stmt.where(CommitmentRecommendation.status == status)
    if provider and provider != "all":
        stmt = stmt.where(CommitmentRecommendation.provider == provider)
    stmt = stmt.order_by(CommitmentRecommendation.estimated_monthly_savings.desc())
    return list(db.execute(stmt).scalars().all())


def get_recommendation(
    db: Session, tenant_id: uuid.UUID, recommendation_id: uuid.UUID
) -> CommitmentRecommendation | None:
    stmt = (
        select(CommitmentRecommendation)
        .options(selectinload(CommitmentRecommendation.approvals))
        .where(
            CommitmentRecommendation.id == recommendation_id,
            CommitmentRecommendation.tenant_id == tenant_id,
        )
    )
    return db.execute(stmt).scalar_one_or_none()


def account_name_map(
    db: Session, tenant_id: uuid.UUID, account_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not account_ids:
        return {}
    stmt = select(CloudAccount).where(
        CloudAccount.tenant_id == tenant_id,
        CloudAccount.id.in_(account_ids),
    )
    return {a.id: a.name for a in db.execute(stmt).scalars().all()}


def apply_decision(
    db: Session,
    recommendation: CommitmentRecommendation,
    decision: str,
    reason: str | None,
    approver: str,
) -> CommitmentRecommendation:
    from app.models.commitment import CommitmentApproval

    status_map = {"approve": "approved", "reject": "rejected", "defer": "deferred"}
    new_status = status_map[decision]

    approval = CommitmentApproval(
        recommendation_id=recommendation.id,
        approver=approver,
        decision=decision,
        reason=reason,
    )
    db.add(approval)
    recommendation.status = new_status
    db.commit()
    db.refresh(recommendation)
    return recommendation


def compute_break_even(
    monthly_cost: float,
    monthly_savings: float,
    term_months: int,
) -> float:
    if monthly_savings <= 0:
        return float(term_months)
    return round(min(term_months, 0.0 if monthly_cost <= 0 else 0.0), 2)