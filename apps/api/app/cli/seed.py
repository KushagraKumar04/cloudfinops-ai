import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.anomaly import Anomaly
from app.models.audit import AuditEvent
from app.models.budget import Budget
from app.models.cloud_account import CloudAccount
from app.models.cost import CostRecord
from app.models.execution import Approval
from app.models.commitment import Commitment, CommitmentRecommendation
from app.models.notification import Notification, NotificationRule
from app.models.kubernetes import (
    KubernetesCluster,
    KubernetesCostAllocation,
    KubernetesNamespace,
    KubernetesWorkload,
)
from app.models.recommendation import Recommendation, RecommendationEvidence
from app.models.resource import Resource
from app.models.tenant import Tenant

TENANT_SLUG = "demo"


def _account_ids(tenant: Tenant) -> dict[str, uuid.UUID]:
    return {
        "aws_prod": uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:aws-prod"),
        "aws_stg": uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:aws-stg"),
        "az_prod": uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:az-prod"),
    }


def now_utc() -> datetime:
    return datetime.now(UTC)


def days_ago_iso(days: int, hour: int = 10, minute: int = 0) -> datetime:
    base = now_utc().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base - timedelta(days=days)


def seed_tenant(db: Session) -> Tenant:
    tenant = db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG)).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(slug=TENANT_SLUG, name="Demo Tenant")
        db.add(tenant)
        db.flush()
    return tenant


def clear_tenant_data(db: Session, tenant: Tenant) -> None:
    for model in (
        Approval,
        RecommendationEvidence,
        Recommendation,
        Anomaly,
        CostRecord,
        Resource,
        KubernetesCostAllocation,
        KubernetesWorkload,
        KubernetesNamespace,
        KubernetesCluster,
        CommitmentRecommendation,
        Commitment,
        Notification,
        NotificationRule,
        Budget,
        AuditEvent,
        CloudAccount,
    ):
        db.query(model).filter(getattr(model, "tenant_id", None) == tenant.id).delete(synchronize_session=False)
    db.flush()


def seed_cloud_accounts(db: Session, tenant: Tenant) -> dict[str, uuid.UUID]:
    ids = _account_ids(tenant)
    accounts = [
        CloudAccount(
            id=ids["aws_prod"],
            tenant_id=tenant.id,
            provider="AWS",
            name="AWS Production",
            account_identifier="123456789012",
            environment="production",
            status="connected",
            role_arn="arn:aws:iam::123456789012:role/CloudFinOpsReadOnly",
            regions=["us-east-1", "us-west-2", "eu-west-1"],
            read_only=True,
            execution_role_configured=False,
            last_sync_at=now_utc() - timedelta(hours=1),
            last_sync_status="success",
            last_sync_message="42,118 cost records · 812 resources updated",
            coverage={
                "billing": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=1)).isoformat()},
                "inventory": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=2)).isoformat()},
                "metrics": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=1)).isoformat()},
            },
            resource_count=812,
            monthly_spend=Decimal("98200"),
            currency="USD",
        ),
        CloudAccount(
            id=ids["aws_stg"],
            tenant_id=tenant.id,
            provider="AWS",
            name="AWS Staging",
            account_identifier="210987654321",
            environment="staging",
            status="connected",
            role_arn="arn:aws:iam::210987654321:role/CloudFinOpsReadOnly",
            regions=["us-west-2"],
            read_only=True,
            execution_role_configured=False,
            last_sync_at=now_utc() - timedelta(hours=3),
            last_sync_status="success",
            last_sync_message="12,402 cost records · 204 resources updated",
            coverage={
                "billing": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=3)).isoformat()},
                "inventory": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=5)).isoformat()},
                "metrics": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=3)).isoformat()},
            },
            resource_count=204,
            monthly_spend=Decimal("30200"),
            currency="USD",
        ),
        CloudAccount(
            id=ids["az_prod"],
            tenant_id=tenant.id,
            provider="Azure",
            name="Azure Production",
            account_identifier="sub-9f2c-1a4e",
            environment="production",
            status="syncing",
            subscription_id="9f2c-1a4e-8b7d-2c1f",
            tenant_external_id="acme.onmicrosoft.com",
            regions=["centralindia", "southeastasia"],
            read_only=True,
            execution_role_configured=False,
            last_sync_at=now_utc() - timedelta(hours=6),
            last_sync_status="partial",
            last_sync_message="Cost Management returned partial data for 2026-09-13 · retry scheduled",
            coverage={
                "billing": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=6)).isoformat()},
                "inventory": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=6)).isoformat()},
                "metrics": {"enabled": True, "last_sync_at": (now_utc() - timedelta(hours=6)).isoformat()},
            },
            resource_count=396,
            monthly_spend=Decimal("55920"),
            currency="USD",
        ),
    ]
    db.add_all(accounts)
    db.flush()
    return ids


RESOURCE_SEEDS = [
    {
        "id": "res_001",
        "account_key": "aws_prod",
        "provider": "AWS",
        "cloud_id": "i-0a1b2c3d4e5f67890",
        "name": "api-server-01",
        "type": "EC2 m5.4xlarge",
        "service": "EC2",
        "region": "us-east-1",
        "environment": "production",
        "status": "running",
        "application": "public-api",
        "owner": "platform-team",
        "tags": [{"key": "env", "value": "prod"}, {"key": "app", "value": "public-api"}],
        "age_days": 420,
        "monthly_cost": "580",
        "utilization": {"cpu": 12, "memory": 31, "networkMbps": 48, "iops": 180},
        "metric_coverage": "0.98",
    },
    {
        "id": "res_002",
        "account_key": "aws_prod",
        "provider": "AWS",
        "cloud_id": "i-0b2c3d4e5f67890ab",
        "name": "api-server-02",
        "type": "EC2 m5.2xlarge",
        "service": "EC2",
        "region": "us-east-1",
        "environment": "production",
        "status": "running",
        "application": "public-api",
        "owner": "platform-team",
        "tags": [{"key": "env", "value": "prod"}],
        "age_days": 420,
        "monthly_cost": "290",
        "utilization": {"cpu": 45, "memory": 58, "networkMbps": 62, "iops": 210},
        "metric_coverage": "0.97",
    },
    {
        "id": "res_003",
        "account_key": "aws_stg",
        "provider": "AWS",
        "cloud_id": "i-0c3d4e5f67890abc",
        "name": "staging-worker-01",
        "type": "EC2 t3.medium",
        "service": "EC2",
        "region": "us-west-2",
        "environment": "staging",
        "status": "running",
        "application": "batch-jobs",
        "owner": "platform-team",
        "tags": [{"key": "env", "value": "staging"}],
        "age_days": 180,
        "monthly_cost": "30",
        "utilization": {"cpu": 8, "memory": 22, "networkMbps": 12, "iops": 60},
        "metric_coverage": "0.95",
    },
    {
        "id": "res_005",
        "account_key": "aws_prod",
        "provider": "AWS",
        "cloud_id": "db-prod-01",
        "name": "orders-primary",
        "type": "RDS db.r5.2xlarge",
        "service": "RDS",
        "region": "us-east-1",
        "environment": "production",
        "status": "available",
        "application": "orders",
        "owner": "data-team",
        "tags": [{"key": "env", "value": "prod"}, {"key": "app", "value": "orders"}],
        "age_days": 620,
        "monthly_cost": "620",
        "utilization": {"cpu": 38, "memory": 62, "connections": 340, "iops": 1400},
        "metric_coverage": "0.99",
    },
    {
        "id": "res_006",
        "account_key": "aws_prod",
        "provider": "AWS",
        "cloud_id": "db-prod-replica",
        "name": "orders-replica-01",
        "type": "RDS db.r5.xlarge",
        "service": "RDS",
        "region": "us-east-1",
        "environment": "production",
        "status": "available",
        "application": "orders",
        "owner": "data-team",
        "tags": [{"key": "env", "value": "prod"}],
        "age_days": 610,
        "monthly_cost": "310",
        "utilization": {"cpu": 22, "memory": 45, "connections": 120, "iops": 480},
        "metric_coverage": "0.97",
    },
    {
        "id": "res_008",
        "account_key": "aws_prod",
        "provider": "AWS",
        "cloud_id": "arn:aws:s3:::acme-logs-prod",
        "name": "acme-logs-prod",
        "type": "S3 bucket",
        "service": "S3",
        "region": "us-east-1",
        "environment": "production",
        "status": "active",
        "application": "observability",
        "owner": "platform-team",
        "tags": [{"key": "env", "value": "prod"}],
        "age_days": 900,
        "monthly_cost": "840",
        "utilization": {"storageGb": 48000},
        "metric_coverage": "0.88",
    },
    {
        "id": "res_011",
        "account_key": "aws_prod",
        "provider": "AWS",
        "cloud_id": "vol-0f1e2d3c4b5a69788",
        "name": "orphan-volume-500gb",
        "type": "EBS gp3 500GB",
        "service": "EBS",
        "region": "us-east-1",
        "environment": "production",
        "status": "unattached",
        "application": "unknown",
        "owner": "unassigned",
        "tags": [],
        "age_days": 240,
        "monthly_cost": "60",
        "utilization": {},
        "metric_coverage": "0.0",
    },
    {
        "id": "res_013",
        "account_key": "aws_stg",
        "provider": "AWS",
        "cloud_id": "vol-0d3c4b5a697881122",
        "name": "staging-scratch-200gb",
        "type": "EBS gp2 200GB",
        "service": "EBS",
        "region": "us-west-2",
        "environment": "staging",
        "status": "unattached",
        "application": "unknown",
        "owner": "unassigned",
        "tags": [],
        "age_days": 400,
        "monthly_cost": "20",
        "utilization": {},
        "metric_coverage": "0.0",
    },
    {
        "id": "res_014",
        "account_key": "aws_prod",
        "provider": "AWS",
        "cloud_id": "eipalloc-0a9b8c7d6e5f4a3b2",
        "name": "unused-eip-1",
        "type": "Elastic IP",
        "service": "Networking",
        "region": "us-east-1",
        "environment": "production",
        "status": "unattached",
        "application": "unknown",
        "owner": "unassigned",
        "tags": [],
        "age_days": 120,
        "monthly_cost": "3.6",
        "utilization": {},
        "metric_coverage": "0.0",
    },
    {
        "id": "res_016",
        "account_key": "aws_prod",
        "provider": "AWS",
        "cloud_id": "arn:aws:eks:us-east-1:prod-cluster",
        "name": "prod-cluster",
        "type": "EKS cluster",
        "service": "EKS",
        "region": "us-east-1",
        "environment": "production",
        "status": "active",
        "application": "platform",
        "owner": "platform-team",
        "tags": [{"key": "env", "value": "prod"}],
        "age_days": 500,
        "monthly_cost": "3200",
        "utilization": {"cpu": 62, "memory": 71},
        "metric_coverage": "0.95",
    },
    {
        "id": "res_017",
        "account_key": "az_prod",
        "provider": "Azure",
        "cloud_id": "/subscriptions/sub-9f2c/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm-app-01",
        "name": "vm-app-01",
        "type": "Standard_D8s_v5",
        "service": "Azure VMs",
        "region": "centralindia",
        "environment": "production",
        "status": "running",
        "application": "internal-portal",
        "owner": "platform-team",
        "tags": [{"key": "env", "value": "prod"}, {"key": "app", "value": "internal-portal"}],
        "age_days": 300,
        "monthly_cost": "420",
        "utilization": {"cpu": 18, "memory": 34, "networkMbps": 22},
        "metric_coverage": "0.93",
    },
    {
        "id": "res_019",
        "account_key": "az_prod",
        "provider": "Azure",
        "cloud_id": "/subscriptions/sub-9f2c/resourceGroups/rg-dev/providers/Microsoft.Compute/virtualMachines/vm-dev-01",
        "name": "vm-dev-01",
        "type": "Standard_D2s_v5",
        "service": "Azure VMs",
        "region": "centralindia",
        "environment": "development",
        "status": "running",
        "application": "internal-portal",
        "owner": "platform-team",
        "tags": [{"key": "env", "value": "dev"}],
        "age_days": 150,
        "monthly_cost": "105",
        "utilization": {"cpu": 6, "memory": 18, "networkMbps": 5},
        "metric_coverage": "0.88",
    },
    {
        "id": "res_020",
        "account_key": "az_prod",
        "provider": "Azure",
        "cloud_id": "/subscriptions/sub-9f2c/resourceGroups/rg-prod/providers/Microsoft.Sql/servers/sql-prod-01",
        "name": "sql-prod-01",
        "type": "Azure SQL S3",
        "service": "Azure SQL",
        "region": "centralindia",
        "environment": "production",
        "status": "online",
        "application": "orders",
        "owner": "data-team",
        "tags": [{"key": "env", "value": "prod"}],
        "age_days": 480,
        "monthly_cost": "850",
        "utilization": {"cpu": 47, "memory": 68, "connections": 280, "iops": 1100},
        "metric_coverage": "0.96",
    },
]


