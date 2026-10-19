import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CostRecord(Base):
    __tablename__ = "cost_records"

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

    date: Mapped[date] = mapped_column(Date, index=True)
    provider: Mapped[str] = mapped_column(String(16), index=True)
    service: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)

    cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    usage_quantity: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    usage_unit: Mapped[str] = mapped_column(String(32), default="")
    tags: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    tenant: Mapped["Tenant"] = relationship(back_populates="cost_records")
    resource: Mapped["Resource | None"] = relationship(back_populates="cost_records")


from app.models.resource import Resource  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402