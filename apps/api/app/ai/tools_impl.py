import uuid
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.ai.tools import ToolContext, ToolResult, register
from app.models.anomaly import Anomaly
from app.models.cloud_account import CloudAccount
from app.models.cost import CostRecord
from app.models.recommendation import Recommendation
from app.models.resource import Resource


def _resolve_range(range_key: str) -> tuple[date, date, date, date]:
    today = date.today()
    if range_key == "7d":
        start = today - timedelta(days=6)
    elif range_key == "90d":
        start = today - timedelta(days=89)
    elif range_key == "mtd":
        start = today.replace(day=1)
    elif range_key == "ytd":
        start = today.replace(month=1, day=1)
    else:
        start = today - timedelta(days=29)
    end = today
    days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return start, end, prev_start, prev_end


class CostSummaryArgs(BaseModel):
    range: str = "30d"
    provider: str | None = None


@register("get_cost_summary", "Current and previous period spend with top mover")
def tool_get_cost_summary(ctx: ToolContext, range: str = "30d", provider: str | None = None) -> ToolResult:
    start, end, prev_start, prev_end = _resolve_range(range)
    base = select(CostRecord).where(
        CostRecord.tenant_id == ctx.tenant_id,
        CostRecord.date >= start,
        CostRecord.date <= end,
    )
    if provider and provider != "all":
        base = base.where(CostRecord.provider == provider)
    rows = list(ctx.db.execute(base).scalars().all())
    current = sum(float(r.cost) for r in rows)

    prev = select(CostRecord).where(
        CostRecord.tenant_id == ctx.tenant_id,
        CostRecord.date >= prev_start,
        CostRecord.date <= prev_end,
    )
    if provider and provider != "all":
        prev = prev.where(CostRecord.provider == provider)
    prev_rows = list(ctx.db.execute(prev).scalars().all())
    previous = sum(float(r.cost) for r in prev_rows)

    change = current - previous
    change_pct = (change / previous * 100) if previous > 0 else 0
    return ToolResult(
        summary=f"Spend ${current:,.0f} · {change_pct:+.1f}% vs prior period",
        data={
            "current": round(current, 2),
            "previous": round(previous, 2),
            "change_amount": round(change, 2),
            "change_pct": round(change_pct, 2),
            "range": range,
            "provider": provider or "all",
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        },
    )


class BreakdownArgs(BaseModel):
    dimension: str = "service"
    range: str = "30d"
    provider: str | None = None


@register("get_cost_breakdown", "Spend grouped by service, account, or region")
def tool_get_cost_breakdown(ctx: ToolContext, dimension: str = "service", range: str = "30d", provider: str | None = None) -> ToolResult:
    start, end, prev_start, prev_end = _resolve_range(range)
    key_attr = {"service": "service", "account": "cloud_account_id", "region": "region"}.get(dimension, "service")

    base = select(CostRecord).where(
        CostRecord.tenant_id == ctx.tenant_id,
        CostRecord.date >= start,
        CostRecord.date <= end,
    )
    if provider and provider != "all":
        base = base.where(CostRecord.provider == provider)
    rows = list(ctx.db.execute(base).scalars().all())

    prev = select(CostRecord).where(
        CostRecord.tenant_id == ctx.tenant_id,
        CostRecord.date >= prev_start,
        CostRecord.date <= prev_end,
    )
    if provider and provider != "all":
        prev = prev.where(CostRecord.provider == provider)
    prev_rows = list(ctx.db.execute(prev).scalars().all())

    def group(items):
        out: dict[str, float] = {}
        for r in items:
            key = str(getattr(r, key_attr))
            out[key] = out.get(key, 0) + float(r.cost)
        return out

    current_grouped = group(rows)
    previous_grouped = group(prev_rows)
    total = sum(current_grouped.values())

    account_names: dict[str, str] = {}
    if key_attr == "cloud_account_id":
        for a in ctx.db.execute(select(CloudAccount).where(CloudAccount.tenant_id == ctx.tenant_id)).scalars().all():
            account_names[str(a.id)] = a.name

    rows_out = []
    for key, spend in current_grouped.items():
        prev_val = previous_grouped.get(key, 0)
        delta = spend - prev_val
        delta_pct = (delta / prev_val * 100) if prev_val > 0 else 0
        name = account_names.get(key, key)
        rows_out.append(
            {
                "id": key,
                "name": name,
                "spend": round(spend, 2),
                "change_pct": round(delta_pct, 2),
                "share": round(spend / total, 4) if total > 0 else 0,
            }
        )
    rows_out.sort(key=lambda r: r["spend"], reverse=True)
    top = rows_out[0] if rows_out else None
    summary = (
        f"Top {dimension}: {top['name']} ${top['spend']:,.0f} ({top['change_pct']:+.1f}%)"
        if top
        else "No data"
    )
    return ToolResult(summary=summary, data={"dimension": dimension, "rows": rows_out[:10]})