def _build_series(seed: int, base: float, variance: float, length: int = 30) -> list[float]:
    rand = _seeded_rand(seed)
    out: list[float] = []
    for _ in range(length):
        v = base + (rand() - 0.5) * base * variance * 2
        out.append(round(max(0, v), 1))
    return out


def seed_resources(db: Session, tenant: Tenant, account_ids: dict[str, uuid.UUID]) -> dict[str, Resource]:
    out: dict[str, Resource] = {}
    for s in RESOURCE_SEEDS:
        resource_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:{s['id']}")
        seed = sum(ord(c) for c in s["id"])
        series: dict[str, list[float]] = {}
        util = s["utilization"]
        if util.get("cpu") is not None:
            series["cpu"] = _build_series(seed, float(util["cpu"]), 0.35)
        if util.get("memory") is not None:
            series["memory"] = _build_series(seed + 7, float(util["memory"]), 0.2)
        if util.get("networkMbps") is not None:
            series["network"] = _build_series(seed + 13, float(util["networkMbps"]), 0.4)

        resource = Resource(
            id=resource_id,
            tenant_id=tenant.id,
            cloud_account_id=account_ids[s["account_key"]],
            provider=s["provider"],
            cloud_id=s["cloud_id"],
            name=s["name"],
            type=s["type"],
            service=s["service"],
            region=s["region"],
            environment=s["environment"],
            status=s["status"],
            application=s["application"],
            owner=s["owner"],
            tags=s["tags"],
            utilization=s["utilization"],
            series=series,
            metric_coverage=Decimal(s["metric_coverage"]),
            monthly_cost=Decimal(s["monthly_cost"]),
            currency="USD",
        )
        db.add(resource)
        out[s["id"]] = resource
    db.flush()
    return out


def _seeded_rand(seed: int):
    state = seed

    def next_float() -> float:
        nonlocal state
        state = (state * 9301 + 49297) % 233280
        return state / 233280

    return next_float


def seed_cost_records(db: Session, tenant: Tenant, resources: dict[str, Resource]) -> None:
    today = date.today()
    resource_cost = {
        "res_001": Decimal("19.33"),
        "res_002": Decimal("9.67"),
        "res_003": Decimal("1.00"),
        "res_005": Decimal("20.67"),
        "res_006": Decimal("10.33"),
        "res_008": Decimal("28.00"),
        "res_011": Decimal("2.00"),
        "res_013": Decimal("0.67"),
        "res_014": Decimal("0.12"),
        "res_016": Decimal("106.67"),
        "res_017": Decimal("14.00"),
        "res_019": Decimal("3.50"),
        "res_020": Decimal("28.33"),
    }
    rows: list[CostRecord] = []
    for res_id, resource in resources.items():
        daily = resource_cost.get(res_id)
        if daily is None:
            continue
        seed = sum(ord(c) for c in res_id)
        rand = _seeded_rand(seed)
        for i in range(90):
            d = today - timedelta(days=i)
            dow = d.weekday()
            weekend = Decimal("0.82") if dow >= 5 else Decimal("1")
            trend = Decimal("1") + Decimal(str(round(((90 - i) / 90) * 0.18, 4)))
            noise = Decimal(str(round(1 + (rand() - 0.5) * 0.14, 4)))
            cost = (daily * weekend * trend * noise).quantize(Decimal("0.0001"))
            rows.append(
                CostRecord(
                    tenant_id=tenant.id,
                    cloud_account_id=resource.cloud_account_id,
                    resource_id=resource.id,
                    date=d,
                    provider=resource.provider,
                    service=resource.service,
                    region=resource.region,
                    cost=cost,
                    currency="USD",
                    usage_quantity=Decimal("1"),
                    usage_unit="day",
                    tags={},
                )
            )
    db.add_all(rows)
    db.flush()


def seed_budget(db: Session, tenant: Tenant) -> None:
    db.add(
        Budget(
            tenant_id=tenant.id,
            name="Monthly cloud budget",
            amount=Decimal("220000"),
            currency="USD",
            period="monthly",
            scope="all",
        )
    )
    db.flush()


def seed_anomalies(db: Session, tenant: Tenant, account_ids: dict[str, uuid.UUID]) -> None:
    db.add_all(
        [
            Anomaly(
                tenant_id=tenant.id,
                cloud_account_id=account_ids["aws_prod"],
                detected_at=days_ago_iso(2, 8),
                provider="AWS",
                service="EC2",
                delta_pct=Decimal("42"),
                delta_amount=Decimal("3820"),
                baseline_value=Decimal("9100"),
                observed_value=Decimal("12920"),
                description="Compute spend on us-east-1 increased 42% vs 14-day baseline.",
                severity="high",
            ),
            Anomaly(
                tenant_id=tenant.id,
                cloud_account_id=account_ids["aws_prod"],
                detected_at=days_ago_iso(4, 8),
                provider="AWS",
                service="Data Transfer",
                delta_pct=Decimal("28"),
                delta_amount=Decimal("640"),
                baseline_value=Decimal("2280"),
                observed_value=Decimal("2920"),
                description="Cross-region data transfer increased 28% week over week.",
                severity="medium",
            ),
            Anomaly(
                tenant_id=tenant.id,
                cloud_account_id=account_ids["az_prod"],
                detected_at=days_ago_iso(6, 8),
                provider="Azure",
                service="Azure SQL",
                delta_pct=Decimal("19"),
                delta_amount=Decimal("410"),
                baseline_value=Decimal("2160"),
                observed_value=Decimal("2570"),
                description="Azure SQL compute tier utilization above expected range.",
                severity="medium",
            ),
        ]
    )
    db.flush()


