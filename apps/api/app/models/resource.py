import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    cloud_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cloud_accounts.id", ondelete="CASCADE"), index=True
    )

    provider: Mapped[str] = mapped_column(String(16), index=True)
    cloud_id: Mapped[str] = mapped_column(String(500), index=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(120))
    service: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    environment: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    application: Mapped[str] = mapped_column(String(120), default="unknown")
    owner: Mapped[str] = mapped_column(String(120), default="unassigned")

    tags: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    utilization: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    series: Mapped[dict[str, list[float]]] = mapped_column(JSON, default=dict)
    metric_coverage: Mapped[float] = mapped_column(Numeric(4, 3), default=0)

    monthly_cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="resources")
    cloud_account: Mapped["CloudAccount"] = relationship(back_populates="resources")
    cost_records: Mapped[list["CostRecord"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )
    metric_records: Mapped[list["MetricRecord"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


from app.models.cloud_account import CloudAccount  # noqa: E402
from app.models.cost import CostRecord  # noqa: E402
from app.models.metric import MetricRecord  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402