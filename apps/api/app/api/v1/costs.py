import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.models.anomaly import Anomaly
from app.models.cloud_account import CloudAccount
from app.models.cost import CostRecord
from app.models.resource import Resource
from app.models.tenant import Tenant
from app.db.session import get_db
from app.schemas.cost import (
    CostAnomalyOut,
    CostBreakdownRow,
    CostSummaryOut,
    CostTrendPoint,
    ResolvedRange,
    ResourceCostPoint,
    TopMover,
)

router = APIRouter(prefix="/costs", tags=["costs"])

RangeKey = str


def _resolve_range(range_key: RangeKey) -> tuple[date, date, date, date]:
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


def _apply_filters(stmt, provider: str | None, account_id: str | None, service: str | None):
    if provider and provider != "all":
        stmt = stmt.where(CostRecord.provider == provider)
    if service and service != "all":
        stmt = stmt.where(CostRecord.service == service)
    if account_id and account_id != "all":
        try:
            import uuid as _uuid

            account_uuid = _uuid.UUID(account_id)
            stmt = stmt.where(CostRecord.cloud_account_id == account_uuid)
        except ValueError:
            pass
    return stmt


@router.get("/summary", response_model=CostSummaryOut)
def cost_summary(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    range: str = Query(default="30d"),
    provider: str | None = Query(default=None),
    account_id: str | None = Query(default=None),
    service: str | None = Query(default=None),
) -> CostSummaryOut:
    start, end, prev_start, prev_end = _resolve_range(range)

    current_stmt = _apply_filters(
        select(CostRecord).where(
            CostRecord.tenant_id == tenant.id,
            CostRecord.date >= start,
            CostRecord.date <= end,
        ),
        provider,
        account_id,
        service,
    )
    previous_stmt = _apply_filters(
        select(CostRecord).where(
            CostRecord.tenant_id == tenant.id,
            CostRecord.date >= prev_start,
            CostRecord.date <= prev_end,
        ),
        provider,
        account_id,
        service,
    )

    current_rows = list(db.execute(current_stmt).scalars().all())
    previous_rows = list(db.execute(previous_stmt).scalars().all())

    current_spend = sum(float(r.cost) for r in current_rows)
    previous_spend = sum(float(r.cost) for r in previous_rows)
    change_amount = current_spend - previous_spend
    change_pct = (change_amount / previous_spend * 100) if previous_spend > 0 else 0

    current_by_service: dict[str, float] = {}
    for r in current_rows:
        current_by_service[r.service] = current_by_service.get(r.service, 0) + float(r.cost)

    previous_by_service: dict[str, float] = {}
    for r in previous_rows:
        previous_by_service[r.service] = previous_by_service.get(r.service, 0) + float(r.cost)

    top_mover = None
    if current_by_service:
        candidates = []
        for name, curr in current_by_service.items():
            prev = previous_by_service.get(name, 0)
            delta = curr - prev
            delta_pct = (delta / prev * 100) if prev > 0 else 0
            candidates.append(TopMover(name=name, delta_amount=round(delta, 2), delta_pct=round(delta_pct, 2)))
        candidates.sort(key=lambda m: m.delta_amount, reverse=True)
        top_mover = candidates[0]

    return CostSummaryOut(
        current_spend=round(current_spend, 2),
        previous_spend=round(previous_spend, 2),
        change_amount=round(change_amount, 2),
        change_pct=round(change_pct, 2),
        top_mover=top_mover,
        currency="USD",
        period=ResolvedRange(start=start, end=end),
    )


@router.get("/trends", response_model=list[CostTrendPoint])
def cost_trends(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    range: str = Query(default="30d"),
    provider: str | None = Query(default=None),
    account_id: str | None = Query(default=None),
    service: str | None = Query(default=None),
) -> list[CostTrendPoint]:
    start, end, _, _ = _resolve_range(range)

    stmt = _apply_filters(
        select(CostRecord).where(
            CostRecord.tenant_id == tenant.id,
            CostRecord.date >= start,
            CostRecord.date <= end,
        ),
        provider,
        account_id,
        service,
    )
    rows = list(db.execute(stmt).scalars().all())

    by_date: dict[date, dict[str, float]] = {}
    for r in rows:
        bucket = by_date.setdefault(r.date, {"aws": 0.0, "azure": 0.0})
        key = "aws" if r.provider == "AWS" else "azure"
        bucket[key] += float(r.cost)

    out: list[CostTrendPoint] = []
    current = start
    while current <= end:
        bucket = by_date.get(current, {"aws": 0.0, "azure": 0.0})
        out.append(
            CostTrendPoint(
                date=current,
                aws=round(bucket["aws"], 2),
                azure=round(bucket["azure"], 2),
                total=round(bucket["aws"] + bucket["azure"], 2),
            )
        )
        current += timedelta(days=1)
    return out