RECOMMENDATION_SEEDS = [
    {
        "key": "rec_001",
        "resource_key": "res_001",
        "type": "compute.rightsizing",
        "type_label": "Compute rightsizing",
        "title": "Rightsize api-server-01 from m5.4xlarge to m5.2xlarge",
        "summary": "Average CPU over the last 30 days is 12% with sufficient metric coverage. Downsize to m5.2xlarge to preserve headroom while reducing fixed compute cost.",
        "status": "pending",
        "risk": "MEDIUM",
        "risk_reasons": ["Production resource", "Peak CPU observed above 40%"],
        "confidence": "0.92",
        "current_monthly_cost": "580",
        "estimated_monthly_cost": "290",
        "estimated_monthly_savings": "290",
        "calculation_basis": [
            "30-day average CPU utilization",
            "Current region us-east-1",
            "On-demand list price for m5.2xlarge",
            "No active Savings Plan coverage",
        ],
        "current_state": [
            {"key": "Instance type", "value": "m5.4xlarge"},
            {"key": "vCPU", "value": "16"},
            {"key": "Memory", "value": "64 GiB"},
            {"key": "Monthly cost", "value": "$580"},
        ],
        "proposed_state": [
            {"key": "Instance type", "value": "m5.2xlarge"},
            {"key": "vCPU", "value": "8"},
            {"key": "Memory", "value": "32 GiB"},
            {"key": "Monthly cost", "value": "$290"},
        ],
        "impact": {
            "availability": "Requires a stop/start. Expected downtime under 5 minutes during the maintenance window.",
            "security": "No security group or IAM changes required.",
            "operational": "AMI and attached EBS volumes are compatible with the target family.",
        },
        "implementation_plan": [
            "Confirm maintenance window with the platform team",
            "Create an AMI snapshot of api-server-01",
            "Stop the instance",
            "Change instance type to m5.2xlarge",
            "Start the instance and verify health checks",
            "Monitor CPU for 24 hours; roll back if sustained CPU exceeds 70%",
        ],
        "evidence": [
            {"label": "Avg CPU (30d)", "value": "12%", "source": "CloudWatch"},
            {"label": "Peak CPU (30d)", "value": "46%", "source": "CloudWatch"},
            {"label": "Avg memory (30d)", "value": "31%", "source": "CloudWatch Agent"},
            {"label": "Metric coverage", "value": "98%", "source": "FinOps engine"},
            {"label": "Observed period", "value": "30 days", "source": "FinOps engine"},
        ],
        "age_days": 1,
    },
    {
        "key": "rec_002",
        "resource_key": "res_011",
        "type": "storage.unattached",
        "type_label": "Unattached storage",
        "title": "Delete unattached EBS volume orphan-volume-500gb",
        "summary": "Volume has been in available state for 240 days with no attachments, snapshots referencing it, or I/O activity. Safe to delete after snapshot retention check.",
        "status": "pending",
        "risk": "LOW",
        "risk_reasons": ["Not attached to any instance", "No I/O in 30 days"],
        "confidence": "0.99",
        "current_monthly_cost": "60",
        "estimated_monthly_cost": "0",
        "estimated_monthly_savings": "60",
        "calculation_basis": ["gp3 list price $0.08/GB-month", "500 GB provisioned"],
        "current_state": [
            {"key": "Size", "value": "500 GB"},
            {"key": "Type", "value": "gp3"},
            {"key": "Monthly cost", "value": "$60"},
        ],
        "proposed_state": [
            {"key": "Size", "value": "—"},
            {"key": "Type", "value": "—"},
            {"key": "Monthly cost", "value": "$0"},
        ],
        "impact": {
            "availability": "None. Volume is not attached to any instance.",
            "security": "None.",
            "operational": "A snapshot can be retained for 30 days before deletion.",
        },
        "implementation_plan": [
            "Notify the account owner of the orphan volume",
            "Create a snapshot tagged as a temporary safety net",
            "Wait 7 days for objection",
            "Delete the volume",
            "Delete the snapshot after 30 days if unused",
        ],
        "evidence": [
            {"label": "State", "value": "available", "source": "EC2 DescribeVolumes"},
            {"label": "Attachment", "value": "none", "source": "EC2 DescribeVolumes"},
            {"label": "Last I/O", "value": "> 30 days", "source": "CloudWatch VolumeReadOps"},
        ],
        "age_days": 1,
    },
    {
        "key": "rec_004",
        "resource_key": "res_017",
        "type": "compute.rightsizing",
        "type_label": "Compute rightsizing",
        "title": "Downsize vm-app-01 from Standard_D8s_v5 to Standard_D4s_v5",
        "summary": "Production VM with sustained low CPU and memory utilization. Requires approval and a defined maintenance window before resizing.",
        "status": "pending",
        "risk": "HIGH",
        "risk_reasons": ["Production resource", "Availability set member"],
        "confidence": "0.74",
        "current_monthly_cost": "420",
        "estimated_monthly_cost": "210",
        "estimated_monthly_savings": "210",
        "calculation_basis": [
            "30-day average CPU and memory utilization",
            "Azure Retail Prices for centralindia",
        ],
        "current_state": [
            {"key": "SKU", "value": "Standard_D8s_v5"},
            {"key": "vCPU", "value": "8"},
            {"key": "Memory", "value": "32 GiB"},
            {"key": "Monthly cost", "value": "$420"},
        ],
        "proposed_state": [
            {"key": "SKU", "value": "Standard_D4s_v5"},
            {"key": "vCPU", "value": "4"},
            {"key": "Memory", "value": "16 GiB"},
            {"key": "Monthly cost", "value": "$210"},
        ],
        "impact": {
            "availability": "Requires a deallocate/start. Downtime of 3–5 minutes.",
            "security": "No network or identity changes.",
            "operational": "Verify ephemeral disk usage before resizing.",
        },
        "implementation_plan": [
            "Confirm maintenance window with the application owner",
            "Snapshot OS and data disks",
            "Deallocate the VM",
            "Resize to Standard_D4s_v5",
            "Start the VM and verify health endpoints",
        ],
        "evidence": [
            {"label": "Avg CPU (30d)", "value": "18%", "source": "Azure Monitor"},
            {"label": "Peak CPU (30d)", "value": "62%", "source": "Azure Monitor"},
            {"label": "Avg memory (30d)", "value": "34%", "source": "Azure Monitor"},
            {"label": "Metric coverage", "value": "93%", "source": "FinOps engine"},
        ],
        "age_days": 2,
    },
    {
        "key": "rec_005",
        "resource_key": "res_008",
        "type": "storage.tiering",
        "type_label": "Storage tiering",
        "title": "Enable S3 Intelligent-Tiering on acme-logs-prod",
        "summary": "Logs bucket holds 48 TB of objects. Access patterns show a large cold tier. Intelligent-Tiering will move cold objects without lifecycle rules.",
        "status": "pending",
        "risk": "LOW",
        "risk_reasons": ["Storage class transition", "Reversible"],
        "confidence": "0.88",
        "current_monthly_cost": "840",
        "estimated_monthly_cost": "420",
        "estimated_monthly_savings": "420",
        "calculation_basis": [
            "Current S3 Standard usage",
            "Estimated 55% cold tier",
            "Intelligent-Tiering monitoring fee",
        ],
        "current_state": [
            {"key": "Storage class", "value": "S3 Standard"},
            {"key": "Lifecycle policy", "value": "none"},
            {"key": "Monthly cost", "value": "$840"},
        ],
        "proposed_state": [
            {"key": "Storage class", "value": "Intelligent-Tiering"},
            {"key": "Lifecycle policy", "value": "retained"},
            {"key": "Monthly cost", "value": "$420"},
        ],
        "impact": {
            "availability": "None. Objects remain readable at any time.",
            "security": "No encryption or ACL changes.",
            "operational": "Small per-object monitoring fee applies.",
        },
        "implementation_plan": [
            "Enable Intelligent-Tiering on the bucket",
            "Verify monitoring fee in next bill",
            "Review cold-tier volume after 30 days",
        ],
        "evidence": [
            {"label": "Storage size", "value": "48,000 GB", "source": "S3 Inventory"},
            {"label": "Objects not accessed in 90 days", "value": "63%", "source": "S3 Storage Lens"},
            {"label": "Lifecycle policy", "value": "none", "source": "S3 Bucket config"},
        ],
        "age_days": 3,
    },
    {
        "key": "rec_006",
        "resource_key": "res_003",
        "type": "compute.idle",
        "type_label": "Idle compute",
        "title": "Stop idle staging-worker-01 outside business hours",
        "summary": "Staging worker shows consistent low utilization during non-business hours. Scheduling a stop/start window reduces running hours without manual effort.",
        "status": "pending",
        "risk": "MEDIUM",
        "risk_reasons": ["Non-production resource", "Batch scheduling dependency"],
        "confidence": "0.90",
        "current_monthly_cost": "30",
        "estimated_monthly_cost": "12",
        "estimated_monthly_savings": "18",
        "calculation_basis": ["Current 24/7 running hours", "Proposed 12h×5d schedule"],
        "current_state": [
            {"key": "Running hours", "value": "24 × 7"},
            {"key": "Monthly cost", "value": "$30"},
        ],
        "proposed_state": [
            {"key": "Running hours", "value": "12 × 5 + nightly batch"},
            {"key": "Monthly cost", "value": "$12"},
        ],
        "impact": {
            "availability": "Unavailable outside business hours. Nightly batch window preserved.",
            "security": "None.",
            "operational": "Requires coordination with batch job owner.",
        },
        "implementation_plan": [
            "Confirm nightly batch window with the data team",
            "Create Instance Scheduler tag",
            "Enable scheduling",
            "Verify batch completes for one week",
        ],
        "evidence": [
            {"label": "Avg CPU off-hours", "value": "4%", "source": "CloudWatch"},
            {"label": "Avg CPU business hours", "value": "28%", "source": "CloudWatch"},
        ],
        "age_days": 4,
    },
    {
        "key": "rec_007",
        "resource_key": "res_006",
        "type": "database.rightsizing",
        "type_label": "Database rightsizing",
        "title": "Rightsize orders-replica-01 from db.r5.xlarge to db.r5.large",
        "summary": "Read replica carries low CPU and I/O load. Downsize is reversible but requires a maintenance window.",
        "status": "pending",
        "risk": "HIGH",
        "risk_reasons": ["Production database", "Replication role"],
        "confidence": "0.70",
        "current_monthly_cost": "310",
        "estimated_monthly_cost": "155",
        "estimated_monthly_savings": "155",
        "calculation_basis": ["30-day average CPU and IOPS", "RDS on-demand pricing us-east-1"],
        "current_state": [
            {"key": "Instance class", "value": "db.r5.xlarge"},
            {"key": "vCPU", "value": "4"},
            {"key": "Memory", "value": "32 GiB"},
            {"key": "Monthly cost", "value": "$310"},
        ],
        "proposed_state": [
            {"key": "Instance class", "value": "db.r5.large"},
            {"key": "vCPU", "value": "2"},
            {"key": "Memory", "value": "16 GiB"},
            {"key": "Monthly cost", "value": "$155"},
        ],
        "impact": {
            "availability": "A brief failover to the primary may be needed.",
            "security": "None.",
            "operational": "Confirm parameter groups are compatible with the smaller class.",
        },
        "implementation_plan": [
            "Coordinate with the orders team on a maintenance window",
            "Take a manual snapshot",
            "Modify the instance class",
            "Verify replication lag returns to baseline",
        ],
        "evidence": [
            {"label": "Avg CPU (30d)", "value": "22%", "source": "CloudWatch"},
            {"label": "Avg connections", "value": "120", "source": "CloudWatch"},
            {"label": "Replication lag", "value": "< 1s", "source": "RDS events"},
        ],
        "age_days": 5,
    },
    {
        "key": "rec_008",
        "resource_key": "res_020",
        "type": "database.rightsizing",
        "type_label": "Database rightsizing",
        "title": "Consider Azure SQL S2 for sql-prod-01",
        "summary": "Azure SQL S3 tier is underutilized. Policy requires approval from data governance before any production tier change.",
        "status": "pending",
        "risk": "BLOCKED",
        "risk_reasons": ["Production database", "Policy: database changes require approval"],
        "confidence": "0.66",
        "current_monthly_cost": "850",
        "estimated_monthly_cost": "670",
        "estimated_monthly_savings": "180",
        "calculation_basis": ["30-day DTU consumption", "Azure SQL tier pricing centralindia"],
        "current_state": [
            {"key": "Tier", "value": "S3"},
            {"key": "Max DTU", "value": "100"},
            {"key": "Monthly cost", "value": "$850"},
        ],
        "proposed_state": [
            {"key": "Tier", "value": "S2"},
            {"key": "Max DTU", "value": "50"},
            {"key": "Monthly cost", "value": "$670"},
        ],
        "impact": {
            "availability": "Tier change is online but may throttle during transition.",
            "security": "None.",
            "operational": "Blocked by policy until data governance approval is recorded.",
        },
        "implementation_plan": [
            "Request data governance review",
            "Confirm the change window",
            "Apply tier change during low traffic",
        ],
        "evidence": [
            {"label": "Avg DTU (30d)", "value": "47%", "source": "Azure Monitor"},
            {"label": "Peak DTU (30d)", "value": "78%", "source": "Azure Monitor"},
        ],
        "age_days": 6,
    },
    {
        "key": "rec_009",
        "resource_key": "res_019",
        "type": "compute.idle",
        "type_label": "Idle compute",
        "title": "Apply dev-hours schedule to vm-dev-01",
        "summary": "Development VM shows minimal off-hours utilization. Scheduling a stop reduces running hours without impacting developers.",
        "status": "deferred",
        "risk": "LOW",
        "risk_reasons": ["Non-production", "Reversible schedule"],
        "confidence": "0.94",
        "current_monthly_cost": "105",
        "estimated_monthly_cost": "30",
        "estimated_monthly_savings": "75",
        "calculation_basis": ["Current running hours", "Proposed 10h × 5d schedule"],
        "current_state": [
            {"key": "Running hours", "value": "24 × 7"},
            {"key": "Monthly cost", "value": "$105"},
        ],
        "proposed_state": [
            {"key": "Running hours", "value": "10 × 5"},
            {"key": "Monthly cost", "value": "$30"},
        ],
        "impact": {
            "availability": "Unavailable outside dev hours.",
            "security": "None.",
            "operational": "Deferred to allow a coordinated rollout.",
        },
        "implementation_plan": [
            "Confirm with dev team",
            "Apply auto-shutdown schedule",
            "Verify no failed overnight jobs",
        ],
        "evidence": [
            {"label": "Avg CPU off-hours", "value": "3%", "source": "Azure Monitor"},
            {"label": "Avg CPU business hours", "value": "24%", "source": "Azure Monitor"},
        ],
        "age_days": 7,
    },
    {
        "key": "rec_010",
        "resource_key": "res_013",
        "type": "storage.unattached",
        "type_label": "Unattached storage",
        "title": "Delete unattached EBS staging-scratch-200gb",
        "summary": "Staging volume unattached for 400 days with no I/O. Safe to remove.",
        "status": "pending",
        "risk": "LOW",
        "risk_reasons": ["Unattached", "No I/O in 30 days"],
        "confidence": "0.99",
        "current_monthly_cost": "20",
        "estimated_monthly_cost": "0",
        "estimated_monthly_savings": "20",
        "calculation_basis": ["gp2 list price $0.10/GB-month", "200 GB provisioned"],
        "current_state": [
            {"key": "Size", "value": "200 GB"},
            {"key": "Type", "value": "gp2"},
            {"key": "Monthly cost", "value": "$20"},
        ],
        "proposed_state": [
            {"key": "Size", "value": "—"},
            {"key": "Type", "value": "—"},
            {"key": "Monthly cost", "value": "$0"},
        ],
        "impact": {
            "availability": "None.",
            "security": "None.",
            "operational": "Confirm no scripts reference the volume ID.",
        },
        "implementation_plan": ["Confirm no references in code or IaC", "Delete the volume"],
        "evidence": [
            {"label": "State", "value": "available", "source": "EC2 DescribeVolumes"},
            {"label": "Last I/O", "value": "> 30 days", "source": "CloudWatch"},
        ],
        "age_days": 8,
    },
    {
        "key": "rec_011",
        "resource_key": "res_016",
        "type": "compute.rightsizing",
        "type_label": "Compute rightsizing",
        "title": "Reduce EKS node group size for prod-cluster",
        "summary": "Cluster-wide CPU and memory utilization remain below target. Reduction requires a rolling update.",
        "status": "approved",
        "risk": "MEDIUM",
        "risk_reasons": ["Production cluster", "Requires rolling node replacement"],
        "confidence": "0.80",
        "current_monthly_cost": "3200",
        "estimated_monthly_cost": "2310",
        "estimated_monthly_savings": "890",
        "calculation_basis": ["Cluster node pool utilization (30d)", "On-demand node pricing"],
        "current_state": [
            {"key": "Node count", "value": "12"},
            {"key": "Instance type", "value": "m5.2xlarge"},
            {"key": "Monthly cost", "value": "$3,200"},
        ],
        "proposed_state": [
            {"key": "Node count", "value": "9"},
            {"key": "Instance type", "value": "m5.2xlarge"},
            {"key": "Monthly cost", "value": "$2,310"},
        ],
        "impact": {
            "availability": "Rolling update. Pods will be rescheduled.",
            "security": "None.",
            "operational": "Cluster autoscaler min size must be adjusted alongside.",
        },
        "implementation_plan": [
            "Confirm cluster autoscaler bounds",
            "Drain one node and verify rescheduling",
            "Reduce node group desired size by 1 per hour",
        ],
        "evidence": [
            {"label": "Avg cluster CPU", "value": "62%", "source": "Container Insights"},
            {"label": "Avg cluster memory", "value": "71%", "source": "Container Insights"},
            {"label": "Pods pending (30d)", "value": "0", "source": "Kubernetes API"},
        ],
        "age_days": 9,
    },
]


