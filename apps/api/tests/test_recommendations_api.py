import uuid

from app.models.resource import Resource
from app.models.recommendation import Recommendation


def _seed_one(db_session, tenant, account_id) -> Recommendation:
    resource = Resource(
        tenant_id=tenant.id,
        cloud_account_id=account_id,
        provider="AWS",
        cloud_id="i-rec",
        name="rec-test",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
    )
    db_session.add(resource)
    db_session.flush()

    rec = Recommendation(
        tenant_id=tenant.id,
        resource_id=resource.id,
        type="compute.rightsizing",
        type_label="Compute rightsizing",
        title="Rightsize rec-test",
        summary="summary",
        status="pending",
        risk="MEDIUM",
        risk_reasons=["Test reason"],
        confidence=0.9,
        current_monthly_cost=100,
        estimated_monthly_cost=50,
        estimated_monthly_savings=50,
        calculation_basis=["basis"],
        current_state=[{"key": "a", "value": "1"}],
        proposed_state=[{"key": "a", "value": "2"}],
        impact={"availability": "none", "security": "none", "operational": "none"},
        implementation_plan=["step 1"],
    )
    db_session.add(rec)
    db_session.commit()
    return rec


def test_list_recommendations_empty(client, seeded_tenant):
    r = client.get("/api/v1/recommendations")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["totals"]["pending"] == 0


def test_list_recommendations(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    _seed_one(db_session, seeded_tenant, account.id)

    r = client.get("/api/v1/recommendations")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Rightsize rec-test"
    assert body["totals"]["pending"] == 1
    assert body["totals"]["savingsPending"] == 50.0


def test_get_recommendation_detail(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_one(db_session, seeded_tenant, account.id)

    r = client.get(f"/api/v1/recommendations/{rec.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(rec.id)
    assert body["resourceName"] == "rec-test"
    assert body["accountName"] == "AWS Production"
    assert len(body["history"]) == 1
    assert body["history"][0]["action"] == "Recommendation created"


def test_approve_recommendation(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_one(db_session, seeded_tenant, account.id)

    r = client.post(f"/api/v1/recommendations/{rec.id}/approve", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "approved"
    assert any(h["action"] == "Approved" for h in body["history"])


def test_reject_requires_reason(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_one(db_session, seeded_tenant, account.id)

    r = client.post(f"/api/v1/recommendations/{rec.id}/reject", json={"reason": ""})
    assert r.status_code == 422


def test_reject_with_reason(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_one(db_session, seeded_tenant, account.id)

    r = client.post(f"/api/v1/recommendations/{rec.id}/reject", json={"reason": "not needed"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_decide_non_pending_fails(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_one(db_session, seeded_tenant, account.id)

    client.post(f"/api/v1/recommendations/{rec.id}/approve", json={})
    r = client.post(f"/api/v1/recommendations/{rec.id}/approve", json={})
    assert r.status_code == 409


def test_blocked_recommendation_cannot_be_approved(client, seeded_tenant, db_session):
    from app.models.cloud_account import CloudAccount
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _seed_one(db_session, seeded_tenant, account.id)
    rec.risk = "BLOCKED"
    db_session.commit()

    r = client.post(f"/api/v1/recommendations/{rec.id}/approve", json={})
    assert r.status_code == 409