import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.cloud_account import CloudAccount
from app.models.cost import CostRecord
from app.models.resource import Resource
from app.services.encryption import decrypt_secret

BOTO_CONFIG = Config(retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=10, read_timeout=30)


class AWSAdapter:
    provider = "AWS"

    def _session_for(self, account: CloudAccount) -> boto3.Session:
        if not account.role_arn:
            raise ValueError("AWS account is missing role_arn")
        sts = boto3.client("sts", config=BOTO_CONFIG)
        assume_kwargs: dict[str, Any] = {
            "RoleArn": account.role_arn,
            "RoleSessionName": "cloudfinops-sync",
            "DurationInSeconds": 3600,
        }
        if account.external_id:
            assume_kwargs["ExternalId"] = account.external_id
        creds = sts.assume_role(**assume_kwargs)["Credentials"]
        return boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )

    def validate_connection(self, db: Session, cloud_account_id: uuid.UUID) -> tuple[bool, str]:
        account = db.get(CloudAccount, cloud_account_id)
        if account is None or account.provider != self.provider:
            return False, "Cloud account not found"
        if not account.role_arn:
            return False, "Missing role ARN"
        if get_settings().mock_adapters:
            return True, f"Mock mode: {account.role_arn} validated"
        try:
            session = self._session_for(account)
            sts = session.client("sts", config=BOTO_CONFIG)
            ident = sts.get_caller_identity()
            return True, f"Verified as {ident['Arn']}"
        except (ClientError, BotoCoreError, ValueError) as exc:
            return False, f"AssumeRole failed: {exc}"

    def get_resources(self, db: Session, cloud_account_id: uuid.UUID) -> list[dict[str, Any]]:
        account = db.get(CloudAccount, cloud_account_id)
        if account is None:
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
            session = self._session_for(account)
        except Exception:
            return []
        out: list[dict[str, Any]] = []
        for region in account.regions or ["us-east-1"]:
            try:
                ec2 = session.client("ec2", region_name=region, config=BOTO_CONFIG)
                for reservation in ec2.describe_instances().get("Reservations", []):
                    for inst in reservation.get("Instances", []):
                        state = inst.get("State", {}).get("Name", "unknown")
                        tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                        out.append(
                            {
                                "cloud_id": inst["InstanceId"],
                                "name": tags.get("Name", inst["InstanceId"]),
                                "type": f"EC2 {inst.get('InstanceType', 'unknown')}",
                                "service": "EC2",
                                "region": region,
                                "environment": tags.get("env", "unknown"),
                                "status": state,
                                "application": tags.get("app", "unknown"),
                                "owner": tags.get("owner", "unassigned"),
                                "tags": [{"key": k, "value": v} for k, v in tags.items()],
                                "utilization": {},
                                "series": {},
                                "metric_coverage": 0.0,
                                "monthly_cost": 0.0,
                            }
                        )
            except (ClientError, BotoCoreError):
                continue
        return out

    def get_costs(
        self,
        db: Session,
        cloud_account_id: uuid.UUID,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        account = db.get(CloudAccount, cloud_account_id)
        if account is None:
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
            session = self._session_for(account)
        except Exception:
            return []
        try:
            ce = session.client("ce", region_name="us-east-1", config=BOTO_CONFIG)
            response = ce.get_cost_and_usage(
                TimePeriod={"Start": start.isoformat(), "End": (end + timedelta(days=1)).isoformat()},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[
                    {"Type": "DIMENSION", "Key": "SERVICE"},
                    {"Type": "DIMENSION", "Key": "REGION"},
                ],
            )
        except (ClientError, BotoCoreError):
            return []

        out: list[dict[str, Any]] = []
        for bucket in response.get("ResultsByTime", []):
            bucket_date = bucket["TimePeriod"]["Start"]
            for group in bucket.get("Groups", []):
                keys = group["Keys"]
                amount = Decimal(group["Metrics"]["UnblendedCost"]["Amount"])
                service = keys[0] if len(keys) > 0 else "Unknown"
                region = keys[1] if len(keys) > 1 else "global"
                if amount <= 0:
                    continue
                out.append(
                    {
                        "date": bucket_date,
                        "service": service,
                        "region": region,
                        "resource_id": None,
                        "cost": float(amount),
                        "currency": group["Metrics"]["UnblendedCost"].get("Unit", "USD"),
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


def _noop_decrypt(token: str) -> str:
    return decrypt_secret(token)    