import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


class AuditMetadata(CamelModel):
    key: str
    value: str


class AuditEventOut(CamelModel):
    id: uuid.UUID
    at: datetime
    category: str
    severity: str
    actor: str
    action: str
    subject: str
    details: str
    metadata: list[AuditMetadata] = Field(default_factory=list, validation_alias="event_metadata")


class AuditListOut(CamelModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int