class TrendArgs(BaseModel):
    range: str = "7d"
    provider: str | None = None


@register("get_cost_trend", "Daily cost totals for a range")
def tool_get_cost_trend(ctx: ToolContext, range: str = "7d", provider: str | None = None) -> ToolResult:
    start, end, _, _ = _resolve_range(range)
    base = select(CostRecord).where(
        CostRecord.tenant_id == ctx.tenant_id,
        CostRecord.date >= start,
        CostRecord.date <= end,
    )
    if provider and provider != "all":
        base = base.where(CostRecord.provider == provider)
    rows = list(ctx.db.execute(base).scalars().all())

    daily: dict[date, float] = {}
    for r in rows:
        daily[r.date] = daily.get(r.date, 0) + float(r.cost)

    points = []
    current = start
    while current <= end:
        points.append({"date": current.isoformat(), "cost": round(daily.get(current, 0), 2)})
        current += timedelta(days=1)

    return ToolResult(
        summary=f"{len(points)} daily points · total ${sum(daily.values()):,.0f}",
        data={"range": range, "points": points},
    )


class AnomalyArgs(BaseModel):
    provider: str | None = None


@register("get_anomalies", "Recent cost anomalies")
def tool_get_anomalies(ctx: ToolContext, provider: str | None = None) -> ToolResult:
    stmt = select(Anomaly).where(Anomaly.tenant_id == ctx.tenant_id)
    if provider and provider != "all":
        stmt = stmt.where(Anomaly.provider == provider)
    rows = list(ctx.db.execute(stmt).scalars().all())
    rows.sort(key=lambda a: a.detected_at, reverse=True)

    account_names: dict[str, str] = {}
    for a in ctx.db.execute(select(CloudAccount).where(CloudAccount.tenant_id == ctx.tenant_id)).scalars().all():
        account_names[str(a.id)] = a.name

    out = [
        {
            "id": str(a.id),
            "service": a.service,
            "account": account_names.get(str(a.cloud_account_id), ""),
            "provider": a.provider,
            "detected_at": a.detected_at.isoformat(),
            "delta_pct": float(a.delta_pct),
            "delta_amount": float(a.delta_amount),
            "description": a.description,
            "severity": a.severity,
        }
        for a in rows
    ]
    return ToolResult(
        summary=f"{len(out)} anomalies · top {out[0]['service'] if out else 'n/a'}",
        data={"anomalies": out},
    )


class ResourceArgs(BaseModel):
    name: str = Field(min_length=1)


@register("get_resource", "Fetch a single resource by name or cloud ID")
def tool_get_resource(ctx: ToolContext, name: str) -> ToolResult:
    stmt = select(Resource).where(
        Resource.tenant_id == ctx.tenant_id,
        or_(func.lower(Resource.name) == name.lower(), Resource.cloud_id == name),
    ).limit(1)
    resource = ctx.db.execute(stmt).scalar_one_or_none()
    if resource is None:
        return ToolResult(summary=f"Resource {name} not found")
    return ToolResult(
        summary=f"{resource.name} · {resource.type} · ${float(resource.monthly_cost):,.0f}/mo",
        data={
            "id": str(resource.id),
            "name": resource.name,
            "type": resource.type,
            "service": resource.service,
            "region": resource.region,
            "environment": resource.environment,
            "status": resource.status,
            "monthly_cost": float(resource.monthly_cost),
            "utilization": resource.utilization,
            "metric_coverage": float(resource.metric_coverage),
        },
    )


class IdleArgs(BaseModel):
    cpu_threshold: float = 15.0
    limit: int = 10


