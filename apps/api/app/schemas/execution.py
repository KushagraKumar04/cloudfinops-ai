import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel


class ExecutionCreateIn(CamelModel):
    recommendation_id: uuid.UUID
    mode: str = Field(default="dry_run", pattern="^(dry_run|apply)$")


class ExecutionOut(CamelModel):
    id: uuid.UUID
    recommendation_id: uuid.UUID
    action: str
    mode: str
    status: str
    idempotency_key: str
    executed_by: str
    policy_result: dict[str, Any] = Field(default_factory=dict)
    preconditions: list[dict[str, Any]] = Field(default_factory=list)
    dry_run_result: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    rollback_reference: str | None = None
    rollback_status: str | None = None
    rollback_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class ExecutionListOut(CamelModel):
    items: list[ExecutionOut]
    total: int