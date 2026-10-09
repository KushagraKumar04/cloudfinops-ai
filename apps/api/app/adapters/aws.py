import logging
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
from app.services.aws_costs import fetch_costs as fetch_aws_costs
from app.services.aws_discovery import discover_all
from app.services.aws_metrics import fetch_metrics_for_resources

logger = logging.getLogger("app.adapters.aws")

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

        settings = get_settings()
        enabled = [s.strip() for s in settings.aws_discovery_services.split(",") if s.strip()]

        try:
            session = self._session_for(account)
        except (ClientError, BotoCoreError, ValueError) as exc:
            logger.warning("AssumeRole failed for %s: %s", account.id, exc)
            return []

        regions = account.regions or ["us-east-1"]
        return discover_all(session, account.account_identifier, regions, enabled)

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
        except (ClientError, BotoCoreError, ValueError) as exc:
            logger.warning("AssumeRole failed for %s: %s", account.id, exc)
            return []

        return fetch_aws_costs(session, start, end)

    def get_metrics(
        self,
        db: Session,
        resource_ids: list[uuid.UUID],
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        if not resource_ids:
            return []

        rows = list(
            db.execute(select(Resource).where(Resource.id.in_(resource_ids))).scalars().all()
        )
        if not rows:
            return []

        if get_settings().mock_adapters:
            return []

        account_ids = {r.cloud_account_id for r in rows}
        if len(account_ids) != 1:
            return []
        account = db.get(CloudAccount, next(iter(account_ids)))
        if account is None or account.provider != self.provider:
            return []

        settings = get_settings()
        days = max(1, (end - start).days + 1)

        try:
            session = self._session_for(account)
        except (ClientError, BotoCoreError, ValueError) as exc:
            logger.warning("AssumeRole failed for %s: %s", account.id, exc)
            return []

        payload = [
            {"cloud_id": r.cloud_id, "service": r.service, "region": r.region}
            for r in rows
        ]
        regions = sorted({r.region for r in rows if r.region})
        metrics = fetch_metrics_for_resources(session, payload, regions, days)

        out: list[dict[str, Any]] = []
        for r in rows:
            data = metrics.get(r.cloud_id)
            if data is None:
                continue
            out.append(
                {
                    "resource_id": str(r.id),
                    "cloud_id": r.cloud_id,
                    "cpu": data.get("cpu"),
                    "memory": data.get("memory"),
                    "series": data.get("series", {}),
                    "coverage": data.get("coverage", 0.0),
                }
            )
        return out

    def get_prices(self, resource_type: str, region: str) -> list[dict[str, Any]]:
        return []

    def execute_action(
        self,
        db: Session,
        cloud_account_id: uuid.UUID,
        resource_cloud_id: str,
        action: str,
        params: dict,
    ) -> dict:
        account = db.get(CloudAccount, cloud_account_id)
        if account is None:
            return {"ok": False, "error": "Cloud account not found"}
        if not account.execution_role_configured:
            return {"ok": False, "error": "No execution role configured for this account"}
        if get_settings().mock_adapters:
            return self._mock_execute(resource_cloud_id, action, params)
        try:
            session = self._session_for(account)
        except (ClientError, BotoCoreError, ValueError) as exc:
            return {"ok": False, "error": f"AssumeRole failed: {exc}"}
        try:
            return self._live_execute(session, account, resource_cloud_id, action, params)
        except (ClientError, BotoCoreError) as exc:
            return {"ok": False, "error": str(exc)}

    def _mock_execute(self, resource_cloud_id: str, action: str, params: dict) -> dict:
        if action == "resize_instance":
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"instance_type": params.get("current_type", "m5.4xlarge")},
                "after": {"instance_type": params.get("target_type", "m5.2xlarge")},
                "rollback_reference": f"rollback:{resource_cloud_id}:{params.get('current_type', 'm5.4xlarge')}",
            }
        if action == "stop_instance":
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"state": "running"},
                "after": {"state": "stopped"},
                "rollback_reference": f"rollback:{resource_cloud_id}:start",
            }
        if action == "delete_volume":
            snapshot_id = f"snap-mock-{resource_cloud_id[-8:]}"
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"state": "available"},
                "after": {"state": "deleted"},
                "rollback_reference": snapshot_id,
            }
        if action == "release_eip":
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"associated": False},
                "after": {"state": "released"},
                "rollback_reference": None,
            }
        if action == "enable_tiering":
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"storage_class": "STANDARD"},
                "after": {"storage_class": "INTELLIGENT_TIERING"},
                "rollback_reference": f"rollback:{resource_cloud_id}:disable_tiering",
            }
        return {"ok": False, "error": f"Unsupported action: {action}"}

    def _live_execute(self, session, account: CloudAccount, resource_cloud_id: str, action: str, params: dict) -> dict:
        region = params.get("region") or (account.regions[0] if account.regions else "us-east-1")
        ec2 = session.client("ec2", region_name=region, config=BOTO_CONFIG)

        if action == "resize_instance":
            current = ec2.describe_instances(InstanceIds=[resource_cloud_id])
            state = current["Reservations"][0]["Instances"][0]["State"]["Name"]
            if state != "stopped":
                ec2.stop_instances(InstanceIds=[resource_cloud_id])
                waiter = ec2.get_waiter("instance_stopped")
                waiter.wait(InstanceIds=[resource_cloud_id], WaiterConfig={"Delay": 5, "MaxAttempts": 60})
            before_type = current["Reservations"][0]["Instances"][0]["InstanceType"]
            ec2.modify_instance_attribute(
                InstanceId=resource_cloud_id,
                InstanceType={"Value": params["target_type"]},
            )
            ec2.start_instances(InstanceIds=[resource_cloud_id])
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"instance_type": before_type},
                "after": {"instance_type": params["target_type"]},
                "rollback_reference": f"rollback:{resource_cloud_id}:{before_type}",
            }

        if action == "stop_instance":
            ec2.stop_instances(InstanceIds=[resource_cloud_id])
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"state": "running"},
                "after": {"state": "stopping"},
                "rollback_reference": f"rollback:{resource_cloud_id}:start",
            }

        if action == "delete_volume":
            snap = ec2.create_snapshot(VolumeId=resource_cloud_id, Description="CloudFinOps safety snapshot")
            ec2.delete_volume(VolumeId=resource_cloud_id)
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"state": "available"},
                "after": {"state": "deleted"},
                "rollback_reference": snap["SnapshotId"],
            }

        if action == "release_eip":
            ec2.release_address(AllocationId=resource_cloud_id)
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"associated": False},
                "after": {"state": "released"},
                "rollback_reference": None,
            }

        if action == "enable_tiering":
            s3 = session.client("s3", region_name=region, config=BOTO_CONFIG)
            bucket = resource_cloud_id.replace("arn:aws:s3:::", "")
            s3.put_bucket_intelligent_tiering_configuration(
                Bucket=bucket,
                Id="CloudFinOpsIntelligentTiering",
                IntelligentTieringConfiguration={
                    "Id": "CloudFinOpsIntelligentTiering",
                    "Status": "Enabled",
                    "Tierings": [{"Days": 90, "AccessTier": "ARCHIVE_ACCESS"}],
                },
            )
            return {
                "ok": True,
                "action": action,
                "resource": resource_cloud_id,
                "before": {"storage_class": "STANDARD"},
                "after": {"storage_class": "INTELLIGENT_TIERING"},
                "rollback_reference": f"rollback:{bucket}:disable_tiering",
            }

        return {"ok": False, "error": f"Unsupported action: {action}"}