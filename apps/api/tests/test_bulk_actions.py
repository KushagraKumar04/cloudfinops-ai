import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.cloud_account import CloudAccount
from app.models.recommendation import Recommendation
from app.models.resource import Resource


def _make_recommendation(db, tenant, account_id, status="pending", risk="MEDIUM"):
    resource = Resource(
        tenant_id=tenant.id,
        cloud_account_id=account_id,
        provider="AWS",
        cloud_id=f"i-bulk-{uuid.uuid4().hex[:8]}",
        name=f"bulk-{uuid.uuid4().hex[:6]}",
        type="EC2 m5.large",
        service="EC2",
        region="us-east-1",
        environment="production",
        status="running",
        metric_coverage=Decimal("0.95"),
        monthly_cost=Decimal("100"),
    )
    db.add(resource)
    db.flush()

    rec = Recommendation(
        tenant_id=tenant.id,
        resource_id=resource.id,
        type="compute.rightsizing",
        type_label="Compute rightsizing",
        title="Bulk test recommendation",
        summary="s",
        status=status,
        risk=risk,
        risk_reasons=[],
        confidence=Decimal("0.9"),
        current_monthly_cost=Decimal("100"),
        estimated_monthly_cost=Decimal("50"),
        estimated_monthly_savings=Decimal("50"),
        calculation_basis=[],
        current_state=[],
        proposed_state=[],
        impact={},
        implementation_plan=[],
    )
    db.add(rec)
    db.commit()
    return rec


def test_bulk_approve(client, seeded_tenant, db_session):
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    recs = [_make_recommendation(db_session, seeded_tenant, account.id) for _ in range(3)]

    r = client.post(
        "/api/v1/recommendations/bulk-decide",
        json={"ids": [str(r.id) for r in recs], "action": "approve"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["succeededCount"] == 3
    assert body["failedCount"] == 0

    for rec in recs:
        db_session.refresh(rec)
        assert rec.status == "approved"


def test_bulk_reject_requires_reason(client, seeded_tenant, db_session):
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _make_recommendation(db_session, seeded_tenant, account.id)

    r = client.post(
        "/api/v1/recommendations/bulk-decide",
        json={"ids": [str(rec.id)], "action": "reject", "reason": ""},
    )
    assert r.status_code == 422


def test_bulk_reject_with_reason(client, seeded_tenant, db_session):
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    rec = _make_recommendation(db_session, seeded_tenant, account.id)

    r = client.post(
        "/api/v1/recommendations/bulk-decide",
        json={"ids": [str(rec.id)], "action": "reject", "reason": "not needed"},
    )
    assert r.status_code == 200
    assert r.json()["succeededCount"] == 1


def test_bulk_partial_failure(client, seeded_tenant, db_session):
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    ok = _make_recommendation(db_session, seeded_tenant, account.id, status="pending")
    already = _make_recommendation(db_session, seeded_tenant, account.id, status="approved")
    blocked = _make_recommendation(db_session, seeded_tenant, account.id, risk="BLOCKED")
    missing = uuid.uuid4()

    r = client.post(
        "/api/v1/recommendations/bulk-decide",
        json={"ids": [str(ok.id), str(already.id), str(blocked.id), str(missing)], "action": "approve"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["succeededCount"] == 1
    assert body["failedCount"] == 3
    errors = {f["id"]: f["error"] for f in body["failed"]}
    assert errors[str(already.id)] == "Status is approved"
    assert errors[str(blocked.id)] == "Blocked by policy"
    assert errors[str(missing)] == "Not found"


def test_bulk_disable_accounts(client, seeded_tenant, db_session):
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    r = client.post(
        "/api/v1/cloud/accounts/bulk-disable",
        json={"ids": [str(account.id)]},
    )
    assert r.status_code == 200
    assert r.json()["succeededCount"] == 1

    db_session.refresh(account)
    assert account.disabled_at is not None
    assert account.status == "disabled"


def test_bulk_enable_accounts(client, seeded_tenant, db_session):
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    account.disabled_at = datetime.now(UTC)
    account.status = "disabled"
    db_session.commit()

    r = client.post(
        "/api/v1/cloud/accounts/bulk-enable",
        json={"ids": [str(account.id)]},
    )
    assert r.status_code == 200
    assert r.json()["succeededCount"] == 1

    db_session.refresh(account)
    assert account.disabled_at is None


def test_bulk_disable_idempotent_conflict(client, seeded_tenant, db_session):
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    account.disabled_at = datetime.now(UTC)
    db_session.commit()

    r = client.post(
        "/api/v1/cloud/accounts/bulk-disable",
        json={"ids": [str(account.id)]},
    )
    assert r.status_code == 200
    assert r.json()["failedCount"] == 1


def test_sync_disabled_account_rejected(client, seeded_tenant, db_session):
    from sqlalchemy import select

    account = db_session.execute(select(CloudAccount)).scalars().first()
    account.disabled_at = datetime.now(UTC)
    db_session.commit()

    r = client.post(f"/api/v1/cloud/accounts/{account.id}/sync")
    assert r.status_code == 409
    assert "disabled" in r.text.lower()


def test_audit_export_csv(client, seeded_tenant, db_session):
    from app.models.audit import AuditEvent

    db_session.add(
        AuditEvent(
            tenant_id=seeded_tenant.id,
            at=datetime.now(UTC),
            category="recommendation",
            severity="info",
            actor="tester",
            action="Tested",
            subject="subject, with comma",
            details="details",
            event_metadata=[{"key": "k", "value": "v"}],
        )
    )
    db_session.commit()

    r = client.get("/api/v1/audit/export?format=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    body = r.text
    assert "actor" in body
    assert "tester" in body
    assert '"subject, with comma"' in body


def test_audit_export_json(client, seeded_tenant, db_session):
    from app.models.audit import AuditEvent

    db_session.add(
        AuditEvent(
            tenant_id=seeded_tenant.id,
            at=datetime.now(UTC),
            category="recommendation",
            severity="info",
            actor="tester",
            action="Tested",
            subject="subject",
            details="details",
            event_metadata=[],
        )
    )
    db_session.commit()

    r = client.get("/api/v1/audit/export?format=json")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    import json as _json

    payload = _json.loads(r.text)
    assert isinstance(payload, list)
    assert any(e["actor"] == "tester" for e in payload)


def test_audit_export_invalid_format(client, seeded_tenant):
    r = client.get("/api/v1/audit/export?format=xml")
    assert r.status_code == 422