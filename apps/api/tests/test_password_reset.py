import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db, set_session_factory
from app.main import app
from app.models.password_reset import PasswordResetToken
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.services.auth import hash_password


@pytest.fixture()
def reset_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()

    set_session_factory(SessionLocal)

    def override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override

    original_auth = os.environ.get("AUTH_DISABLED")
    original_demo = os.environ.get("DEMO_MODE")
    original_smtp = os.environ.get("SMTP_ENABLED")
    original_worker = os.environ.get("WORKER_ENABLED")
    os.environ["AUTH_DISABLED"] = "false"
    os.environ["DEMO_MODE"] = "false"
    os.environ["SMTP_ENABLED"] = "false"
    os.environ["WORKER_ENABLED"] = "false"
    get_settings.cache_clear()

    with TestClient(app) as c:
        yield c, db

    for k, v in (
        ("AUTH_DISABLED", original_auth),
        ("DEMO_MODE", original_demo),
        ("SMTP_ENABLED", original_smtp),
        ("WORKER_ENABLED", original_worker),
    ):
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    set_session_factory(None)
    get_settings.cache_clear()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)


def _make_user(db, email: str, password: str = "supersecret123") -> User:
    tenant = db.query(Tenant).first()
    if tenant is None:
        tenant = Tenant(slug="acme", name="Acme")
        db.add(tenant)
        db.flush()
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name="Test User",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(TeamMember(user_id=user.id, tenant_id=tenant.id, role="owner"))
    db.commit()
    return user


def test_request_returns_url_when_smtp_disabled(reset_client):
    client, db = reset_client
    _make_user(db, "user@acme.io")

    r = client.post("/api/v1/auth/password-reset/request", json={"email": "user@acme.io"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["resetUrl"] is not None
    assert "token=" in body["resetUrl"]


def test_request_unknown_email_still_returns_ok(reset_client):
    client, db = reset_client
    r = client.post("/api/v1/auth/password-reset/request", json={"email": "missing@acme.io"})
    assert r.status_code == 200
    assert r.json()["resetUrl"] is None


def test_request_hides_url_when_smtp_enabled(reset_client):
    client, db = reset_client
    _make_user(db, "user@acme.io")
    os.environ["SMTP_ENABLED"] = "true"
    get_settings.cache_clear()
    try:
        r = client.post("/api/v1/auth/password-reset/request", json={"email": "user@acme.io"})
        assert r.status_code == 200
        assert r.json()["resetUrl"] is None
    finally:
        os.environ["SMTP_ENABLED"] = "false"
        get_settings.cache_clear()


def test_confirm_updates_password(reset_client):
    client, db = reset_client
    _make_user(db, "user@acme.io")

    req = client.post("/api/v1/auth/password-reset/request", json={"email": "user@acme.io"}).json()
    token = req["resetUrl"].split("token=")[1]

    r = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "newpassword123"},
    )
    assert r.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@acme.io", "password": "newpassword123"},
    )
    assert login.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@acme.io", "password": "supersecret123"},
    )
    assert old_login.status_code == 401


def test_confirm_rejects_short_password(reset_client):
    client, db = reset_client
    _make_user(db, "user@acme.io")
    req = client.post("/api/v1/auth/password-reset/request", json={"email": "user@acme.io"}).json()
    token = req["resetUrl"].split("token=")[1]

    r = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "short"},
    )
    assert r.status_code == 422


def test_confirm_rejects_reuse(reset_client):
    client, db = reset_client
    _make_user(db, "user@acme.io")
    req = client.post("/api/v1/auth/password-reset/request", json={"email": "user@acme.io"}).json()
    token = req["resetUrl"].split("token=")[1]

    first = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "newpassword123"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "anotherpass123"},
    )
    assert second.status_code == 400


def test_confirm_rejects_expired(reset_client):
    client, db = reset_client
    user = _make_user(db, "user@acme.io")
    entry = PasswordResetToken(
        user_id=user.id,
        token="expiredtoken-abc123",
        expires_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db.add(entry)
    db.commit()

    r = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "expiredtoken-abc123", "password": "newpassword123"},
    )
    assert r.status_code == 400


def test_request_invalidates_previous_tokens(reset_client):
    client, db = reset_client
    _make_user(db, "user@acme.io")

    first = client.post("/api/v1/auth/password-reset/request", json={"email": "user@acme.io"}).json()
    second = client.post("/api/v1/auth/password-reset/request", json={"email": "user@acme.io"}).json()

    first_token = first["resetUrl"].split("token=")[1]
    second_token = second["resetUrl"].split("token=")[1]
    assert first_token != second_token

    reuse = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": first_token, "password": "newpassword123"},
    )
    assert reuse.status_code == 400

    ok = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": second_token, "password": "newpassword123"},
    )
    assert ok.status_code == 200