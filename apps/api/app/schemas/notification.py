import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel


class RuleDestination(CamelModel):
    to: list[str] | None = None
    cc: list[str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None


class RuleIn(CamelModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=500)
    event_type: str = Field(min_length=1, max_length=64)
    channel: str = Field(pattern="^(email|webhook)$")
    destination: dict[str, Any] = Field(default_factory=dict)
    min_severity: str = Field(default="info", pattern="^(info|warning|critical)$")
    enabled: bool = True


class RuleUpdate(CamelModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    event_type: str | None = Field(default=None, max_length=64)
    channel: str | None = Field(default=None, pattern="^(email|webhook)$")
    destination: dict[str, Any] | None = None
    min_severity: str | None = Field(default=None, pattern="^(info|warning|critical)$")
    enabled: bool | None = None


class RuleOut(CamelModel):
    id: uuid.UUID
    name: str
    description: str = ""
    event_type: str
    channel: str
    destination: dict[str, Any] = Field(default_factory=dict)
    min_severity: str = "info"
    enabled: bool = True
    last_fired_at: datetime | None = None
    fire_count: int = 0
    created_at: datetime
    updated_at: datetime


class NotificationOut(CamelModel):
    id: uuid.UUID
    rule_id: uuid.UUID | None = None
    event_type: str
    severity: str
    channel: str
    subject: str
    body: str = ""
    destination: dict[str, Any] = Field(default_factory=dict)
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    status: str
    error: str | None = None
    attempt: int = 1
    duration_ms: int = 0
    read_at: datetime | None = None
    created_at: datetime


class NotificationListOut(CamelModel):
    items: list[NotificationOut]
    total: int
    unread: int = 0
    totals: dict[str, int] = Field(default_factory=dict)


class RuleListOut(CamelModel):
    items: list[RuleOut]
    total: int
    event_types: dict[str, str] = Field(default_factory=dict)


class DispatchIn(CamelModel):
    event_type: str = Field(min_length=1, max_length=64)
    severity: str = Field(default="info", pattern="^(info|warning|critical)$")
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(default="", max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)