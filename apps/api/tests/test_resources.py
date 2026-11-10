import uuid
from decimal import Decimal

from app.models.resource import Resource


def _seed_resources(db_session, tenant, account_id):
    rows = [
        ("i-001", "api-01", "EC2", "us-east-1", "production", "running", "100"),
        ("i-002", "api-02", "EC2", "us-east-1", "production", "running", "200"),
        ("i-003", "worker-01", "EC2", "us-west-2", "staging", "running", "50"),
        ("vol-001", "orphan", "EBS", "us-east-1", "production", "unattached", "60"),
    ]
    for cloud_id, name, service, region, env, status, cost in rows:
        db_session.add(
            Resource(
                tenant_id=tenant.id,
                cloud_account_id=account_id,
                provider="AWS",
                cloud_id=cloud_id,
                name=name,
                type="EC2 m5.large" if service == "EC2" else "EBS gp3",
                service=service,
                region=region,
                environment=env,
                status=status,
                application="test",
                owner="tester",
                tags=[],
                utilization={},
                series={},
                metric_coverage=Decimal("0.9"),
                monthly_cost=Decimal(cost),
            )
        )
    db_session.commit()


def test_list_resources_empty(client, seeded_tenant):
    r = client.get("/api/v1/resources")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_list_resources_with_data(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_resources(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/resources")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4
    assert body["aggregates"]["totalMonthlyCost"] == 410.0
    assert body["aggregates"]["byProvider"]["AWS"]["count"] == 4
    assert body["aggregates"]["byEnvironment"]["production"]["count"] == 3


def test_list_resources_filters(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_resources(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/resources", params={"service": "EC2"})
    assert r.status_code == 200
    assert r.json()["total"] == 3

    r = client.get("/api/v1/resources", params={"environment": "staging"})
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.get("/api/v1/resources", params={"status": "unattached"})
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_list_resources_search(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_resources(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/resources", params={"q": "api"})
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_list_resources_pagination(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_resources(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/resources", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2


def test_get_resource(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_resources(db_session, seeded_tenant, account.id)

    resource = db_session.execute(select(Resource).where(Resource.cloud_id == "i-001")).scalar_one()
    r = client.get(f"/api/v1/resources/{resource.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "api-01"
    assert body["accountName"] == "AWS Production"


def test_get_resource_not_found(client, seeded_tenant):
    r = client.get(f"/api/v1/resources/{uuid.uuid4()}")
    assert r.status_code == 404