@register("find_idle_resources", "Resources with sustained low CPU utilization")
def tool_find_idle_resources(ctx: ToolContext, cpu_threshold: float = 15.0, limit: int = 10) -> ToolResult:
    stmt = select(Resource).where(Resource.tenant_id == ctx.tenant_id)
    rows = list(ctx.db.execute(stmt).scalars().all())
    candidates = []
    for r in rows:
        cpu = (r.utilization or {}).get("cpu")
        if cpu is None:
            continue
        if float(cpu) < cpu_threshold and float(r.metric_coverage) >= 0.7:
            candidates.append(
                {
                    "id": str(r.id),
                    "name": r.name,
                    "type": r.type,
                    "service": r.service,
                    "region": r.region,
                    "environment": r.environment,
                    "status": r.status,
                    "cpu": float(cpu),
                    "monthly_cost": float(r.monthly_cost),
                }
            )
    candidates.sort(key=lambda c: c["monthly_cost"], reverse=True)
    candidates = candidates[:limit]
    total = sum(c["monthly_cost"] for c in candidates)
    return ToolResult(
        summary=f"{len(candidates)} idle candidates · ${total:,.0f}/mo identified",
        data={"candidates": candidates, "total_monthly_cost": round(total, 2)},
    )


class ListRecommendationsArgs(BaseModel):
    status: str = "pending"
    limit: int = 10


@register("list_recommendations", "Open recommendations sorted by savings")
def tool_list_recommendations(ctx: ToolContext, status: str = "pending", limit: int = 10) -> ToolResult:
    stmt = select(Recommendation).where(Recommendation.tenant_id == ctx.tenant_id)
    if status and status != "all":
        stmt = stmt.where(Recommendation.status == status)
    rows = list(ctx.db.execute(stmt).scalars().all())
    rows.sort(key=lambda r: float(r.estimated_monthly_savings), reverse=True)
    rows = rows[:limit]

    resource_ids = {r.resource_id for r in rows}
    resources: dict[uuid.UUID, Resource] = {}
    if resource_ids:
        for r in ctx.db.execute(select(Resource).where(Resource.id.in_(resource_ids))).scalars().all():
            resources[r.id] = r

    out = []
    for r in rows:
        resource = resources.get(r.resource_id)
        out.append(
            {
                "id": str(r.id),
                "title": r.title,
                "type": r.type,
                "risk": r.risk,
                "status": r.status,
                "estimated_monthly_savings": float(r.estimated_monthly_savings),
                "resource_name": resource.name if resource else "",
            }
        )
    total = sum(r["estimated_monthly_savings"] for r in out)
    return ToolResult(
        summary=f"{len(out)} recommendations · ${total:,.0f}/mo identified",
        data={"recommendations": out, "total_savings": round(total, 2)},
    )


class CalculateSavingsArgs(BaseModel):
    recommendation_ids: list[str] = Field(default_factory=list)


@register("calculate_savings", "Total monthly savings for the given recommendation IDs")
def tool_calculate_savings(ctx: ToolContext, recommendation_ids: list[str]) -> ToolResult:
    if not recommendation_ids:
        return ToolResult(summary="No recommendations provided")
    try:
        ids = [uuid.UUID(rid) for rid in recommendation_ids]
    except ValueError:
        return ToolResult(summary="Invalid recommendation IDs")
    stmt = select(Recommendation).where(
        Recommendation.tenant_id == ctx.tenant_id,
        Recommendation.id.in_(ids),
    )
    rows = list(ctx.db.execute(stmt).scalars().all())
    total = sum(float(r.estimated_monthly_savings) for r in rows)
    return ToolResult(
        summary=f"${total:,.0f}/mo across {len(rows)} recommendations",
        data={"total_monthly_savings": round(total, 2), "count": len(rows)},
    )


class ForecastArgs(BaseModel):
    horizon: str = "30d"


@register("forecast_spend", "Projected spend for the next horizon")
def tool_forecast_spend(ctx: ToolContext, horizon: str = "30d") -> ToolResult:
    from app.api.v1.forecasts import _build_series, _load_daily_totals, _horizon_days

    class _TenantShim:
        def __init__(self, tenant_id):
            self.id = tenant_id

    shim = _TenantShim(ctx.tenant_id)
    daily = _load_daily_totals(ctx.db, shim, None)
    points = _build_series(daily, _horizon_days(horizon))
    forecast_points = [p for p in points if p.forecast is not None]
    total = sum(p.forecast or 0 for p in forecast_points)
    return ToolResult(
        summary=f"Projected {horizon} spend ${total:,.0f}",
        data={
            "horizon": horizon,
            "projected_total": round(total, 2),
            "points": [{"date": p.date.isoformat(), "forecast": p.forecast} for p in forecast_points],
        },
    )