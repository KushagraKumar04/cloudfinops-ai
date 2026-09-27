import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )

    approver: Mapped[str] = mapped_column(String(200))
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recommendation: Mapped["Recommendation"] = relationship(back_populates="approvals")


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )

    action: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(16), default="dry_run")
    status: Mapped[str] = mapped_column(String(24), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)

    executed_by: Mapped[str] = mapped_column(String(200), default="")

    policy_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    preconditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    dry_run_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    verification: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    rollback_reference: Mapped[str | None] = mapped_column(String(300), nullable=True)
    rollback_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    rollback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recommendation: Mapped["Recommendation"] = relationship(back_populates="executions")


from app.models.recommendation import Recommendation  # noqa: E402