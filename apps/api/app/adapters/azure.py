import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from azure.core.exceptions import AzureError, ClientAuthenticationError
from azure.identity import ClientSecretCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import (
    QueryAggregation,
    QueryDataset,
    QueryDefinition,
    QueryGrouping,
    QueryTimePeriod,
)
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.cloud_account import CloudAccount
from app.models.cost import CostRecord
from app.models.resource import Resource
from app.services.encryption import decrypt_secret


class AzureAdapter:
    provider = "Azure"

    def _credential(self, account: CloudAccount) -> ClientSecretCredential:
        if not (account.tenant_external_id and account.client_id and account.encrypted_client_secret):
            raise ValueError("Azure account is missing tenant_id, client_id, or client_secret")
        secret = decrypt_secret(account.encrypted_client_secret)
        return ClientSecretCredential(
            tenant_id=account.tenant_external_id,
            client_id=account.client_id,
            client_secret=secret,
        )

    def validate_connection(self, db: Session, cloud_account_id: uuid.UUID) -> tuple[bool, str]:
        account = db.get(CloudAccount, cloud_account_id)
        if account is None or account.provider != self.provider:
            return False, "Cloud account not found"
        if not account.subscription_id:
            return False, "Missing subscription ID"
        if get_settings().mock_adapters:
            return True, f"Mock mode: subscription {account.subscription_id} accepted"
        try:
            credential = self._credential(account)
            client = CostManagementClient(credential)
            client.query.usage(
                scope=f"/subscriptions/{account.subscription_id}",
                parameters=QueryDefinition(
                    type="ActualCost",
                    timeframe="MonthToDate",
                    dataset=QueryDataset(
                        granularity="None",
                        aggregation={"totalCost": QueryAggregation(name="Cost", function="Sum")},
                    ),
                ),
            )
            return True, "Cost Management API reachable"
        except (ClientAuthenticationError, AzureError, ValueError) as exc:
            return False, f"Authentication failed: {exc}"

    def get_resources(self, db: Session, cloud_account_id: uuid.UUID) -> list[dict[str, Any]]:
        account = db.get(CloudAccount, cloud_account_id)
        if account is None or not account.subscription_id:
            return []

        if get_settings().mock_adapters:
            stmt = select(Resource).where(
                Resource.cloud_account_id == cloud_account_id,
                Resource.provider == self.provider,
            )
            rows = list(db.execute(stmt).scalars().all())
            return [
                {
                    "cloud_id": r.cloud_id,
                    "name": r.name,
                    "type": r.type,
                    "service": r.service,
                    "region": r.region,
                    "environment": r.environment,
                    "status": r.status,
                    "application": r.application,
                    "owner": r.owner,
                    "tags": r.tags,
                    "utilization": r.utilization,
                    "series": r.series,
                    "metric_coverage": float(r.metric_coverage),
                    "monthly_cost": float(r.monthly_cost),
                }
                for r in rows
            ]

        try:
            credential = self._credential(account)
            rg = ResourceGraphClient(credential)
            query = QueryRequest(
                query=(
                    "Resources "
                    "| project id, name, type, location, resourceGroup, tags, properties"
                ),
                subscriptions=[account.subscription_id],
            )
            response = rg.resources(query)
        except (ClientAuthenticationError, AzureError, ValueError):
            return []

        out: list[dict[str, Any]] = []
        for row in response.data or []:
            tags = row.get("tags") or {}
            if not isinstance(tags, dict):
                tags = {}
            out.append(
                {
                    "cloud_id": row.get("id", ""),
                    "name": row.get("name", ""),
                    "type": row.get("type", ""),
                    "service": _classify_service(row.get("type", "")),
                    "region": row.get("location", "unknown"),
                    "environment": tags.get("env", "unknown"),
                    "status": "active",
                    "application": tags.get("app", "unknown"),
                    "owner": tags.get("owner", "unassigned"),
                    "tags": [{"key": k, "value": str(v)} for k, v in tags.items()],
                    "utilization": {},
                    "series": {},
                    "metric_coverage": 0.0,
                    "monthly_cost": 0.0,
                }
            )
        return out

    def get_costs(
        self,
        db: Session,
        cloud_account_id: uuid.UUID,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        account = db.get(CloudAccount, cloud_account_id)
        if account is None or not account.subscription_id:
            return []

        if get_settings().mock_adapters:
            stmt = select(CostRecord).where(
                CostRecord.cloud_account_id == cloud_account_id,
                CostRecord.provider == self.provider,
                CostRecord.date >= start,
                CostRecord.date <= end,
            )
            rows = list(db.execute(stmt).scalars().all())
            return [
                {
                    "date": r.date.isoformat(),
                    "service": r.service,
                    "region": r.region,
                    "resource_id": str(r.resource_id) if r.resource_id else None,
                    "cost": float(r.cost),
                    "currency": r.currency,
                    "usage_quantity": float(r.usage_quantity),
                    "usage_unit": r.usage_unit,
                }
                for r in rows
            ]

        try:
            credential = self._credential(account)
            client = CostManagementClient(credential)
            definition = QueryDefinition(
                type="ActualCost",
                timeframe="Custom",
                time_period=QueryTimePeriod(
                    from_property=f"{start.isoformat()}T00:00:00Z",
                    to=f"{(end + timedelta(days=1)).isoformat()}T00:00:00Z",
                ),
                dataset=QueryDataset(
                    granularity="Daily",
                    aggregation={"totalCost": QueryAggregation(name="Cost", function="Sum")},
                    grouping=[
                        QueryGrouping(type="Dimension", name="ServiceName"),
                        QueryGrouping(type="Dimension", name="ResourceLocation"),
                    ],
                ),
            )
            result = client.query.usage(
                scope=f"/subscriptions/{account.subscription_id}",
                parameters=definition,
            )
        except (ClientAuthenticationError, AzureError, ValueError):
            return []

        columns = [c.name for c in result.columns]
        try:
            cost_idx = columns.index("Cost")
            date_idx = columns.index("UsageDate")
            service_idx = columns.index("ServiceName")
            location_idx = columns.index("ResourceLocation")
        except ValueError:
            return []

        out: list[dict[str, Any]] = []
        for row in result.rows or []:
            raw_date = str(row[date_idx])
            formatted = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}" if len(raw_date) == 8 else raw_date
            amount = Decimal(str(row[cost_idx]))
            if amount <= 0:
                continue
            out.append(
                {
                    "date": formatted,
                    "service": str(row[service_idx]) or "Unknown",
                    "region": str(row[location_idx]) or "global",
                    "resource_id": None,
                    "cost": float(amount),
                    "currency": result.currency or "USD",
                    "usage_quantity": 0.0,
                    "usage_unit": "",
                }
            )
        return out

    def get_metrics(
        self,
        db: Session,
        resource_ids: list[uuid.UUID],
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        return []

    def get_prices(self, resource_type: str, region: str) -> list[dict[str, Any]]:
        return []


def _classify_service(azure_type: str) -> str:
    t = azure_type.lower()
    if "virtualmachines" in t:
        return "Azure VMs"
    if "sql" in t:
        return "Azure SQL"
    if "storage" in t:
        return "Blob Storage"
    if "disks" in t:
        return "Azure Disk"
    if "networkinterfaces" in t or "publicipaddresses" in t:
        return "Networking"
    return "Other"