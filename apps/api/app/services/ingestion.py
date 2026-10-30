import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import get_adapter
from app.config import get_settings
from app.models.cloud_account import CloudAccount
from app.models.cost import CostRecord
from app.models.resource import Resource

logger = logging.getLogger("app.services.ingestion")


class IngestionResult:
    def __init__(self) -> None:
        self.resources_fetched = 0
        self.resources_inserted = 0
        self.resources_updated = 0
        self.metrics_fetched = 0
        self.metrics_applied = 0
        self.costs_fetched = 0
        self.costs_inserted = 0
        self.errors: list[str] = []

    def as_dict(self) -> dict:
        return {
            "resources_fetched": self.resources_fetched,
            "resources_inserted": self.resources_inserted,
            "resources_updated": self.resources_updated,
            "metrics_fetched": self.metrics_fetched,
            "metrics_applied": self.metrics_applied,
            "costs_fetched": self.costs_fetched,
            "costs_inserted": self.costs_inserted,
            "errors": self.errors,
        }


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _set_phase(self, account: CloudAccount, phase: str, pct: int) -> None:
        account.sync_phase = phase
        account.sync_progress_pct = max(0, min(100, pct))
        self.db.commit()

    def sync_account(self, cloud_account_id: uuid.UUID, days: int | None = None) -> IngestionResult:
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

        settings = get_settings()
        lookback = days or settings.aws_cost_lookback_days

        account.sync_started_at = datetime.now(UTC)
        account.sync_completed_at = None
        account.sync_error_count = 0
        account.status = "syncing"
        self._set_phase(account, "discovering", 5)

        end = date.today()
        start = end - timedelta(days=lookback - 1)

        try:
            resource_map = self._sync_resources(adapter, account, result)
            self._set_phase(account, "discovering", 40)

            self._sync_costs(adapter, account, start, end, result)
            self._set_phase(account, "costs", 65)

            self._sync_metrics(adapter, account, resource_map, result, days=settings.aws_metrics_days)
            self._set_phase(account, "metrics", 95)

            account.last_sync_at = datetime.now(UTC)
            account.last_sync_status = "success" if not result.errors else "partial"
            account.last_sync_message = (
                f"{result.resources_inserted}+{result.resources_updated} resources · "
                f"{result.costs_inserted} cost rows · {result.metrics_applied} metrics"
                if not result.errors
                else "; ".join(result.errors[:3])
            )
            if not result.errors:
                account.status = "connected"
                account.connection_verified = True
                account.connection_error = None
                coverage = dict(account.coverage or {})
                now_iso = account.last_sync_at.isoformat()
                for scope in ("billing", "inventory", "metrics"):
                    entry = dict(coverage.get(scope, {"enabled": True}))
                    entry["enabled"] = True
                    entry["last_sync_at"] = now_iso
                    coverage[scope] = entry
                account.coverage = coverage

            account.sync_completed_at = datetime.now(UTC)
            account.sync_progress_pct = 100
            self._set_phase(account, "complete", 100)
        except Exception as exc:
            logger.exception("Sync failed for account %s", account.id)
            result.errors.append(str(exc))
            account.last_sync_status = "failed"
            account.last_sync_message = str(exc)[:500]
            account.status = "error"
            account.sync_error_count = (account.sync_error_count or 0) + 1
            account.sync_completed_at = datetime.now(UTC)
            account.sync_phase = "failed"
            self._set_phase(account, "failed", 0)

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
                existing.name = item["name"]
                existing.type = item["type"]
                existing.status = item["status"]
                existing.environment = item["environment"]
                existing.tags = item.get("tags", [])
                existing.application = item.get("application", "unknown")
                existing.owner = item.get("owner", "unassigned")
                result.resources_updated += 1
                resource_map[item["cloud_id"]] = existing

        account.resource_count = len(items)
        self.db.flush()
        return resource_map

    def _sync_costs(
        self,
        adapter,
        account: CloudAccount,
        start: date,
        end: date,
        result: IngestionResult,
    ) -> None:
        items = adapter.get_costs(self.db, account.id, start, end)
        result.costs_fetched = len(items)

        total = Decimal("0")
        for item in items:
            record_date = date.fromisoformat(item["date"])
            stmt = select(CostRecord).where(
                CostRecord.cloud_account_id == account.id,
                CostRecord.date == record_date,
                CostRecord.service == item["service"],
                CostRecord.region == item["region"],
                CostRecord.resource_id.is_(None),
            )
            existing = self.db.execute(stmt).scalar_one_or_none()
            cost_value = Decimal(str(item["cost"]))
            if existing is None:
                self.db.add(
                    CostRecord(
                        tenant_id=account.tenant_id,
                        cloud_account_id=account.id,
                        resource_id=None,
                        date=record_date,
                        provider=account.provider,
                        service=item["service"],
                        region=item["region"],
                        cost=cost_value,
                        currency=item.get("currency", "USD"),
                        usage_quantity=Decimal(str(item.get("usage_quantity", 0))),
                        usage_unit=item.get("usage_unit", ""),
                        tags={},
                    )
                )
                result.costs_inserted += 1
            else:
                existing.cost = cost_value
            total += cost_value

        account.monthly_spend = Decimal(str(round(float(total), 2)))
        self.db.flush()

    def _sync_metrics(
        self,
        adapter,
        account: CloudAccount,
        resource_map: dict[str, Resource],
        result: IngestionResult,
        days: int = 30,
    ) -> None:
        if not resource_map:
            return

        resource_ids = [r.id for r in resource_map.values()]
        if not resource_ids:
            return

        end = date.today()
        start = end - timedelta(days=days - 1)

        try:
            metrics = adapter.get_metrics(self.db, resource_ids, start, end)
        except Exception as exc:
            logger.warning("Metrics fetch failed for account %s: %s", account.id, exc)
            return

        result.metrics_fetched = len(metrics)
        threshold = get_settings().aws_metric_coverage_threshold

        by_id = {r.id: r for r in resource_map.values()}
        for entry in metrics:
            try:
                resource_id = uuid.UUID(entry["resource_id"])
            except (KeyError, ValueError):
                continue
            resource = by_id.get(resource_id)
            if resource is None:
                continue

            utilization = dict(resource.utilization or {})
            series = dict(resource.series or {})

            if entry.get("cpu") is not None:
                utilization["cpu"] = entry["cpu"]
            if entry.get("memory") is not None:
                utilization["memory"] = entry["memory"]
            for key, values in (entry.get("series") or {}).items():
                if values:
                    series[key] = values

            resource.utilization = utilization
            resource.series = series
            coverage_value = float(entry.get("coverage", 0.0))
            resource.metric_coverage = Decimal(str(round(coverage_value, 3)))
            if coverage_value >= threshold:
                result.metrics_applied += 1

        self.db.flush()