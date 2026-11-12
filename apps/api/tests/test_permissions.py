import uuid
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
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.services.auth import hash_password


@pytest.fixture()
def permission_client():
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

    set_session_factory(lambda: db)

    def override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override

    original_auth = __import__("os").environ.get("AUTH_DISABLED")
    original_demo = __import__("os").environ.get("DEMO_MODE")
    __import__("os").environ["AUTH_DISABLED"] = "false"
    __import__("os").environ["DEMO_MODE"] = "false"
    __import__("os").environ["WORKER_ENABLED"] = "false"
    get_settings.cache_clear()

    with TestClient(app) as c:
        yield c, db

    if original_auth is None:
        __import__("os").environ.pop("AUTH_DISABLED", None)
    else:
        __import__("os").environ["AUTH_DISABLED"] = original_auth
    if original_demo is None:
        __import__("os").environ.pop("DEMO_MODE", None)
    else:
        __import__("os").environ["DEMO_MODE"] = original_demo
    from app.db.session import set_session_factory

    set_session_factory(None)
    from app.db.session import set_session_factory

    set_session_factory(None)
    get_settings.cache_clear()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)


def _make_tenant(db, slug: str) -> Tenant:
    t = Tenant(slug=slug, name=slug.title())
    db.add(t)
    db.flush()
    return t


def _make_user(db, tenant: Tenant, email: str, password: str, role: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=email.split("@")[0],
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(TeamMember(user_id=user.id, tenant_id=tenant.id, role=role))
    db.commit()
    return user


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["accessToken"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_me_returns_permissions(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "owner@acme.io", "supersecret123", "owner")
    token = _login(client, "owner@acme.io", "supersecret123")

    r = client.get("/api/v1/auth/me", headers=_auth_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert "permissions" in body
    assert "manage_team" in body["permissions"]
    assert body["tenant"]["role"] == "owner"


def test_viewer_can_read(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "viewer@acme.io", "supersecret123", "viewer")
    token = _login(client, "viewer@acme.io", "supersecret123")

    r = client.get("/api/v1/resources", headers=_auth_headers(token))
    assert r.status_code == 200


def test_viewer_cannot_approve_recommendation(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "viewer@acme.io", "supersecret123", "viewer")
    token = _login(client, "viewer@acme.io", "supersecret123")

    fake_id = uuid.uuid4()
    r = client.post(
        f"/api/v1/recommendations/{fake_id}/approve",
        json={},
        headers=_auth_headers(token),
    )
    assert r.status_code == 403
    assert "approve_recommendation" in r.text


def test_viewer_cannot_execute(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "viewer@acme.io", "supersecret123", "viewer")
    token = _login(client, "viewer@acme.io", "supersecret123")

    r = client.post(
        "/api/v1/executions",
        json={"recommendationId": str(uuid.uuid4()), "mode": "dry_run"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 403


def test_viewer_cannot_connect_cloud_account(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "viewer@acme.io", "supersecret123", "viewer")
    token = _login(client, "viewer@acme.io", "supersecret123")

    r = client.post(
        "/api/v1/cloud/accounts/aws",
        json={
            "name": "AWS",
            "accountIdentifier": "123456789012",
            "roleArn": "arn:aws:iam::123456789012:role/x",
            "environment": "production",
            "regions": ["us-east-1"],
        },
        headers=_auth_headers(token),
    )
    assert r.status_code == 403


def test_viewer_cannot_edit_settings(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "viewer@acme.io", "supersecret123", "viewer")
    token = _login(client, "viewer@acme.io", "supersecret123")

    r = client.put(
        "/api/v1/settings/policies",
        json={"policies": []},
        headers=_auth_headers(token),
    )
    assert r.status_code == 403


def test_member_can_approve_but_not_execute(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "member@acme.io", "supersecret123", "member")
    token = _login(client, "member@acme.io", "supersecret123")

    approve = client.post(
        f"/api/v1/recommendations/{uuid.uuid4()}/approve",
        json={},
        headers=_auth_headers(token),
    )
    assert approve.status_code in {404, 409}

    execute = client.post(
        "/api/v1/executions",
        json={"recommendationId": str(uuid.uuid4()), "mode": "dry_run"},
        headers=_auth_headers(token),
    )
    assert execute.status_code == 403


def test_member_cannot_edit_settings(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "member@acme.io", "supersecret123", "member")
    token = _login(client, "member@acme.io", "supersecret123")

    r = client.put(
        "/api/v1/settings/policies",
        json={"policies": []},
        headers=_auth_headers(token),
    )
    assert r.status_code == 403


def test_admin_can_edit_settings(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "admin@acme.io", "supersecret123", "admin")
    token = _login(client, "admin@acme.io", "supersecret123")

    r = client.put(
        "/api/v1/settings/policies",
        json={"policies": []},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200


def test_admin_cannot_manage_team(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "admin@acme.io", "supersecret123", "admin")
    token = _login(client, "admin@acme.io", "supersecret123")

    r = client.patch(
        f"/api/v1/team/{uuid.uuid4()}",
        json={"role": "member"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 403


def test_owner_can_change_member_role(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    owner = _make_user(db, tenant, "owner@acme.io", "supersecret123", "owner")
    member_user = _make_user(db, tenant, "member@acme.io", "supersecret123", "member")
    token = _login(client, "owner@acme.io", "supersecret123")

    target_member = db.query(TeamMember).filter(TeamMember.user_id == member_user.id).first()
    assert target_member is not None

    r = client.patch(
        f"/api/v1/team/{target_member.id}",
        json={"role": "admin"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_cannot_demote_last_owner(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    owner = _make_user(db, tenant, "owner@acme.io", "supersecret123", "owner")
    token = _login(client, "owner@acme.io", "supersecret123")

    owner_member = db.query(TeamMember).filter(TeamMember.user_id == owner.id).first()
    r = client.patch(
        f"/api/v1/team/{owner_member.id}",
        json={"role": "member"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 409


def test_list_team_members(permission_client):
    client, db = permission_client
    tenant = _make_tenant(db, "acme")
    _make_user(db, tenant, "owner@acme.io", "supersecret123", "owner")
    _make_user(db, tenant, "member@acme.io", "supersecret123", "member")
    token = _login(client, "owner@acme.io", "supersecret123")

    r = client.get("/api/v1/team", headers=_auth_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["currentRole"] == "owner"