def seed_recommendations(db: Session, tenant: Tenant, resources: dict[str, Resource]) -> None:
    for s in RECOMMENDATION_SEEDS:
        resource = resources.get(s["resource_key"])
        if resource is None:
            continue
        rec_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:{s['key']}")
        rec = Recommendation(
            id=rec_id,
            tenant_id=tenant.id,
            resource_id=resource.id,
            type=s["type"],
            type_label=s["type_label"],
            title=s["title"],
            summary=s["summary"],
            status=s["status"],
            risk=s["risk"],
            risk_reasons=s["risk_reasons"],
            confidence=Decimal(s["confidence"]),
            current_monthly_cost=Decimal(s["current_monthly_cost"]),
            estimated_monthly_cost=Decimal(s["estimated_monthly_cost"]),
            estimated_monthly_savings=Decimal(s["estimated_monthly_savings"]),
            currency="USD",
            calculation_basis=s["calculation_basis"],
            current_state=s["current_state"],
            proposed_state=s["proposed_state"],
            impact=s["impact"],
            implementation_plan=s["implementation_plan"],
            created_at=days_ago_iso(s["age_days"], 10, 14),
            updated_at=days_ago_iso(s["age_days"], 10, 14),
        )
        db.add(rec)
        for i, e in enumerate(s["evidence"]):
            db.add(
                RecommendationEvidence(
                    recommendation_id=rec_id,
                    position=i,
                    label=e["label"],
                    value=e["value"],
                    source=e["source"],
                )
            )
    db.flush()


