from datetime import UTC, datetime

from app.models.audit import AuditEvent


def test_list_audit_empty(client, seeded_tenant):
    r = client.get("/api/v1/audit")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_list_audit_with_filters(client, seeded_tenant, db_session):
    db_session.add_all(
        [
            AuditEvent(
                tenant_id=seeded_tenant.id,
                at=datetime.now(UTC),
                category="recommendation",
                severity="info",
                actor="tester",
                action="Tested",
                subject="test",
                details="details",
                event_metadata=[],
            ),
            AuditEvent(
                tenant_id=seeded_tenant.id,
                at=datetime.now(UTC),
                category="auth",
                severity="critical",
                actor="unknown",
                action="Failed login",
                subject="admin",
                details="details",
                event_metadata=[],
            ),
        ]
    )
    db_session.commit()

    r = client.get("/api/v1/audit")
    assert r.json()["total"] == 2

    r = client.get("/api/v1/audit", params={"severity": "critical"})
    assert r.json()["total"] == 1

    r = client.get("/api/v1/audit", params={"category": "recommendation"})
    assert r.json()["total"] == 1

    r = client.get("/api/v1/audit", params={"q": "login"})
    assert r.json()["total"] == 1