@router.get("/breakdown", response_model=list[CostBreakdownRow])
def cost_breakdown(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    range: str = Query(default="30d"),
    dimension: str = Query(default="service"),
    provider: str | None = Query(default=None),
    account_id: str | None = Query(default=None),
    service: str | None = Query(default=None),
) -> list[CostBreakdownRow]:
    start, end, prev_start, prev_end = _resolve_range(range)

    current_stmt = _apply_filters(
        select(CostRecord).where(
            CostRecord.tenant_id == tenant.id,
            CostRecord.date >= start,
            CostRecord.date <= end,
        ),
        provider,
        account_id,
        service,
    )
    previous_stmt = _apply_filters(
        select(CostRecord).where(
            CostRecord.tenant_id == tenant.id,
            CostRecord.date >= prev_start,
            CostRecord.date <= prev_end,
        ),
        provider,
        account_id,
        service,
    )

    current_rows = list(db.execute(current_stmt).scalars().all())
    previous_rows = list(db.execute(previous_stmt).scalars().all())

    key_attr = {
        "service": "service",
        "account": "cloud_account_id",
        "region": "region",
    }.get(dimension, "service")

    account_names: dict[str, str] = {}
    if key_attr == "cloud_account_id":
        account_stmt = select(CloudAccount).where(CloudAccount.tenant_id == tenant.id)
        for a in db.execute(account_stmt).scalars().all():
            account_names[str(a.id)] = a.name

    def group(rows):
        out: dict[str, dict[str, float | str]] = {}
        for r in rows:
            key_val = getattr(r, key_attr)
            key = str(key_val)
            entry = out.setdefault(key, {"spend": 0.0, "provider": r.provider})
            entry["spend"] = float(entry["spend"]) + float(r.cost)
            if entry["provider"] != r.provider:
                entry["provider"] = "mixed"
        return out

    current_grouped = group(current_rows)
    previous_grouped = group(previous_rows)
    total_spend = sum(float(v["spend"]) for v in current_grouped.values())

    rows_out: list[CostBreakdownRow] = []
    for key, data in current_grouped.items():
        spend = float(data["spend"])
        prev = float(previous_grouped.get(key, {}).get("spend", 0))
        change_pct = ((spend - prev) / prev * 100) if prev > 0 else 0
        share = (spend / total_spend) if total_spend > 0 else 0
        name = account_names.get(key, key) if key_attr == "cloud_account_id" else key
        rows_out.append(
            CostBreakdownRow(
                id=key,
                name=name,
                provider=str(data["provider"]),
                spend=round(spend, 2),
                change_pct=round(change_pct, 2),
                share=round(share, 4),
            )
        )

    rows_out.sort(key=lambda r: r.spend, reverse=True)
    return rows_out


@router.get("/by-resource/{resource_id}", response_model=list[ResourceCostPoint])
def cost_by_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    days: int = Query(default=30, ge=7, le=180),
) -> list[ResourceCostPoint]:
    resource = db.get(Resource, resource_id)
    if resource is None or resource.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Resource not found")

    today = date.today()
    start = today - timedelta(days=days - 1)

    stmt = select(CostRecord).where(
        CostRecord.tenant_id == tenant.id,
        CostRecord.resource_id == resource_id,
        CostRecord.date >= start,
        CostRecord.date <= today,
    )
    rows = list(db.execute(stmt).scalars().all())

    by_date: dict[date, float] = {}
    for r in rows:
        by_date[r.date] = by_date.get(r.date, 0.0) + float(r.cost)

    out: list[ResourceCostPoint] = []
    current = start
    while current <= today:
        out.append(ResourceCostPoint(date=current, cost=round(by_date.get(current, 0.0), 4)))
        current += timedelta(days=1)
    return out


@router.get("/anomalies", response_model=list[CostAnomalyOut])
def cost_anomalies(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    provider: str | None = Query(default=None),
    account_id: str | None = Query(default=None),
    service: str | None = Query(default=None),
) -> list[CostAnomalyOut]:
    stmt = select(Anomaly).where(Anomaly.tenant_id == tenant.id)
    if provider and provider != "all":
        stmt = stmt.where(Anomaly.provider == provider)
    if service and service != "all":
        stmt = stmt.where(Anomaly.service == service)

    rows = list(db.execute(stmt).scalars().all())
    rows.sort(key=lambda a: a.detected_at, reverse=True)

    account_names: dict[str, str] = {}
    account_stmt = select(CloudAccount).where(CloudAccount.tenant_id == tenant.id)
    for a in db.execute(account_stmt).scalars().all():
        account_names[str(a.id)] = a.name

    out: list[CostAnomalyOut] = []
    for a in rows:
        out.append(
            CostAnomalyOut(
                id=a.id,
                service=a.service,
                account=account_names.get(str(a.cloud_account_id), ""),
                provider=a.provider,
                detected_at=a.detected_at,
                delta_pct=float(a.delta_pct),
                delta_amount=float(a.delta_amount),
                description=a.description,
                severity=a.severity,
            )
        )
    return out