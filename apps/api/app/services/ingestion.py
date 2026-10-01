import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import get_adapter
from app.models.cloud_account import CloudAccount
from app.models.cost import CostRecord
from app.models.resource import Resource


class IngestionResult:
    def __init__(self) -> None:
        self.resources_fetched = 0
        self.resources_inserted = 0
        self.resources_updated = 0
        self.costs_fetched = 0
        self.costs_inserted = 0
        self.errors: list[str] = []

    def as_dict(self) -> dict[str, int | list[str]]:
        return {
            "resources_fetched": self.resources_fetched,
            "resources_inserted": self.resources_inserted,
            "resources_updated": self.resources_updated,
            "costs_fetched": self.costs_fetched,
            "costs_inserted": self.costs_inserted,
            "errors": self.errors,
        }


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sync_account(self, cloud_account_id: uuid.UUID, days: int = 30) -> IngestionResult:
        result = IngestionResult()
        account = self.db.get(CloudAccount, cloud_account_id)
        if account is None:
            result.errors.append("Cloud account not found")
            return result

        try:
            adapter = get_adapter(account.provider)
        except ValueError as exc:
            result.errors.append(str(exc))
            return result

        end = date.today()
        start = end - timedelta(days=days)

        resource_map = self._sync_resources(adapter, account, result)
        self._sync_costs(adapter, account, start, end, resource_map, result)

        account.last_sync_at = datetime.now(UTC)
        account.last_sync_status = "success" if not result.errors else "partial"
        account.last_sync_message = (
            f"{result.costs_inserted} cost records · {result.resources_inserted} resources inserted"
            if not result.errors
            else "; ".join(result.errors)
        )
        if not result.errors:
            account.status = "connected"
            account.connection_verified = True
            account.connection_error = None
            for scope in ("billing", "inventory", "metrics"):
                entry = dict(account.coverage.get(scope, {"enabled": True}))
                entry["enabled"] = True
                entry["last_sync_at"] = account.last_sync_at.isoformat()
                account.coverage = {**account.coverage, scope: entry}
        self.db.commit()
        return result

    def _sync_resources(self, adapter, account: CloudAccount, result: IngestionResult) -> dict[str, Resource]:
        items = adapter.get_resources(self.db, account.id)
        result.resources_fetched = len(items)
        resource_map: dict[str, Resource] = {}

        for item in items:
            stmt = select(Resource).where(
                Resource.cloud_account_id == account.id,
                Resource.cloud_id == item["cloud_id"],
            )
            existing = self.db.execute(stmt).scalar_one_or_none()
            if existing is None:
                resource = Resource(
                    tenant_id=account.tenant_id,
                    cloud_account_id=account.id,
                    provider=account.provider,
                    cloud_id=item["cloud_id"],
                    name=item["name"],
                    type=item["type"],
                    service=item["service"],
                    region=item["region"],
                    environment=item["environment"],
                    status=item["status"],
                    application=item.get("application", "unknown"),
                    owner=item.get("owner", "unassigned"),
                    tags=item.get("tags", []),
                    utilization=item.get("utilization", {}),
                    series=item.get("series", {}),
                    metric_coverage=Decimal(str(item.get("metric_coverage", 0))),
                    monthly_cost=Decimal(str(item.get("monthly_cost", 0))),
                )
                self.db.add(resource)
                self.db.flush()
                result.resources_inserted += 1
                resource_map[item["cloud_id"]] = resource
            else:
                existing.status = item["status"]
                existing.monthly_cost = Decimal(str(item.get("monthly_cost", 0)))
                existing.utilization = item.get("utilization", {})
                result.resources_updated += 1
                resource_map[item["cloud_id"]] = existing

        account.resource_count = len(items)
        return resource_map

    def _sync_costs(
        self,
        adapter,
        account: CloudAccount,
        start: date,
        end: date,
        resource_map: dict[str, Resource],
        result: IngestionResult,
    ) -> None:
        items = adapter.get_costs(self.db, account.id, start, end)
        result.costs_fetched = len(items)

        for item in items:
            resource = None
            if item.get("resource_id"):
                resource = resource_map.get(item["resource_id"])
                if resource is None:
                    try:
                        resource = self.db.get(Resource, uuid.UUID(item["resource_id"]))
                    except (ValueError, TypeError):
                        resource = None

            stmt = select(CostRecord).where(
                CostRecord.cloud_account_id == account.id,
                CostRecord.date == date.fromisoformat(item["date"]),
                CostRecord.service == item["service"],
                CostRecord.region == item["region"],
                CostRecord.resource_id == (resource.id if resource else None),
            )
            existing = self.db.execute(stmt).scalar_one_or_none()
            if existing is None:
                self.db.add(
                    CostRecord(
                        tenant_id=account.tenant_id,
                        cloud_account_id=account.id,
                        resource_id=resource.id if resource else None,
                        date=date.fromisoformat(item["date"]),
                        provider=account.provider,
                        service=item["service"],
                        region=item["region"],
                        cost=Decimal(str(item["cost"])),
                        currency=item.get("currency", "USD"),
                        usage_quantity=Decimal(str(item.get("usage_quantity", 0))),
                        usage_unit=item.get("usage_unit", ""),
                        tags={},
                    )
                )
                result.costs_inserted += 1

        total_spend = sum(float(item["cost"]) for item in items)
        account.monthly_spend = Decimal(str(round(total_spend, 2)))