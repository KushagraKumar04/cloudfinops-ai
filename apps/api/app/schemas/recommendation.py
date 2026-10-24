import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class EvidenceOut(CamelModel):
    label: str
    value: str
    source: str


class StateKV(CamelModel):
    key: str
    value: str


class HistoryEntry(CamelModel):
    at: datetime
    actor: str
    action: str
    reason: str | None = None


class ImpactOut(CamelModel):
    availability: str = ""
    security: str = ""
    operational: str = ""


class RecommendationOut(CamelModel):
    id: uuid.UUID
    resource_id: uuid.UUID
    resource_name: str = ""
    resource_type: str = ""
    provider: str = ""
    account_name: str = ""
    region: str = ""
    environment: str = ""
    type: str
    type_label: str
    title: str
    summary: str
    status: str
    risk: str
    risk_reasons: list[str] = Field(default_factory=list)
    confidence: float = 0
    current_monthly_cost: float = 0
    estimated_monthly_cost: float = 0
    estimated_monthly_savings: float = 0
    currency: str = "USD"
    calculation_basis: list[str] = Field(default_factory=list)
    evidence: list[EvidenceOut] = Field(default_factory=list)
    current_state: list[StateKV] = Field(default_factory=list)
    proposed_state: list[StateKV] = Field(default_factory=list)
    impact: ImpactOut = Field(default_factory=ImpactOut)
    implementation_plan: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    history: list[HistoryEntry] = Field(default_factory=list)

    @field_validator(
        "confidence",
        "current_monthly_cost",
        "estimated_monthly_cost",
        "estimated_monthly_savings",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)


class RecommendationTotals(CamelModel):
    pending: int
    approved: int
    rejected: int
    deferred: int
    savings_pending: float
    savings_approved: float


class RecommendationListOut(CamelModel):
    items: list[RecommendationOut]
    total: int
    page: int
    page_size: int
    totals: RecommendationTotals


class DecisionIn(CamelModel):
    reason: str | None = None