import uuid
from datetime import date, datetime

from pydantic import Field

from app.schemas.base import CamelModel


class ResolvedRange(CamelModel):
    start: date
    end: date


class TopMover(CamelModel):
    name: str
    delta_amount: float
    delta_pct: float


class CostSummaryOut(CamelModel):
    current_spend: float
    previous_spend: float
    change_amount: float
    change_pct: float
    top_mover: TopMover | None
    currency: str = "USD"
    period: ResolvedRange


class CostTrendPoint(CamelModel):
    date: date
    aws: float
    azure: float
    total: float


class CostBreakdownRow(CamelModel):
    id: str
    name: str
    provider: str
    spend: float
    change_pct: float
    share: float


class CostAnomalyOut(CamelModel):
    id: uuid.UUID
    service: str
    account: str
    provider: str
    detected_at: datetime
    delta_pct: float
    delta_amount: float
    description: str
    severity: str


class ResourceCostPoint(CamelModel):
    date: date
    cost: float