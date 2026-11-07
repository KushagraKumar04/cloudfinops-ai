import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def auth_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()

    def override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override

    original_auth = os.environ.get("AUTH_DISABLED")
    original_demo = os.environ.get("DEMO_MODE")
    original_worker = os.environ.get("WORKER_ENABLED")
    os.environ["AUTH_DISABLED"] = "false"
    os.environ["DEMO_MODE"] = "false"
    os.environ["WORKER_ENABLED"] = "false"
    get_settings.cache_clear()

    with TestClient(app) as c:
        yield c

    if original_auth is None:
        os.environ.pop("AUTH_DISABLED", None)
    else:
        os.environ["AUTH_DISABLED"] = original_auth
    if original_demo is None:
        os.environ.pop("DEMO_MODE", None)
    else:
        os.environ["DEMO_MODE"] = original_demo
    if original_worker is None:
        os.environ.pop("WORKER_ENABLED", None)
    else:
        os.environ["WORKER_ENABLED"] = original_worker
    get_settings.cache_clear()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)


def test_register_creates_user_and_tenant(auth_client):
    r = auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@example.com",
            "password": "supersecret123",
            "fullName": "Alice",
            "organizationName": "Alice Cloud",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["accessToken"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["tenant"]["name"] == "Alice Cloud"
    assert body["tenant"]["role"] == "owner"


def test_register_duplicate_email(auth_client):
    payload = {"email": "bob@example.com", "password": "supersecret123"}
    first = auth_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = auth_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_register_rejects_short_password(auth_client):
    r = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "123"},
    )
    assert r.status_code == 422


def test_login_success(auth_client):
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "carol@example.com", "password": "supersecret123"},
    )
    r = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "carol@example.com", "password": "supersecret123"},
    )
    assert r.status_code == 200
    assert r.json()["accessToken"]


def test_login_wrong_password(auth_client):
    auth_client.post(
        "/api/v1/auth/register",
        json={"email": "dave@example.com", "password": "supersecret123"},
    )
    r = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "dave@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401


def test_me_requires_token(auth_client):
    r = auth_client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user(auth_client):
    created = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "eve@example.com", "password": "supersecret123"},
    ).json()
    token = created["accessToken"]
    r = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "eve@example.com"
    assert body["tenant"]["id"] == created["tenant"]["id"]


def test_protected_endpoint_without_token(auth_client):
    r = auth_client.get("/api/v1/resources")
    assert r.status_code == 401


def test_protected_endpoint_with_token(auth_client):
    created = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "frank@example.com", "password": "supersecret123"},
    ).json()
    token = created["accessToken"]
    r = auth_client.get("/api/v1/resources", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_invalid_token_rejected(auth_client):
    r = auth_client.get(
        "/api/v1/resources",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r.status_code == 401


def test_tenant_isolation(auth_client):
    alice = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "alice2@example.com", "password": "supersecret123"},
    ).json()
    bob = auth_client.post(
        "/api/v1/auth/register",
        json={"email": "bob2@example.com", "password": "supersecret123"},
    ).json()

    alice_res = auth_client.get(
        "/api/v1/resources",
        headers={"Authorization": f"Bearer {alice['accessToken']}"},
    ).json()
    bob_res = auth_client.get(
        "/api/v1/resources",
        headers={"Authorization": f"Bearer {bob['accessToken']}"},
    ).json()

    assert alice_res["total"] == 0
    assert bob_res["total"] == 0
    assert alice["tenant"]["id"] != bob["tenant"]["id"]