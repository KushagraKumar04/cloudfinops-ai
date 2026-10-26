import uuid
from typing import Any

from pydantic import Field

from app.schemas.base import CamelModel


class BulkRecommendationDecisionIn(CamelModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    action: str = Field(pattern="^(approve|reject|defer)$")
    reason: str | None = Field(default=None, max_length=500)


class BulkActionResult(CamelModel):
    succeeded: list[uuid.UUID] = Field(default_factory=list)
    failed: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    succeeded_count: int = 0
    failed_count: int = 0


class BulkAccountIdsIn(CamelModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)