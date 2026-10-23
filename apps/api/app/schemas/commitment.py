import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class CommitmentOut(CamelModel):
    id: uuid.UUID
    cloud_account_id: uuid.UUID
    account_name: str = ""
    provider: str
    commitment_type: str
    service: str
    region: str
    term_months: int
    payment_option: str
    monthly_cost: float = 0
    monthly_savings: float = 0
    hourly_commitment: float | None = None
    instance_count: int | None = None
    start_date: date
    end_date: date
    status: str
    utilization_pct: float = 0
    currency: str = "USD"

    @field_validator("monthly_cost", "monthly_savings", "hourly_commitment", "utilization_pct", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)


class CoverageSummary(CamelModel):
    total_monthly_spend: float
    eligible_monthly_spend: float
    covered_monthly_spend: float
    uncovered_monthly_spend: float
    coverage_pct: float
    active_commitments: int
    expiring_within_60_days: int
    average_utilization_pct: float
    realized_monthly_savings: float
    potential_monthly_savings: float
    on_demand_risk_pct: float


class CommitmentApprovalOut(CamelModel):
    id: uuid.UUID
    approver: str
    decision: str
    reason: str | None = None
    created_at: datetime


class CommitmentRecommendationOut(CamelModel):
    id: uuid.UUID
    cloud_account_id: uuid.UUID
    account_name: str = ""
    provider: str
    commitment_type: str
    service: str
    region: str
    title: str
    summary: str
    rationale: str = ""
    term_months: int
    payment_option: str
    recommended_hourly_commitment: float | None = None
    recommended_instance_count: int | None = None
    estimated_monthly_cost: float = 0
    estimated_monthly_savings: float = 0
    estimated_annual_savings: float = 0
    coverage_before_pct: float = 0
    coverage_after_pct: float = 0
    break_even_months: float = 0
    risk: str
    risk_reasons: list[str] = Field(default_factory=list)
    confidence: float = 0.75
    status: str
    evidence: list[dict[str, str]] = Field(default_factory=list)
    impact: dict[str, str] = Field(default_factory=dict)
    currency: str = "USD"
    created_at: datetime
    updated_at: datetime
    history: list[CommitmentApprovalOut] = Field(default_factory=list)

    @field_validator(
        "estimated_monthly_cost",
        "estimated_monthly_savings",
        "estimated_annual_savings",
        "recommended_hourly_commitment",
        "coverage_before_pct",
        "coverage_after_pct",
        "break_even_months",
        "confidence",
        mode="before",
    )
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return 0
        return float(v)


class CommitmentRecommendationList(CamelModel):
    items: list[CommitmentRecommendationOut]
    total: int
    totals: dict[str, Any] = Field(default_factory=dict)


class CommitmentDecisionIn(CamelModel):
    reason: str | None = None


class CommitmentListOut(CamelModel):
    items: list[CommitmentOut]
    total: int