def seed_audit_events(db: Session, tenant: Tenant) -> None:
    events = [
        {
            "at": days_ago_iso(0, 9, 12),
            "category": "recommendation",
            "severity": "info",
            "actor": "demo.user@acme.io",
            "action": "Approved recommendation",
            "subject": "rec_003 · Release unused Elastic IP unused-eip-1",
            "details": "Approved via Approvals queue.",
            "event_metadata": [{"key": "recommendation_id", "value": "rec_003"}],
        },
        {
            "at": days_ago_iso(0, 8, 4),
            "category": "billing.sync",
            "severity": "info",
            "actor": "ingestion-worker",
            "action": "Billing sync completed",
            "subject": "AWS Production · 2026-09-23",
            "details": "Records fetched 42118, inserted 42118, dedup 0.",
            "event_metadata": [{"key": "provider", "value": "AWS"}, {"key": "account", "value": "123456789012"}],
        },
        {
            "at": days_ago_iso(1, 17, 45),
            "category": "recommendation",
            "severity": "info",
            "actor": "finops-engine",
            "action": "Recommendation created",
            "subject": "rec_001 · Rightsize api-server-01",
            "details": "Rule: compute.rightsizing · avg_cpu_30d=12% · threshold=15%.",
            "event_metadata": [{"key": "recommendation_id", "value": "rec_001"}],
        },
        {
            "at": days_ago_iso(1, 15, 30),
            "category": "cost.anomaly",
            "severity": "warning",
            "actor": "finops-engine",
            "action": "Anomaly detected",
            "subject": "EC2 · us-east-1",
            "details": "Spend +42% vs 14-day baseline.",
            "event_metadata": [{"key": "provider", "value": "AWS"}, {"key": "delta_amount", "value": "3820"}],
        },
        {
            "at": days_ago_iso(2, 11, 10),
            "category": "cloud.account",
            "severity": "info",
            "actor": "admin@acme.io",
            "action": "Cloud account connected",
            "subject": "Azure Production · sub-9f2c-1a4e",
            "details": "Read-only connector established.",
            "event_metadata": [{"key": "provider", "value": "Azure"}, {"key": "mode", "value": "read-only"}],
        },
        {
            "at": days_ago_iso(2, 9, 0),
            "category": "policy",
            "severity": "warning",
            "actor": "policy-engine",
            "action": "Recommendation blocked",
            "subject": "rec_008 · Azure SQL tier change",
            "details": "Policy: database.require_approval=true.",
            "event_metadata": [{"key": "recommendation_id", "value": "rec_008"}],
        },
        {
            "at": days_ago_iso(6, 9, 12),
            "category": "auth",
            "severity": "critical",
            "actor": "unknown",
            "action": "Failed login",
            "subject": "admin@acme.io",
            "details": "Five consecutive failed attempts within two minutes.",
            "event_metadata": [{"key": "result", "value": "blocked"}],
        },
    ]
    for e in events:
        db.add(AuditEvent(tenant_id=tenant.id, **e))
    db.flush()


K8S_CLUSTERS = [
    {
        "key": "cluster_aws_prod",
        "account_key": "aws_prod",
        "provider": "AWS",
        "name": "prod-eks",
        "version": "1.30",
        "region": "us-east-1",
        "status": "active",
        "node_count": 12,
        "total_cpu_cores": 96,
        "total_memory_gb": 384,
        "monthly_cost": "3240",
        "namespaces": [
            {
                "name": "payments",
                "cpu_request_cores": "24.0",
                "cpu_limit_cores": "40.0",
                "cpu_usage_avg_cores": "7.2",
                "memory_request_gb": "96.0",
                "memory_limit_gb": "160.0",
                "memory_usage_avg_gb": "32.0",
                "monthly_cost": "1180",
                "workloads": [
                    {"name": "payments-api", "kind": "Deployment", "replicas": 6,
                     "cpu_request_cores": "12.0", "cpu_limit_cores": "20.0", "cpu_usage_avg_cores": "3.4",
                     "memory_request_gb": "48.0", "memory_limit_gb": "80.0", "memory_usage_avg_gb": "18.0",
                     "monthly_cost": "640", "potential_savings": "190", "over_provisioned": True},
                    {"name": "ledger-worker", "kind": "Deployment", "replicas": 4,
                     "cpu_request_cores": "8.0", "cpu_limit_cores": "12.0", "cpu_usage_avg_cores": "2.0",
                     "memory_request_gb": "32.0", "memory_limit_gb": "64.0", "memory_usage_avg_gb": "10.0",
                     "monthly_cost": "380", "potential_savings": "120", "over_provisioned": True},
                ],
            },
            {
                "name": "observability",
                "cpu_request_cores": "16.0",
                "cpu_limit_cores": "24.0",
                "cpu_usage_avg_cores": "9.0",
                "memory_request_gb": "64.0",
                "memory_limit_gb": "96.0",
                "memory_usage_avg_gb": "52.0",
                "monthly_cost": "820",
                "workloads": [
                    {"name": "prometheus", "kind": "StatefulSet", "replicas": 3,
                     "cpu_request_cores": "8.0", "cpu_limit_cores": "12.0", "cpu_usage_avg_cores": "4.5",
                     "memory_request_gb": "32.0", "memory_limit_gb": "48.0", "memory_usage_avg_gb": "26.0",
                     "monthly_cost": "420", "potential_savings": "60", "over_provisioned": False},
                    {"name": "grafana", "kind": "Deployment", "replicas": 2,
                     "cpu_request_cores": "4.0", "cpu_limit_cores": "6.0", "cpu_usage_avg_cores": "3.0",
                     "memory_request_gb": "16.0", "memory_limit_gb": "24.0", "memory_usage_avg_gb": "14.0",
                     "monthly_cost": "240", "potential_savings": "30", "over_provisioned": False},
                ],
            },
            {
                "name": "default",
                "cpu_request_cores": "4.0",
                "cpu_limit_cores": "8.0",
                "cpu_usage_avg_cores": "1.0",
                "memory_request_gb": "16.0",
                "memory_limit_gb": "32.0",
                "memory_usage_avg_gb": "4.0",
                "monthly_cost": "260",
                "workloads": [
                    {"name": "echo-server", "kind": "Deployment", "replicas": 2,
                     "cpu_request_cores": "2.0", "cpu_limit_cores": "4.0", "cpu_usage_avg_cores": "0.4",
                     "memory_request_gb": "8.0", "memory_limit_gb": "16.0", "memory_usage_avg_gb": "2.0",
                     "monthly_cost": "180", "potential_savings": "80", "over_provisioned": True},
                ],
            },
        ],
    },
    {
        "key": "cluster_azure_prod",
        "account_key": "az_prod",
        "provider": "Azure",
        "name": "prod-aks",
        "version": "1.29",
        "region": "centralindia",
        "status": "active",
        "node_count": 8,
        "total_cpu_cores": 64,
        "total_memory_gb": 256,
        "monthly_cost": "2160",
        "namespaces": [
            {
                "name": "internal-portal",
                "cpu_request_cores": "16.0",
                "cpu_limit_cores": "28.0",
                "cpu_usage_avg_cores": "6.4",
                "memory_request_gb": "64.0",
                "memory_limit_gb": "96.0",
                "memory_usage_avg_gb": "28.0",
                "monthly_cost": "980",
                "workloads": [
                    {"name": "portal-web", "kind": "Deployment", "replicas": 4,
                     "cpu_request_cores": "8.0", "cpu_limit_cores": "16.0", "cpu_usage_avg_cores": "3.2",
                     "memory_request_gb": "32.0", "memory_limit_gb": "48.0", "memory_usage_avg_gb": "14.0",
                     "monthly_cost": "520", "potential_savings": "140", "over_provisioned": True},
                    {"name": "portal-api", "kind": "Deployment", "replicas": 4,
                     "cpu_request_cores": "8.0", "cpu_limit_cores": "12.0", "cpu_usage_avg_cores": "3.2",
                     "memory_request_gb": "32.0", "memory_limit_gb": "48.0", "memory_usage_avg_gb": "14.0",
                     "monthly_cost": "460", "potential_savings": "110", "over_provisioned": True},
                ],
            },
            {
                "name": "batch-jobs",
                "cpu_request_cores": "12.0",
                "cpu_limit_cores": "20.0",
                "cpu_usage_avg_cores": "2.4",
                "memory_request_gb": "48.0",
                "memory_limit_gb": "80.0",
                "memory_usage_avg_gb": "10.0",
                "monthly_cost": "720",
                "workloads": [
                    {"name": "nightly-etl", "kind": "CronJob", "replicas": 1,
                     "cpu_request_cores": "8.0", "cpu_limit_cores": "16.0", "cpu_usage_avg_cores": "1.6",
                     "memory_request_gb": "32.0", "memory_limit_gb": "64.0", "memory_usage_avg_gb": "6.0",
                     "monthly_cost": "480", "potential_savings": "210", "over_provisioned": True},
                ],
            },
        ],
    },
]


