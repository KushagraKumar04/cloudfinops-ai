import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=func.now(),
    )

    cloud_accounts: Mapped[list["CloudAccount"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    resources: Mapped[list["Resource"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    cost_records: Mapped[list["CostRecord"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


from app.models.audit import AuditEvent  # noqa: E402
from app.models.cloud_account import CloudAccount  # noqa: E402
from app.models.cost import CostRecord  # noqa: E402
from app.models.resource import Resource  # noqa: E402
from app.models.user import TeamMember  # noqa: E402