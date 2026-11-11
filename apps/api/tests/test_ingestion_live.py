from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.models.cloud_account import CloudAccount
from app.services.ingestion import IngestionService


def _seed_account(db_session, tenant):
    account = CloudAccount(
        tenant_id=tenant.id,
        provider="AWS",
        name="Live Test AWS",
        account_identifier="999999999999",
        environment="production",
        status="connected",
        role_arn="arn:aws:iam::999999999999:role/CloudFinOpsReadOnly",
        regions=["us-east-1"],
        coverage={},
        connection_verified=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def test_ingestion_persists_resources_and_costs(monkeypatch, db_session, seeded_tenant):
    account = _seed_account(db_session, seeded_tenant)

    fake_adapter = MagicMock()
    fake_adapter.get_resources.return_value = [
        {
            "cloud_id": "i-live-1",
            "name": "live-instance",
            "type": "EC2 m5.large",
            "service": "EC2",
            "region": "us-east-1",
            "environment": "production",
            "status": "running",
            "application": "test",
            "owner": "tester",
            "tags": [{"key": "env", "value": "production"}],
            "utilization": {},
            "series": {},
            "metric_coverage": 0.0,
            "monthly_cost": 0.0,
        }
    ]
    fake_adapter.get_costs.return_value = [
        {
            "date": "2026-10-01",
            "service": "EC2",
            "region": "us-east-1",
            "resource_id": None,
            "cost": 42.5,
            "currency": "USD",
            "usage_quantity": 0,
            "usage_unit": "",
        }
    ]
    fake_adapter.get_metrics.return_value = []

    monkeypatch.setattr(
        "app.services.ingestion.get_adapter",
        lambda provider: fake_adapter,
    )

    service = IngestionService(db_session)
    result = service.sync_account(account.id, days=7)

    assert result.resources_inserted == 1
    assert result.costs_inserted >= 1

    from app.models.resource import Resource

    resource = db_session.execute(
        select(Resource).where(Resource.cloud_id == "i-live-1")
    ).scalar_one()
    assert resource.name == "live-instance"
    assert resource.service == "EC2"

    db_session.refresh(account)
    assert account.status == "connected"
    assert account.sync_phase == "complete"
    assert account.sync_progress_pct == 100


def test_ingestion_applies_metrics(monkeypatch, db_session, seeded_tenant):
    account = _seed_account(db_session, seeded_tenant)
    account.regions = ["us-east-1"]
    db_session.commit()

    fake_adapter = MagicMock()
    fake_adapter.get_resources.return_value = [
        {
            "cloud_id": "i-metrics",
            "name": "metrics-instance",
            "type": "EC2 m5.large",
            "service": "EC2",
            "region": "us-east-1",
            "environment": "production",
            "status": "running",
            "application": "test",
            "owner": "tester",
            "tags": [],
            "utilization": {},
            "series": {},
            "metric_coverage": 0.0,
            "monthly_cost": 0.0,
        }
    ]
    fake_adapter.get_costs.return_value = []

    def metrics_for(db, resource_ids, start, end):
        from app.models.resource import Resource

        rows = db.execute(select(Resource).where(Resource.id.in_(resource_ids))).scalars().all()
        out = []
        for r in rows:
            out.append(
                {
                    "resource_id": str(r.id),
                    "cloud_id": r.cloud_id,
                    "cpu": 12.5,
                    "memory": None,
                    "series": {"cpu": [12.5] * 30},
                    "coverage": 0.95,
                }
            )
        return out

    fake_adapter.get_metrics.side_effect = metrics_for

    monkeypatch.setattr(
        "app.services.ingestion.get_adapter",
        lambda provider: fake_adapter,
    )

    service = IngestionService(db_session)
    result = service.sync_account(account.id, days=7)

    assert result.metrics_applied == 1

    from app.models.resource import Resource

    resource = db_session.execute(
        select(Resource).where(Resource.cloud_id == "i-metrics")
    ).scalar_one()
    assert float(resource.metric_coverage) == 0.95
    assert resource.utilization.get("cpu") == 12.5