def _build_k8s_trend(seed: int, base_daily: float, length: int = 90) -> list[float]:
    rand = _seeded_rand(seed)
    out: list[float] = []
    for i in range(length):
        dow = (length - 1 - i) % 7
        weekend = 0.88 if dow >= 5 else 1.0
        trend = 1 + ((length - 1 - i) / length) * 0.10
        noise = 1 + (rand() - 0.5) * 0.10
        out.append(round(base_daily * weekend * trend * noise, 4))
    return out


def seed_kubernetes(db: Session, tenant: Tenant, account_ids: dict[str, uuid.UUID]) -> None:
    today = date.today()
    for spec in K8S_CLUSTERS:
        cluster_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:{spec['key']}")
        cluster = KubernetesCluster(
            id=cluster_id,
            tenant_id=tenant.id,
            cloud_account_id=account_ids[spec["account_key"]],
            provider=spec["provider"],
            name=spec["name"],
            version=spec["version"],
            region=spec["region"],
            status=spec["status"],
            node_count=spec["node_count"],
            total_cpu_cores=Decimal(spec["total_cpu_cores"]),
            total_memory_gb=Decimal(spec["total_memory_gb"]),
            monthly_cost=Decimal(spec["monthly_cost"]),
        )
        db.add(cluster)
        db.flush()

        for ns_spec in spec["namespaces"]:
            ns_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:{spec['key']}/{ns_spec['name']}")
            namespace = KubernetesNamespace(
                id=ns_id,
                tenant_id=tenant.id,
                cluster_id=cluster.id,
                name=ns_spec["name"],
                cpu_request_cores=Decimal(ns_spec["cpu_request_cores"]),
                cpu_limit_cores=Decimal(ns_spec["cpu_limit_cores"]),
                cpu_usage_avg_cores=Decimal(ns_spec["cpu_usage_avg_cores"]),
                memory_request_gb=Decimal(ns_spec["memory_request_gb"]),
                memory_limit_gb=Decimal(ns_spec["memory_limit_gb"]),
                memory_usage_avg_gb=Decimal(ns_spec["memory_usage_avg_gb"]),
                monthly_cost=Decimal(ns_spec["monthly_cost"]),
            )
            db.add(namespace)
            db.flush()

            for wl_spec in ns_spec["workloads"]:
                wl_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:{spec['key']}/{ns_spec['name']}/{wl_spec['name']}")
                workload = KubernetesWorkload(
                    id=wl_id,
                    tenant_id=tenant.id,
                    cluster_id=cluster.id,
                    namespace_id=namespace.id,
                    name=wl_spec["name"],
                    kind=wl_spec["kind"],
                    replicas=wl_spec["replicas"],
                    cpu_request_cores=Decimal(wl_spec["cpu_request_cores"]),
                    cpu_limit_cores=Decimal(wl_spec["cpu_limit_cores"]),
                    cpu_usage_avg_cores=Decimal(wl_spec["cpu_usage_avg_cores"]),
                    memory_request_gb=Decimal(wl_spec["memory_request_gb"]),
                    memory_limit_gb=Decimal(wl_spec["memory_limit_gb"]),
                    memory_usage_avg_gb=Decimal(wl_spec["memory_usage_avg_gb"]),
                    monthly_cost=Decimal(wl_spec["monthly_cost"]),
                    potential_savings=Decimal(wl_spec["potential_savings"]),
                    over_provisioned=bool(wl_spec["over_provisioned"]),
                )
                db.add(workload)

            seed = sum(ord(c) for c in f"{spec['key']}/{ns_spec['name']}")
            base_daily = float(ns_spec["monthly_cost"]) / 30
            trend = _build_k8s_trend(seed, base_daily, length=90)
            for i, value in enumerate(trend):
                d = today - timedelta(days=len(trend) - 1 - i)
                total = Decimal(str(value))
                cpu_share = total * Decimal("0.55")
                mem_share = total * Decimal("0.30")
                storage_share = total * Decimal("0.10")
                network_share = total * Decimal("0.05")
                db.add(
                    KubernetesCostAllocation(
                        tenant_id=tenant.id,
                        cluster_id=cluster.id,
                        namespace_id=namespace.id,
                        workload_id=None,
                        date=d,
                        cost=total,
                        cpu_cost=cpu_share.quantize(Decimal("0.0001")),
                        memory_cost=mem_share.quantize(Decimal("0.0001")),
                        storage_cost=storage_share.quantize(Decimal("0.0001")),
                        network_cost=network_share.quantize(Decimal("0.0001")),
                    )
                )
        db.flush()


