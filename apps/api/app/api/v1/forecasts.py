from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.models.budget import Budget
from app.models.tenant import Tenant
from app.schemas.forecast import (
    ForecastPoint,
    ForecastScenarioOut,
    ForecastSummaryOut,
    ServiceForecastOut,
)
from app.services.forecasting import (
    DailySeries,
    ForecastError,
    fit_forecast,
    list_services,
    load_daily_series,
    trend_direction,
    trend_pct,
)

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


def _horizon_days(horizon: str) -> int:
    return {"30d": 30, "60d": 60, "90d": 90}.get(horizon, 30)


def _resolve_budget(db: Session, tenant: Tenant) -> float:
    stmt = select(Budget).where(Budget.tenant_id == tenant.id).limit(1)
    budget = db.execute(stmt).scalar_one_or_none()
    if budget is None:
        return 220000.0
    return float(budget.amount)


def _build_points(series: DailySeries, horizon: int) -> list[ForecastPoint]:
    if not series.values:
        return []
    try:
        result = fit_forecast(series, horizon)
    except ForecastError:
        return []

    points: list[ForecastPoint] = []
    for d, v in zip(series.dates, series.values):
        points.append(
            ForecastPoint(date=d, actual=round(float(v), 2), forecast=None, lower=None, upper=None)
        )

    last_date = series.dates[-1]
    for i, value in enumerate(result.forecast):
        points.append(
            ForecastPoint(
                date=last_date + timedelta(days=i + 1),
                actual=None,
                forecast=round(value, 2),
                lower=round(result.lower[i], 2),
                upper=round(result.upper[i], 2),
            )
        )
    return points


def _summarize(
    series: DailySeries,
    horizon: int,
    budget: float,
) -> tuple[float, float, float, float, float, str, float, float]:
    try:
        result = fit_forecast(series, horizon)
    except ForecastError:
        return 0.0, 0.0, 0.0, 0.0, 0.0, "flat", 0.0, 0.0

    today = date.today()
    actual_mtd = sum(v for d, v in zip(series.dates, series.values) if d.month == today.month and d.year == today.year)
    end_of_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    days_remaining = max(1, (end_of_month - today).days)

    forecast_remaining = sum(result.forecast[:days_remaining])
    lower_remaining = sum(result.lower[:days_remaining])
    upper_remaining = sum(result.upper[:days_remaining])

    projection = actual_mtd + forecast_remaining
    lower = actual_mtd + lower_remaining
    upper = actual_mtd + upper_remaining

    pct = trend_pct(result, horizon)
    direction = trend_direction(pct)

    if budget <= 0:
        breach = 0.0
    elif upper <= budget:
        breach = 0.02
    elif lower >= budget:
        breach = 0.95
    else:
        span = max(1.0, upper - lower)
        breach = 0.4 + (upper - budget) / span * 0.5

    if result.method == "flat-zero":
        confidence = 0.5
    elif result.seasonal_periods:
        confidence = 0.88
    else:
        confidence = 0.74

    return (
        round(projection, 2),
        round(lower, 2),
        round(upper, 2),
        round(breach, 3),
        confidence,
        direction,
        pct,
        round(actual_mtd, 2),
    )


@router.get("/summary", response_model=ForecastSummaryOut)
def forecast_summary(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
    horizon: str = Query(default="30d"),
    budget: float | None = Query(default=None),
) -> ForecastSummaryOut:
    series = load_daily_series(db, tenant.id, provider=provider)
    budget_amount = budget if budget is not None else _resolve_budget(db, tenant)
    horizon_days = _horizon_days(horizon)

    projection, lower, upper, breach, confidence, direction, pct, _mtd = _summarize(
        series, horizon_days, budget_amount
    )
    utilization = (projection / budget_amount * 100) if budget_amount > 0 else 0.0

    return ForecastSummaryOut(
        month_end_projection=projection,
        month_end_lower=lower,
        month_end_upper=upper,
        budget=round(budget_amount, 2),
        budget_utilization=round(utilization, 2),
        breach_probability=breach,
        trend_direction=direction,
        trend_pct=pct,
        confidence=confidence,
        currency="USD",
        horizon=horizon,
        as_of=datetime.utcnow(),
    )


