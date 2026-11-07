import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.models.anomaly import Anomaly
from app.models.cost import CostRecord


def _seed_costs(db_session, tenant, account_id):
    today = date.today()
    for i in range(10):
        d = today - timedelta(days=i)
        db_session.add(
            CostRecord(
                tenant_id=tenant.id,
                cloud_account_id=account_id,
                date=d,
                provider="AWS",
                service="EC2",
                region="us-east-1",
                cost=Decimal("100"),
                currency="USD",
                usage_quantity=Decimal("1"),
                usage_unit="day",
                tags={},
            )
        )
        db_session.add(
            CostRecord(
                tenant_id=tenant.id,
                cloud_account_id=account_id,
                date=d,
                provider="AWS",
                service="RDS",
                region="us-east-1",
                cost=Decimal("50"),
                currency="USD",
                usage_quantity=Decimal("1"),
                usage_unit="day",
                tags={},
            )
        )
    db_session.commit()


def test_cost_summary(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/costs/summary", params={"range": "7d"})
    assert r.status_code == 200
    body = r.json()
    assert body["currentSpend"] == 1050.0
    assert body["currency"] == "USD"
    assert "start" in body["period"]
    assert body["topMover"]["name"] == "EC2"


def test_cost_summary_with_provider_filter(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/costs/summary", params={"range": "7d", "provider": "Azure"})
    assert r.status_code == 200
    assert r.json()["currentSpend"] == 0.0


def test_cost_trends(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/costs/trends", params={"range": "7d"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 7
    assert body[-1]["total"] == 150.0
    assert body[-1]["aws"] == 150.0
    assert body[-1]["azure"] == 0.0


def test_cost_breakdown_service(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/costs/breakdown", params={"range": "7d", "dimension": "service"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["name"] == "EC2"
    assert body[0]["spend"] == 700.0
    assert body[1]["name"] == "RDS"
    assert body[1]["spend"] == 350.0


def test_cost_breakdown_region(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_costs(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/costs/breakdown", params={"range": "7d", "dimension": "region"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "us-east-1"


def test_cost_anomalies(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    db_session.add(
        Anomaly(
            tenant_id=seeded_tenant.id,
            cloud_account_id=account.id,
            detected_at=date.today(),
            provider="AWS",
            service="EC2",
            delta_pct=Decimal("42"),
            delta_amount=Decimal("3820"),
            baseline_value=Decimal("9100"),
            observed_value=Decimal("12920"),
            description="Test anomaly",
            severity="high",
        )
    )
    db_session.commit()

    r = client.get("/api/v1/costs/anomalies")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["severity"] == "high"
    assert body[0]["account"] == "AWS Production"

def test_cost_by_resource_empty(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from app.models.resource import Resource
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    resource = Resource(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        provider="AWS",
        cloud_id="i-cost-history-empty",
        name="empty-history",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
    )
    db_session.add(resource)
    db_session.commit()

    r = client.get(f"/api/v1/costs/by-resource/{resource.id}?days=7")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 7
    assert all(p["cost"] == 0 for p in body)


def test_cost_by_resource_with_data(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from app.models.resource import Resource
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    resource = Resource(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        provider="AWS",
        cloud_id="i-cost-history",
        name="cost-history",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
    )
    db_session.add(resource)
    db_session.flush()

    today = date.today()
    for i in range(10):
        d = today - timedelta(days=i)
        db_session.add(
            CostRecord(
                tenant_id=seeded_tenant.id,
                cloud_account_id=account.id,
                resource_id=resource.id,
                date=d,
                provider="AWS",
                service="EC2",
                region="us-east-1",
                cost=Decimal("10"),
                currency="USD",
                usage_quantity=Decimal("1"),
                usage_unit="day",
                tags={},
            )
        )
    db_session.commit()

    r = client.get(f"/api/v1/costs/by-resource/{resource.id}?days=10")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 10
    assert all(p["cost"] == 10.0 for p in body)


def test_cost_by_resource_404(client, seeded_tenant):
    import uuid

    r = client.get(f"/api/v1/costs/by-resource/{uuid.uuid4()}")
    assert r.status_code == 404


def test_cost_by_resource_invalid_days(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from app.models.resource import Resource
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    resource = Resource(
        tenant_id=seeded_tenant.id,
        cloud_account_id=account.id,
        provider="AWS",
        cloud_id="i-days-invalid",
        name="days-invalid",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
    )
    db_session.add(resource)
    db_session.commit()

    low = client.get(f"/api/v1/costs/by-resource/{resource.id}?days=2")
    assert low.status_code == 422

    high = client.get(f"/api/v1/costs/by-resource/{resource.id}?days=1000")
    assert high.status_code == 422