def seed_commitments(db: Session, tenant: Tenant, account_ids: dict[str, uuid.UUID]) -> None:
    today = date.today()

    commitments = [
        {
            "key": "c_aws_ec2_ri_12",
            "account_key": "aws_prod",
            "provider": "AWS",
            "type": "reserved_instance",
            "service": "EC2",
            "region": "us-east-1",
            "term_months": 12,
            "payment_option": "partial_upfront",
            "monthly_cost": "1840",
            "monthly_savings": "610",
            "instance_count": 8,
            "start_date": today - timedelta(days=180),
            "end_date": today + timedelta(days=185),
            "status": "active",
            "utilization_pct": "0.942",
        },
        {
            "key": "c_aws_sp_compute_12",
            "account_key": "aws_prod",
            "provider": "AWS",
            "type": "savings_plan",
            "service": "Compute",
            "region": "us-east-1",
            "term_months": 12,
            "payment_option": "no_upfront",
            "monthly_cost": "980",
            "monthly_savings": "190",
            "hourly_commitment": "1.35",
            "start_date": today - timedelta(days=120),
            "end_date": today + timedelta(days=245),
            "status": "active",
            "utilization_pct": "0.882",
        },
        {
            "key": "c_aws_rds_ri_12",
            "account_key": "aws_prod",
            "provider": "AWS",
            "type": "reserved_instance",
            "service": "RDS",
            "region": "us-east-1",
            "term_months": 12,
            "payment_option": "no_upfront",
            "monthly_cost": "420",
            "monthly_savings": "135",
            "instance_count": 2,
            "start_date": today - timedelta(days=310),
            "end_date": today + timedelta(days=55),
            "status": "active",
            "utilization_pct": "0.971",
        },
        {
            "key": "c_az_vm_ri_12",
            "account_key": "az_prod",
            "provider": "Azure",
            "type": "reserved_vm",
            "service": "Azure VMs",
            "region": "centralindia",
            "term_months": 12,
            "payment_option": "monthly",
            "monthly_cost": "310",
            "monthly_savings": "110",
            "instance_count": 1,
            "start_date": today - timedelta(days=90),
            "end_date": today + timedelta(days=275),
            "status": "active",
            "utilization_pct": "0.905",
        },
    ]

    for spec in commitments:
        db.add(
            Commitment(
                tenant_id=tenant.id,
                cloud_account_id=account_ids[spec["account_key"]],
                provider=spec["provider"],
                commitment_type=spec["type"],
                service=spec["service"],
                region=spec["region"],
                term_months=spec["term_months"],
                payment_option=spec["payment_option"],
                monthly_cost=Decimal(spec["monthly_cost"]),
                monthly_savings=Decimal(spec["monthly_savings"]),
                hourly_commitment=Decimal(spec["hourly_commitment"]) if spec.get("hourly_commitment") else None,
                instance_count=spec.get("instance_count"),
                start_date=spec["start_date"],
                end_date=spec["end_date"],
                status=spec["status"],
                utilization_pct=Decimal(spec["utilization_pct"]),
            )
        )

    recs = [
        {
            "key": "crec_aws_ec2_ri_36",
            "account_key": "aws_prod",
            "provider": "AWS",
            "type": "reserved_instance",
            "service": "EC2",
            "region": "us-east-1",
            "title": "Purchase 36-month EC2 Reserved Instances for m5 family",
            "summary": "Extend coverage of the m5 on-demand baseline with a 3-year standard RI. Coverage on m5 rises from 62% to 88%.",
            "rationale": "Steady m5 usage over the last 180 days with no plan to migrate families. 36-month partial upfront yields the highest effective discount.",
            "term_months": 36,
            "payment_option": "partial_upfront",
            "recommended_instance_count": 6,
            "monthly_cost": "2210",
            "monthly_savings": "980",
            "coverage_before_pct": "0.62",
            "coverage_after_pct": "0.88",
            "break_even_months": "6.8",
            "risk": "MEDIUM",
            "risk_reasons": ["Commits capacity for 3 years", "Requires upfront payment"],
            "confidence": "0.86",
            "evidence": [
                {"label": "m5 on-demand baseline (30d)", "value": "$4,180/mo", "source": "Cost records"},
                {"label": "Existing coverage", "value": "62%", "source": "Commitment snapshot"},
                {"label": "Effective discount", "value": "50%", "source": "AWS public pricing"},
            ],
            "impact": {
                "financial": "38% reduction on the covered m5 baseline",
                "operational": "No change to running capacity. Coverage is per instance family and region.",
                "risk": "Medium: 3-year commitment reduces flexibility if the workload changes",
            },
        },
        {
            "key": "crec_aws_ec2_sp_compute",
            "account_key": "aws_prod",
            "provider": "AWS",
            "type": "savings_plan",
            "service": "Compute",
            "region": "us-east-1",
            "title": "Increase Compute Savings Plan to $2.10/hr",
            "summary": "Raise the hourly compute commitment from $1.35 to $2.10. Coverage on eligible compute rises from 42% to 71% with no instance family lock-in.",
            "rationale": "Compute Savings Plan applies across EC2, Lambda, and Fargate. History shows stable compute baseline with room to grow.",
            "term_months": 12,
            "payment_option": "no_upfront",
            "recommended_hourly_commitment": "2.10",
            "monthly_cost": "1520",
            "monthly_savings": "310",
            "coverage_before_pct": "0.42",
            "coverage_after_pct": "0.71",
            "break_even_months": "0.0",
            "risk": "LOW",
            "risk_reasons": ["Flexible across services", "No upfront payment"],
            "confidence": "0.92",
            "evidence": [
                {"label": "Current SP commitment", "value": "$1.35/hr", "source": "Commitment record"},
                {"label": "Eligible on-demand baseline (30d)", "value": "$5,020/mo", "source": "Cost records"},
                {"label": "Utilization of existing SP", "value": "88.2%", "source": "Commitment snapshot"},
            ],
            "impact": {
                "financial": "Applies a 17% discount to incremental compute spend",
                "operational": "No capacity commitment. Rate only.",
                "risk": "Low: unused commitment only loses the discount, not the capital",
            },
        },
        {
            "key": "crec_aws_rds_ri_replace",
            "account_key": "aws_prod",
            "provider": "AWS",
            "type": "reserved_instance",
            "service": "RDS",
            "region": "us-east-1",
            "title": "Replace expiring RDS RI with 12-month no-upfront",
            "summary": "Existing RDS RI expires in 55 days. Renew at 12 months with no upfront to preserve cash flow.",
            "rationale": "Renewal cost is lower than on-demand for the same database family. No upfront means no capital commitment.",
            "term_months": 12,
            "payment_option": "no_upfront",
            "recommended_instance_count": 2,
            "monthly_cost": "470",
            "monthly_savings": "160",
            "coverage_before_pct": "0.72",
            "coverage_after_pct": "0.86",
            "break_even_months": "0.0",
            "risk": "LOW",
            "risk_reasons": ["Renewal of existing commitment", "Same instance family"],
            "confidence": "0.94",
            "evidence": [
                {"label": "Current RI expiry", "value": "55 days", "source": "Commitment record"},
                {"label": "On-demand baseline (30d)", "value": "$980/mo", "source": "Cost records"},
                {"label": "Effective discount", "value": "32%", "source": "AWS public pricing"},
            ],
            "impact": {
                "financial": "Continues the current discount at the same rate",
                "operational": "No change to running databases",
                "risk": "Low: same family, same term",
            },
        },
        {
            "key": "crec_az_vm_ri_expand",
            "account_key": "az_prod",
            "provider": "Azure",
            "type": "reserved_vm",
            "service": "Azure VMs",
            "region": "centralindia",
            "title": "Purchase Azure Reserved VM for internal-portal workload",
            "summary": "Cover the D-series VM baseline with a 1-year Azure Reserved VM. Coverage rises from 38% to 76%.",
            "rationale": "Stable D-series VM usage over 120 days. Azure Reserved VMs offer 31% savings at 1-year term.",
            "term_months": 12,
            "payment_option": "monthly",
            "recommended_instance_count": 3,
            "monthly_cost": "890",
            "monthly_savings": "290",
            "coverage_before_pct": "0.38",
            "coverage_after_pct": "0.76",
            "break_even_months": "0.0",
            "risk": "MEDIUM",
            "risk_reasons": ["1-year term", "Family and region lock-in"],
            "confidence": "0.82",
            "evidence": [
                {"label": "D-series on-demand baseline (30d)", "value": "$1,560/mo", "source": "Cost records"},
                {"label": "Current Azure coverage", "value": "38%", "source": "Commitment snapshot"},
                {"label": "Effective discount", "value": "31%", "source": "Azure public pricing"},
            ],
            "impact": {
                "financial": "31% reduction on the covered D-series baseline",
                "operational": "No change to running workloads",
                "risk": "Medium: family and region are fixed for the term",
            },
        },
        {
            "key": "crec_aws_eks_blocked",
            "account_key": "aws_prod",
            "provider": "AWS",
            "type": "reserved_instance",
            "service": "EKS",
            "region": "us-east-1",
            "title": "Consider 3-year compute commitment for prod-eks node pool",
            "summary": "Node pool has stable utilization but workload mix is under review. Blocked by policy until capacity planning completes.",
            "rationale": "Long-term commitment would lock in current instance family, which may change after the Q4 capacity review.",
            "term_months": 36,
            "payment_option": "all_upfront",
            "recommended_instance_count": 9,
            "monthly_cost": "2380",
            "monthly_savings": "720",
            "coverage_before_pct": "0.0",
            "coverage_after_pct": "0.62",
            "break_even_months": "9.4",
            "risk": "BLOCKED",
            "risk_reasons": ["Pending capacity review", "Policy: no 36-month commitments without planning sign-off"],
            "confidence": "0.62",
            "evidence": [
                {"label": "Node pool cost (30d)", "value": "$3,240", "source": "Cost records"},
                {"label": "Current coverage", "value": "0%", "source": "Commitment snapshot"},
                {"label": "Blocked by", "value": "Policy: capacity review", "source": "FinOps policy"},
            ],
            "impact": {
                "financial": "Potential 30% reduction if purchased",
                "operational": "Would lock the current m5 node family",
                "risk": "High: family and 36-month term in flux",
            },
        },
    ]

    for i, spec in enumerate(recs):
        days_ago = 2 + i
        created = days_ago_iso(days_ago, 11, 20)
        rec_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:{spec['key']}")
        db.add(
            CommitmentRecommendation(
                id=rec_id,
                tenant_id=tenant.id,
                cloud_account_id=account_ids[spec["account_key"]],
                provider=spec["provider"],
                commitment_type=spec["type"],
                service=spec["service"],
                region=spec["region"],
                title=spec["title"],
                summary=spec["summary"],
                rationale=spec["rationale"],
                term_months=spec["term_months"],
                payment_option=spec["payment_option"],
                recommended_hourly_commitment=(
                    Decimal(spec["recommended_hourly_commitment"])
                    if spec.get("recommended_hourly_commitment")
                    else None
                ),
                recommended_instance_count=spec.get("recommended_instance_count"),
                estimated_monthly_cost=Decimal(spec["monthly_cost"]),
                estimated_monthly_savings=Decimal(spec["monthly_savings"]),
                estimated_annual_savings=Decimal(spec["monthly_savings"]) * 12,
                coverage_before_pct=Decimal(spec["coverage_before_pct"]),
                coverage_after_pct=Decimal(spec["coverage_after_pct"]),
                break_even_months=Decimal(spec["break_even_months"]),
                risk=spec["risk"],
                risk_reasons=spec["risk_reasons"],
                confidence=Decimal(spec["confidence"]),
                status="pending",
                evidence=spec["evidence"],
                impact=spec["impact"],
                created_at=created,
                updated_at=created,
            )
        )
    db.flush()


