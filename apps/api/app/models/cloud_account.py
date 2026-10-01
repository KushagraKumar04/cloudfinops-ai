import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CloudAccount(Base):
    __tablename__ = "cloud_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )

    provider: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(120))
    account_identifier: Mapped[str] = mapped_column(String(120))
    environment: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(24), default="connected")

    role_arn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tenant_external_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    encrypted_client_secret: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    connection_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    connection_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    read_only: Mapped[bool] = mapped_column(Boolean, default=True)
    execution_role_configured: Mapped[bool] = mapped_column(Boolean, default=False)

    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_sync_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    coverage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    resource_count: Mapped[int] = mapped_column(default=0)
    monthly_spend: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="cloud_accounts")
    resources: Mapped[list["Resource"]] = relationship(
        back_populates="cloud_account", cascade="all, delete-orphan"
    )


from app.models.resource import Resource  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402