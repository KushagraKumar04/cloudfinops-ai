import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.recommendation import Recommendation
from app.models.resource import Resource


def _seed_recommendation(db_session, tenant, account_id, status="approved"):
    resource = Resource(
        tenant_id=tenant.id,
        cloud_account_id=account_id,
        provider="AWS",
        cloud_id="i-exec-test",
        name="exec-test",
        type="EC2 m5.4xlarge",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
        metric_coverage=Decimal("0.95"),
        monthly_cost=Decimal("580"),
    )
    db_session.add(resource)
    db_session.flush()

    rec = Recommendation(
        tenant_id=tenant.id,
        resource_id=resource.id,
        type="compute.rightsizing",
        type_label="Compute rightsizing",
        title="Rightsize exec-test",
        summary="Downsize",
        status=status,
        risk="MEDIUM",
        risk_reasons=[],
        confidence=Decimal("0.9"),
        current_monthly_cost=Decimal("580"),
        estimated_monthly_cost=Decimal("290"),
        estimated_monthly_savings=Decimal("290"),
        calculation_basis=["basis"],
        current_state=[{"key": "Instance type", "value": "m5.4xlarge"}],
        proposed_state=[{"key": "Instance type", "value": "m5.2xlarge"}],
        impact={},
        implementation_plan=["step"],
    )
    db_session.add(rec)
    db_session.flush()
    return rec, resource


def test_create_dry_run(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, _ = _seed_recommendation(db_session, seeded_tenant, account.id)

    r = client.post("/api/v1/executions", json={"recommendationId": str(rec.id), "mode": "dry_run"})
    assert r.status_code == 201
    body = r.json()
    assert body["mode"] == "dry_run"
    assert body["status"] == "completed"
    assert body["dryRunResult"]["ok"] is True
    assert body["idempotencyKey"].startswith("execution:")


def test_create_apply(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, _ = _seed_recommendation(db_session, seeded_tenant, account.id)

    r = client.post("/api/v1/executions", json={"recommendationId": str(rec.id), "mode": "apply"})
    assert r.status_code == 201
    body = r.json()
    assert body["mode"] == "apply"
    assert body["status"] in {"completed", "blocked"}
    assert body["policyResult"]["action"] == "resize_instance"


def test_unapproved_apply_returns_blocked(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, _ = _seed_recommendation(db_session, seeded_tenant, account.id, status="pending")

    r = client.post("/api/v1/executions", json={"recommendationId": str(rec.id), "mode": "apply"})
    assert r.status_code == 201
    assert r.json()["status"] == "blocked"


def test_unapproved_dry_run_allowed(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, _ = _seed_recommendation(db_session, seeded_tenant, account.id, status="pending")

    r = client.post("/api/v1/executions", json={"recommendationId": str(rec.id), "mode": "dry_run"})
    assert r.status_code == 201
    assert r.json()["status"] == "completed"


def test_idempotent_apply_rejected(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, _ = _seed_recommendation(db_session, seeded_tenant, account.id)

    first = client.post("/api/v1/executions", json={"recommendationId": str(rec.id), "mode": "apply"})
    assert first.status_code == 201

    if first.json()["status"] == "completed":
        second = client.post("/api/v1/executions", json={"recommendationId": str(rec.id), "mode": "apply"})
        assert second.status_code == 409


def test_list_executions(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, _ = _seed_recommendation(db_session, seeded_tenant, account.id)

    client.post("/api/v1/executions", json={"recommendationId": str(rec.id), "mode": "dry_run"})

    r = client.get(f"/api/v1/executions?recommendation_id={rec.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert body["items"][0]["action"] == "resize_instance"


def test_get_execution_detail(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec, _ = _seed_recommendation(db_session, seeded_tenant, account.id)

    created = client.post("/api/v1/executions", json={"recommendationId": str(rec.id), "mode": "dry_run"}).json()
    r = client.get(f"/api/v1/executions/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_unknown_execution_404(client, seeded_tenant):
    r = client.get(f"/api/v1/executions/{uuid.uuid4()}")
    assert r.status_code == 404