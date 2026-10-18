import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)


class Commitment(Base):
    __tablename__ = "commitments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_commitments_tenant"), index=True
    )
    cloud_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cloud_accounts.id", ondelete="CASCADE", name="fk_commitments_cloud_account"),
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(16), index=True)
    commitment_type: Mapped[str] = mapped_column(String(32), index=True)
    service: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)

    term_months: Mapped[int] = mapped_column(Integer, default=12)
    payment_option: Mapped[str] = mapped_column(String(24), default="no_upfront")

    monthly_cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    monthly_savings: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    hourly_commitment: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    instance_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)

    utilization_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class CommitmentRecommendation(Base):
    __tablename__ = "commitment_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_commitment_recs_tenant"), index=True
    )
    cloud_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cloud_accounts.id", ondelete="CASCADE", name="fk_commitment_recs_cloud_account"),
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(16), index=True)
    commitment_type: Mapped[str] = mapped_column(String(32), index=True)
    service: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)

    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(String(1000))
    rationale: Mapped[str] = mapped_column(String(1000), default="")

    term_months: Mapped[int] = mapped_column(Integer, default=12)
    payment_option: Mapped[str] = mapped_column(String(24), default="no_upfront")

    recommended_hourly_commitment: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    recommended_instance_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    estimated_monthly_cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    estimated_monthly_savings: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    estimated_annual_savings: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    coverage_before_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    coverage_after_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0)

    break_even_months: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    risk: Mapped[str] = mapped_column(String(16), default="LOW", index=True)
    risk_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.75)

    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    evidence: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    impact: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    approvals: Mapped[list["CommitmentApproval"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class CommitmentApproval(Base):
    __tablename__ = "commitment_approvals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "commitment_recommendations.id",
            ondelete="CASCADE",
            name="fk_commitment_approvals_rec",
        ),
        index=True,
    )
    approver: Mapped[str] = mapped_column(String(200))
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    recommendation: Mapped["CommitmentRecommendation"] = relationship(back_populates="approvals")