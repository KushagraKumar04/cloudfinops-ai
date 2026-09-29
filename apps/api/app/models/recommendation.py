import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"), index=True
    )

    type: Mapped[str] = mapped_column(String(64), index=True)
    type_label: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(String(1000))

    status: Mapped[str] = mapped_column(String(16), index=True, default="pending")
    risk: Mapped[str] = mapped_column(String(16), index=True)
    risk_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3))

    current_monthly_cost: Mapped[float] = mapped_column(Numeric(18, 2))
    estimated_monthly_cost: Mapped[float] = mapped_column(Numeric(18, 2))
    estimated_monthly_savings: Mapped[float] = mapped_column(Numeric(18, 2), index=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    calculation_basis: Mapped[list[str]] = mapped_column(JSON, default=list)
    current_state: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    proposed_state: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    impact: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    implementation_plan: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    resource: Mapped["Resource"] = relationship()
    evidence: Mapped[list["RecommendationEvidence"]] = relationship(
        back_populates="recommendation",
        cascade="all, delete-orphan",
        order_by="RecommendationEvidence.position",
    )
    approvals: Mapped[list["Approval"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )
    executions: Mapped[list["Execution"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class RecommendationEvidence(Base):
    __tablename__ = "recommendation_evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )

    position: Mapped[int] = mapped_column(Integer, default=0)
    label: Mapped[str] = mapped_column(String(120))
    value: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(120))

    recommendation: Mapped["Recommendation"] = relationship(back_populates="evidence")


from app.models.execution import Approval, Execution  # noqa: E402
from app.models.resource import Resource  # noqa: E402