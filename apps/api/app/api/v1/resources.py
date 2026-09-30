import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.session import get_db
from app.models.cloud_account import CloudAccount
from app.models.resource import Resource
from app.models.tenant import Tenant
from app.schemas.resource import (
    EnvironmentAggregate,
    ResourceAggregates,
    ResourceListOut,
    ResourceOut,
)

router = APIRouter(prefix="/resources", tags=["resources"])

SortKey = Literal["name", "service", "region", "environment", "monthlyCost", "utilization"]
SortDir = Literal["asc", "desc"]


def _resource_to_out(resource: Resource, account: CloudAccount | None) -> ResourceOut:
    out = ResourceOut.model_validate(resource)
    if account is not None:
        out.account_name = account.name
    return out


@router.get("", response_model=ResourceListOut)
def list_resources(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    q: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    service: str | None = Query(default=None),
    region: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    status: str | None = Query(default=None),
    sort_key: SortKey = Query(default="monthlyCost"),
    sort_dir: SortDir = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> ResourceListOut:
    base = select(Resource).where(Resource.tenant_id == tenant.id)

    if q:
        term = f"%{q.strip().lower()}%"
        base = base.where(
            or_(
                func.lower(Resource.name).like(term),
                func.lower(Resource.cloud_id).like(term),
                func.lower(Resource.type).like(term),
                func.lower(Resource.application).like(term),
            )
        )
    if provider and provider != "all":
        base = base.where(Resource.provider == provider)
    if service and service != "all":
        base = base.where(Resource.service == service)
    if region and region != "all":
        base = base.where(Resource.region == region)
    if environment and environment != "all":
        base = base.where(Resource.environment == environment)
    if status and status != "all":
        base = base.where(Resource.status == status)

    all_rows = list(db.execute(base).scalars().all())
    total = len(all_rows)

    sort_attr = {
        "name": Resource.name,
        "service": Resource.service,
        "region": Resource.region,
        "environment": Resource.environment,
        "monthlyCost": Resource.monthly_cost,
        "utilization": Resource.metric_coverage,
    }[sort_key]
    reverse = sort_dir == "desc"
    all_rows.sort(key=lambda r: getattr(r, sort_attr.key) if hasattr(sort_attr, "key") else getattr(r, sort_key, ""), reverse=reverse)

    start = (page - 1) * page_size
    page_rows = all_rows[start : start + page_size]

    account_ids = {r.cloud_account_id for r in page_rows}
    accounts: dict[uuid.UUID, CloudAccount] = {}
    if account_ids:
        stmt = select(CloudAccount).where(CloudAccount.id.in_(account_ids))
        for a in db.execute(stmt).scalars().all():
            accounts[a.id] = a

    items = [_resource_to_out(r, accounts.get(r.cloud_account_id)) for r in page_rows]

    total_monthly_cost = sum(float(r.monthly_cost) for r in all_rows)
    by_environment: dict[str, EnvironmentAggregate] = {}
    by_provider: dict[str, EnvironmentAggregate] = {}
    for r in all_rows:
        cost = float(r.monthly_cost)
        env = by_environment.get(r.environment)
        if env is None:
            by_environment[r.environment] = EnvironmentAggregate(count=1, cost=cost)
        else:
            env.count += 1
            env.cost += cost
        prov = by_provider.get(r.provider)
        if prov is None:
            by_provider[r.provider] = EnvironmentAggregate(count=1, cost=cost)
        else:
            prov.count += 1
            prov.cost += cost

    return ResourceListOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        aggregates=ResourceAggregates(
            total_monthly_cost=round(total_monthly_cost, 2),
            by_environment=by_environment,
            by_provider=by_provider,
        ),
    )


@router.get("/{resource_id}", response_model=ResourceOut)
def get_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> ResourceOut:
    resource = db.get(Resource, resource_id)
    if resource is None or resource.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Resource not found")
    account = db.get(CloudAccount, resource.cloud_account_id)
    return _resource_to_out(resource, account)