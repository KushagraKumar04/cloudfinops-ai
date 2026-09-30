from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.models.budget import Budget
from app.models.cost import CostRecord
from app.models.tenant import Tenant
from app.schemas.forecast import (
    ForecastPoint,
    ForecastScenarioOut,
    ForecastSummaryOut,
    ServiceForecastOut,
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


def _load_daily_totals(db: Session, tenant: Tenant, provider: str | None) -> dict[date, float]:
    stmt = select(CostRecord).where(CostRecord.tenant_id == tenant.id)
    if provider and provider != "all":
        stmt = stmt.where(CostRecord.provider == provider)
    rows = list(db.execute(stmt).scalars().all())
    daily: dict[date, float] = {}
    for r in rows:
        daily[r.date] = daily.get(r.date, 0) + float(r.cost)
    return daily


def _build_series(daily: dict[date, float], horizon_days: int) -> list[ForecastPoint]:
    today = date.today()
    dates = sorted(daily.keys())
    if not dates:
        return []

    hist_start = dates[0]
    hist_end = dates[-1]
    hist_days = (hist_end - hist_start).days + 1

    total_recent = sum(daily.get(hist_start + timedelta(days=i), 0) for i in range(hist_days))
    trend = 0.0035

    window = min(hist_days, 14)
    recent_values = [daily.get(hist_end - timedelta(days=i), 0) for i in range(window)]
    recent_values = [v for v in recent_values if v > 0]
    baseline = (sum(recent_values) / len(recent_values)) if recent_values else (total_recent / max(1, hist_days))

    forecast_values: list[float] = []
    for i in range(horizon_days):
        trend_factor = (1 + trend) ** (i + 1)
        dow = i % 7
        weekend = 0.82 if dow >= 5 else 1.0
        forecast_values.append(baseline * trend_factor * weekend)

    points: list[ForecastPoint] = []
    for i in range(hist_days):
        d = hist_start + timedelta(days=i)
        actual = daily.get(d, 0)
        points.append(ForecastPoint(date=d, actual=round(actual, 2), forecast=None, lower=None, upper=None))

    for i, v in enumerate(forecast_values):
        d = hist_end + timedelta(days=i + 1)
        widening = 0.03 + (i / horizon_days) * 0.06
        points.append(
            ForecastPoint(
                date=d,
                actual=None,
                forecast=round(v, 2),
                lower=round(v * (1 - widening), 2),
                upper=round(v * (1 + widening), 2),
            )
        )
    return points


@router.get("/summary", response_model=ForecastSummaryOut)
def forecast_summary(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
    horizon: str = Query(default="30d"),
    budget: float | None = Query(default=None),
) -> ForecastSummaryOut:
    daily = _load_daily_totals(db, tenant, provider)
    horizon_days = _horizon_days(horizon)
    points = _build_series(daily, horizon_days)
    budget_amount = budget if budget is not None else _resolve_budget(db, tenant)

    today = date.today()
    actual_mtd = sum(v for d, v in daily.items() if d.month == today.month and d.year == today.year)

    end_of_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    days_remaining = max(1, (end_of_month - today).days)

    horizon_forecast = [p for p in points if p.forecast is not None][:days_remaining]
    forecast_remaining = sum(p.forecast or 0 for p in horizon_forecast)
    lower_remaining = sum(p.lower or 0 for p in horizon_forecast)
    upper_remaining = sum(p.upper or 0 for p in horizon_forecast)

    month_end_projection = actual_mtd + forecast_remaining
    month_end_lower = actual_mtd + lower_remaining
    month_end_upper = actual_mtd + upper_remaining

    forecast_points = [p for p in points if p.forecast is not None]
    if forecast_points:
        first = forecast_points[0].forecast or 0
        last = forecast_points[-1].forecast or 0
        trend_pct = ((last - first) / first * 100) if first > 0 else 0
    else:
        trend_pct = 0

    trend_direction = "up" if trend_pct > 1 else "down" if trend_pct < -1 else "flat"
    budget_utilization = (month_end_projection / budget_amount * 100) if budget_amount > 0 else 0

    if month_end_upper <= budget_amount:
        breach_probability = 0.02
    elif month_end_lower >= budget_amount:
        breach_probability = 0.95
    else:
        span = max(1.0, month_end_upper - month_end_lower)
        breach_probability = 0.4 + (month_end_upper - budget_amount) / span * 0.5

    return ForecastSummaryOut(
        month_end_projection=round(month_end_projection, 2),
        month_end_lower=round(month_end_lower, 2),
        month_end_upper=round(month_end_upper, 2),
        budget=round(budget_amount, 2),
        budget_utilization=round(budget_utilization, 2),
        breach_probability=round(breach_probability, 3),
        trend_direction=trend_direction,
        trend_pct=round(trend_pct, 2),
        confidence=0.82,
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
    daily = _load_daily_totals(db, tenant, provider)
    return _build_series(daily, _horizon_days(horizon))


@router.get("/by-service", response_model=list[ServiceForecastOut])
def forecast_by_service(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
    horizon: str = Query(default="30d"),
) -> list[ServiceForecastOut]:
    horizon_days = _horizon_days(horizon)
    stmt = select(CostRecord).where(CostRecord.tenant_id == tenant.id)
    if provider and provider != "all":
        stmt = stmt.where(CostRecord.provider == provider)
    rows = list(db.execute(stmt).scalars().all())

    today = date.today()
    window_start = today - timedelta(days=30)
    by_service: dict[str, dict[str, object]] = {}
    for r in rows:
        if r.date < window_start:
            continue
        entry = by_service.setdefault(r.service, {"provider": r.provider, "current": 0.0})
        entry["current"] = float(entry["current"]) + float(r.cost)

    out: list[ServiceForecastOut] = []
    total_projected = 0.0
    for name, entry in by_service.items():
        current = float(entry["current"])
        projected = current * (1 + 0.0035 * horizon_days)
        out.append(
            ServiceForecastOut(
                name=name,
                provider=str(entry["provider"]),
                current=round(current, 2),
                projected=round(projected, 2),
                change_pct=round(((projected - current) / current * 100) if current > 0 else 0, 2),
                share=0,
            )
        )
        total_projected += projected

    for s in out:
        s.share = round(s.projected / total_projected, 4) if total_projected > 0 else 0

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
                actions=list(r["actions"]),  # type: ignore[arg-type]
            )
        )
    return out