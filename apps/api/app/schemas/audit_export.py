import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel


class AuditExportCreateIn(CamelModel):
    format: str = Field(default="csv", pattern="^(csv|json)$")
    q: str | None = None
    category: str | None = None
    severity: str | None = None
    start: date | None = None
    end: date | None = None


class AuditExportOut(CamelModel):
    id: uuid.UUID
    format: str
    storage_backend: str
    size_bytes: int = 0
    record_count: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)
    status: str
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    expires_at: datetime
    deleted_at: datetime | None = None
    download_url: str | None = None


class AuditExportListOut(CamelModel):
    items: list[AuditExportOut]
    total: int


class AuditExportCleanupOut(CamelModel):
    removed: int