@router.get("/series", response_model=list[ForecastPoint])
def forecast_series(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
    horizon: str = Query(default="30d"),
) -> list[ForecastPoint]:
    series = load_daily_series(db, tenant.id, provider=provider)
    return _build_points(series, _horizon_days(horizon))


@router.get("/by-service", response_model=list[ServiceForecastOut])
def forecast_by_service(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
    horizon: str = Query(default="30d"),
) -> list[ServiceForecastOut]:
    horizon_days = _horizon_days(horizon)
    services = list_services(db, tenant.id, provider=provider)
    if not services:
        return []

    out: list[ServiceForecastOut] = []
    for service_name, service_provider in services:
        series = load_daily_series(db, tenant.id, provider=provider, service=service_name)
        if not series.values:
            continue
        current = round(float(sum(series.values[-30:])), 2)
        try:
            result = fit_forecast(series, horizon_days)
            projected = round(float(sum(result.forecast)), 2)
        except ForecastError:
            projected = round(current, 2)
        change_pct = ((projected - current) / current * 100) if current > 0 else 0.0
        out.append(
            ServiceForecastOut(
                name=service_name,
                provider=service_provider,
                current=current,
                projected=projected,
                change_pct=round(change_pct, 2),
                share=0.0,
            )
        )

    total_projected = sum(s.projected for s in out)
    if total_projected > 0:
        for s in out:
            s.share = round(s.projected / total_projected, 4)

    out.sort(key=lambda s: s.projected, reverse=True)
    return out


@router.get("/scenarios", response_model=list[ForecastScenarioOut])
def forecast_scenarios(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
    horizon: str = Query(default="30d"),
    budget: float | None = Query(default=None),
) -> list[ForecastScenarioOut]:
    summary = forecast_summary(db, tenant, provider, horizon, budget)
    base = summary.month_end_projection
    budget_amount = summary.budget

    raw = [
        {
            "id": "sc_compute_20",
            "label": "Reduce compute spend by 20%",
            "description": "Apply all open compute rightsizing and idle candidates. Excludes production database changes.",
            "monthly_delta": -round(base * 0.14, 2),
            "actions": [
                "Rightsize 3 EC2 instances",
                "Reduce EKS node group by 3",
                "Schedule dev/staging VMs",
            ],
        },
        {
            "id": "sc_storage_tier",
            "label": "Enable intelligent storage tiering",
            "description": "Apply S3 Intelligent-Tiering and Azure blob lifecycle rules to cold data.",
            "monthly_delta": -round(base * 0.04, 2),
            "actions": ["S3 Intelligent-Tiering on logs bucket", "Blob lifecycle on cold container"],
        },
        {
            "id": "sc_no_action",
            "label": "Take no action",
            "description": "Hold current architecture. Assumes no new workloads and no traffic growth.",
            "monthly_delta": 0.0,
            "actions": [],
        },
        {
            "id": "sc_growth_30",
            "label": "Traffic grows 30%",
            "description": "Assume steady workload growth. Useful for budget planning.",
            "monthly_delta": round(base * 0.18, 2),
            "actions": ["Plan for capacity expansion", "Review commitment coverage"],
        },
    ]

    out: list[ForecastScenarioOut] = []
    for r in raw:
        new_projection = base + float(r["monthly_delta"])
        ratio = new_projection / budget_amount if budget_amount > 0 else 0
        status = "over" if ratio > 1 else "near" if ratio > 0.95 else "under"
        out.append(
            ForecastScenarioOut(
                id=str(r["id"]),
                label=str(r["label"]),
                description=str(r["description"]),
                monthly_delta=float(r["monthly_delta"]),
                new_projection=round(new_projection, 2),
                budget_status=status,
                actions=list(r["actions"]),
            )
        )
    return out