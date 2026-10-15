import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )

    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, server_default=func.now())
    category: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(300))
    details: Mapped[str] = mapped_column(String(1000))
    event_metadata: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)

    tenant: Mapped["Tenant"] = relationship(back_populates="audit_events")


from app.models.tenant import Tenant  # noqa: E402