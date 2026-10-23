from datetime import date, datetime

from app.schemas.base import CamelModel


class ForecastPoint(CamelModel):
    date: date
    actual: float | None
    forecast: float | None
    lower: float | None
    upper: float | None


class ForecastSummaryOut(CamelModel):
    month_end_projection: float
    month_end_lower: float
    month_end_upper: float
    budget: float
    budget_utilization: float
    breach_probability: float
    trend_direction: str
    trend_pct: float
    confidence: float
    currency: str = "USD"
    horizon: str
    as_of: datetime


class ServiceForecastOut(CamelModel):
    name: str
    provider: str
    current: float
    projected: float
    change_pct: float
    share: float


class ForecastScenarioOut(CamelModel):
    id: str
    label: str
    description: str
    monthly_delta: float
    new_projection: float
    budget_status: str
    actions: list[str]