import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)


class NotificationRule(Base):
    __tablename__ = "notification_rules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_notification_rule_tenant_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_notification_rules_tenant"),
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(500), default="")

    event_type: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(16), index=True)
    destination: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    min_severity: Mapped[str] = mapped_column(String(16), default="info")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fire_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    deliveries: Mapped[list["Notification"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE", name="fk_notifications_tenant"),
        index=True,
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("notification_rules.id", ondelete="SET NULL", name="fk_notifications_rule"),
        index=True,
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    channel: Mapped[str] = mapped_column(String(16), index=True)

    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(String(4000), default="")
    destination: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(24), index=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    rule: Mapped["NotificationRule | None"] = relationship(back_populates="deliveries")