import json
import os
import tempfile
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditEvent
from app.models.tenant import Tenant
from app.services.audit_storage import reset_storage


@pytest.fixture()
def export_client():
    tmp = tempfile.mkdtemp(prefix="audit-export-test-")
    os.environ["AUDIT_EXPORT_BACKEND"] = "local"
    os.environ["AUDIT_EXPORT_LOCAL_ROOT"] = tmp
    os.environ["AUDIT_EXPORT_RETENTION_DAYS"] = "30"
    os.environ["AUDIT_EXPORT_MAX_RECORDS"] = "1000"
    get_settings.cache_clear()
    reset_storage()

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()

    from app.db.session import set_session_factory

    set_session_factory(SessionLocal)

    def override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override

    original_auth = os.environ.get("AUTH_DISABLED")
    original_demo = os.environ.get("DEMO_MODE")
    os.environ["AUTH_DISABLED"] = "true"
    os.environ["DEMO_MODE"] = "false"
    get_settings.cache_clear()

    with TestClient(app) as c:
        tenant = Tenant(slug="demo", name="Demo")
        db.add(tenant)
        db.commit()
        yield c, db, tenant

    for k, v in (("AUTH_DISABLED", original_auth), ("DEMO_MODE", original_demo)):
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    from app.db.session import set_session_factory

    set_session_factory(None)
    os.environ.pop("AUDIT_EXPORT_LOCAL_ROOT", None)
    os.environ.pop("AUDIT_EXPORT_BACKEND", None)
    get_settings.cache_clear()
    reset_storage()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)


def _seed_events(db, tenant, count=5):
    for i in range(count):
        db.add(
            AuditEvent(
                tenant_id=tenant.id,
                at=datetime.now(UTC),
                category="recommendation",
                severity="info",
                actor="tester",
                action=f"Action {i}",
                subject=f"Subject {i}",
                details="details",
                event_metadata=[{"key": "index", "value": str(i)}],
            )
        )
    db.commit()


def test_create_csv_export(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 3)

    r = client.post("/api/v1/audit/exports", json={"format": "csv"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "completed"
    assert body["format"] == "csv"
    assert body["recordCount"] == 3
    assert body["sizeBytes"] > 0
    assert body["storageBackend"] == "local"
    assert body["downloadUrl"] is not None


def test_create_json_export(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 2)

    r = client.post("/api/v1/audit/exports", json={"format": "json"})
    assert r.status_code == 201
    assert r.json()["status"] == "completed"


def test_list_exports(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 1)

    client.post("/api/v1/audit/exports", json={"format": "csv"})
    client.post("/api/v1/audit/exports", json={"format": "json"})

    r = client.get("/api/v1/audit/exports")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2


def test_get_export_detail(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 1)

    created = client.post("/api/v1/audit/exports", json={"format": "csv"}).json()
    r = client.get(f"/api/v1/audit/exports/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_export_filters_applied(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 3)

    r = client.post(
        "/api/v1/audit/exports",
        json={"format": "csv", "q": "tester"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["filters"]["q"] == "tester"
    assert body["recordCount"] == 3

    r = client.post(
        "/api/v1/audit/exports",
        json={"format": "csv", "q": "no-match-expected"},
    )
    assert r.status_code == 201
    assert r.json()["recordCount"] == 0


def test_download_csv_export(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 2)

    created = client.post("/api/v1/audit/exports", json={"format": "csv"}).json()
    key = created["downloadUrl"].split("key=")[1]
    r = client.get(f"/api/v1/audit/exports/download?key={key}")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert b"tester" in r.content


def test_download_json_export(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 2)

    created = client.post("/api/v1/audit/exports", json={"format": "json"}).json()
    key = created["downloadUrl"].split("key=")[1]
    r = client.get(f"/api/v1/audit/exports/download?key={key}")
    assert r.status_code == 200
    payload = json.loads(r.content)
    assert isinstance(payload, list)
    assert len(payload) == 2


def test_download_other_tenant_key_rejected(export_client):
    import uuid

    client, db, tenant = export_client
    fake_key = f"{uuid.uuid4()}/nonexistent.csv"
    r = client.get(f"/api/v1/audit/exports/download?key={fake_key}")
    assert r.status_code == 404


def test_delete_export(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 1)

    created = client.post("/api/v1/audit/exports", json={"format": "csv"}).json()
    r = client.delete(f"/api/v1/audit/exports/{created['id']}")
    assert r.status_code == 204

    missing = client.get(f"/api/v1/audit/exports/{created['id']}")
    assert missing.status_code == 404


def test_cleanup_expired(export_client):
    from datetime import timedelta

    from app.models.audit_export import AuditExport

    client, db, tenant = export_client
    _seed_events(db, tenant, 1)

    created = client.post("/api/v1/audit/exports", json={"format": "csv"}).json()
    export = db.get(AuditExport, __import__("uuid").UUID(created["id"]))
    export.expires_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    r = client.post("/api/v1/audit/exports/cleanup")
    assert r.status_code == 200
    assert r.json()["removed"] == 1


def test_legacy_export_available_for_local_backend(export_client):
    client, db, tenant = export_client
    _seed_events(db, tenant, 2)

    r = client.get("/api/v1/audit/export?format=csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")


def test_legacy_export_blocked_when_s3(export_client):
    client, db, tenant = export_client
    os.environ["AUDIT_EXPORT_BACKEND"] = "s3"
    get_settings.cache_clear()
    reset_storage()
    try:
        r = client.get("/api/v1/audit/export?format=csv")
        assert r.status_code == 400
    finally:
        os.environ["AUDIT_EXPORT_BACKEND"] = "local"
        get_settings.cache_clear()
        reset_storage()


def test_create_export_unknown_id_404(export_client):
    import uuid

    client, db, tenant = export_client
    r = client.get(f"/api/v1/audit/exports/{uuid.uuid4()}")
    assert r.status_code == 404