def seed_notifications(db: Session, tenant: Tenant, account_ids: dict[str, uuid.UUID]) -> None:
    rules = [
        {
            "key": "nr_cost_anomaly_email",
            "name": "Cost anomalies → FinOps team",
            "description": "Email the FinOps team whenever a cost anomaly is detected at warning or above.",
            "event_type": "cost.anomaly.detected",
            "channel": "email",
            "destination": {"to": ["finops@acme.io"], "cc": ["cloud-ops@acme.io"]},
            "min_severity": "warning",
        },
        {
            "key": "nr_high_risk_webhook",
            "name": "High-risk recommendations → Slack webhook",
            "description": "POST to the ops Slack channel when a high-risk recommendation is approved.",
            "event_type": "recommendation.high_risk",
            "channel": "webhook",
            "destination": {
                "url": "https://hooks.slack.com/services/T00000000/B00000000/example",
                "headers": {"X-Source": "cloudfinops-ai"},
            },
            "min_severity": "warning",
        },
        {
            "key": "nr_policy_blocked_email",
            "name": "Policy blocks → security review",
            "description": "Email security when an execution is blocked by policy.",
            "event_type": "policy.blocked",
            "channel": "email",
            "destination": {"to": ["security@acme.io"]},
            "min_severity": "warning",
        },
    ]

    created_rules: list[NotificationRule] = []
    for spec in rules:
        rule_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant.id}:{spec['key']}")
        rule = NotificationRule(
            id=rule_id,
            tenant_id=tenant.id,
            name=spec["name"],
            description=spec["description"],
            event_type=spec["event_type"],
            channel=spec["channel"],
            destination=spec["destination"],
            min_severity=spec["min_severity"],
            enabled=True,
            fire_count=0,
        )
        db.add(rule)
        created_rules.append(rule)

    db.flush()

    history = [
        {
            "at": days_ago_iso(0, 9, 12),
            "event_type": "cost.anomaly.detected",
            "severity": "warning",
            "channel": "email",
            "subject": "Cost anomaly: EC2 +42% in us-east-1",
            "body": "Detected $3,820 in additional compute spend vs 14-day baseline.",
            "status": "suppressed",
            "error": "SMTP disabled; delivery logged but not sent",
            "destination": {"to": ["finops@acme.io"]},
            "rule_index": 0,
        },
        {
            "at": days_ago_iso(1, 17, 45),
            "event_type": "recommendation.high_risk",
            "severity": "warning",
            "channel": "webhook",
            "subject": "High-risk recommendation approved: Downsize vm-app-01",
            "body": "Approver: demo.user@acme.io\nRisk: HIGH\nEstimated savings: $210.00/mo",
            "status": "delivered",
            "error": None,
            "destination": {"url": "https://hooks.slack.com/services/T00000000/B00000000/example"},
            "rule_index": 1,
        },
        {
            "at": days_ago_iso(2, 11, 10),
            "event_type": "policy.blocked",
            "severity": "warning",
            "channel": "email",
            "subject": "Execution blocked: resize_instance",
            "body": "Recommendation was blocked by policy: production.allow_auto_execution.",
            "status": "suppressed",
            "error": "SMTP disabled; delivery logged but not sent",
            "destination": {"to": ["security@acme.io"]},
            "rule_index": 2,
        },
        {
            "at": days_ago_iso(3, 8, 0),
            "event_type": "cost.anomaly.detected",
            "severity": "critical",
            "channel": "email",
            "subject": "Cost anomaly: RDS +58% in us-east-1",
            "body": "Detected $2,140 in additional database spend.",
            "status": "suppressed",
            "error": "SMTP disabled; delivery logged but not sent",
            "destination": {"to": ["finops@acme.io"]},
            "rule_index": 0,
        },
    ]

    for idx, item in enumerate(history):
        rule = created_rules[item["rule_index"]]
        read_at = None if idx < 2 else item["at"]
        db.add(
            Notification(
                tenant_id=tenant.id,
                rule_id=rule.id,
                event_type=item["event_type"],
                severity=item["severity"],
                channel=item["channel"],
                subject=item["subject"],
                body=item["body"],
                destination=item["destination"],
                event_metadata={"seeded": True},
                status=item["status"],
                error=item["error"],
                attempt=1,
                duration_ms=0,
                read_at=read_at,
                created_at=item["at"],
            )
        )

    for rule in created_rules:
        rule.last_fired_at = history[0]["at"]
        rule.fire_count = 1

    db.flush()


def seed_settings(db: Session, tenant: Tenant) -> None:
    tenant.settings = {
        "policies": [
            {
                "id": "production.allow_auto_execution",
                "scope": "Production resources",
                "description": "Block automatic execution of any mutation against production resources.",
                "enabled": True,
                "requiresApproval": True,
                "blockAutoExecution": True,
            },
            {
                "id": "database.require_approval",
                "scope": "Databases",
                "description": "Database changes require approval and a maintenance window.",
                "enabled": True,
                "requiresApproval": True,
                "blockAutoExecution": True,
            },
            {
                "id": "network.require_security_review",
                "scope": "Network resources",
                "description": "Network changes require a security reviewer sign-off.",
                "enabled": True,
                "requiresApproval": True,
                "blockAutoExecution": False,
            },
            {
                "id": "delete_resource.require_approval",
                "scope": "Deletion",
                "description": "Any delete action requires human approval regardless of risk.",
                "enabled": True,
                "requiresApproval": True,
                "blockAutoExecution": True,
            },
            {
                "id": "max_monthly_savings_claim.require_evidence",
                "scope": "Savings claims",
                "description": "Savings estimates must include evidence and calculation basis.",
                "enabled": True,
                "requiresApproval": False,
                "blockAutoExecution": False,
            },
        ],
        "thresholds": [
            {
                "id": "cpu_rightsizing",
                "label": "CPU rightsizing threshold",
                "description": "Average 30-day CPU below this value makes a compute resource a candidate.",
                "value": 15,
                "unit": "%",
                "minimum": 5,
                "maximum": 40,
            },
            {
                "id": "memory_rightsizing",
                "label": "Memory rightsizing threshold",
                "description": "Average 30-day memory below this value makes a compute resource a candidate.",
                "value": 25,
                "unit": "%",
                "minimum": 5,
                "maximum": 60,
            },
            {
                "id": "metric_coverage",
                "label": "Minimum metric coverage",
                "description": "Required metric coverage to consider a resource for a recommendation.",
                "value": 85,
                "unit": "%",
                "minimum": 50,
                "maximum": 100,
            },
            {
                "id": "anomaly_pct",
                "label": "Anomaly percentage change",
                "description": "Percentage change from baseline that triggers anomaly detection.",
                "value": 20,
                "unit": "%",
                "minimum": 5,
                "maximum": 100,
            },
            {
                "id": "idle_days",
                "label": "Idle period",
                "description": "Number of consecutive days without activity to classify a resource as idle.",
                "value": 30,
                "unit": "days",
                "minimum": 7,
                "maximum": 90,
            },
        ],
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.2,
            "maxTokens": 2048,
            "cacheEnabled": True,
            "compactToolOutputs": True,
            "promptVersion": "2026-09-01",
        },
    }
    db.flush()


def seed_tenant_data(db: Session, tenant: Tenant) -> None:
    account_ids = seed_cloud_accounts(db, tenant)
    resources = seed_resources(db, tenant, account_ids)
    seed_cost_records(db, tenant, resources)
    seed_budget(db, tenant)
    seed_anomalies(db, tenant, account_ids)
    seed_recommendations(db, tenant, resources)
    seed_audit_events(db, tenant)
    seed_kubernetes(db, tenant, account_ids)
    seed_commitments(db, tenant, account_ids)
    seed_notifications(db, tenant, account_ids)
    seed_settings(db, tenant)


def run() -> None:
    db: Session = SessionLocal()
    try:
        tenant = seed_tenant(db)
        clear_tenant_data(db, tenant)
        seed_tenant_data(db, tenant)
        db.commit()
        print("Seed complete.")
        print(f"  tenant: {tenant.slug}")
        print(f"  cloud accounts: 3")
        print(f"  resources: 13")
        print(f"  cost records: 900")
        print(f"  recommendations: {len(RECOMMENDATION_SEEDS)}")
        print(f"  audit events: 7")
        print(f"  k8s clusters: {len(K8S_CLUSTERS)}")
        print(f"  commitments: 4 active · 5 recommendations")
        print(f"  notifications: 3 rules · 4 deliveries")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
