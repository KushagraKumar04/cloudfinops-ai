import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    cloud_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cloud_accounts.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resources.id", ondelete="SET NULL"), index=True, nullable=True
    )

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    provider: Mapped[str] = mapped_column(String(16), index=True)
    service: Mapped[str] = mapped_column(String(64), index=True)

    delta_pct: Mapped[float] = mapped_column(Numeric(8, 2))
    delta_amount: Mapped[float] = mapped_column(Numeric(18, 2))
    baseline_value: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    observed_value: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    description: Mapped[str] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())