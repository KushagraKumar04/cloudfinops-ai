import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.invitation import Invitation
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.services.auth import hash_password


@pytest.fixture()
def invite_client():
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

    original_auth = __import__("os").environ.get("AUTH_DISABLED")
    original_demo = __import__("os").environ.get("DEMO_MODE")
    original_smtp = __import__("os").environ.get("SMTP_ENABLED")
    __import__("os").environ["AUTH_DISABLED"] = "false"
    __import__("os").environ["DEMO_MODE"] = "false"
    __import__("os").environ["SMTP_ENABLED"] = "false"
    __import__("os").environ["WORKER_ENABLED"] = "false"
    get_settings.cache_clear()

    with TestClient(app) as c:
        yield c, db

    for k, v in (
        ("AUTH_DISABLED", original_auth),
        ("DEMO_MODE", original_demo),
        ("SMTP_ENABLED", original_smtp),
    ):
        if v is None:
            __import__("os").environ.pop(k, None)
        else:
            __import__("os").environ[k] = v
    from app.db.session import set_session_factory

    set_session_factory(None)
    get_settings.cache_clear()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)


def _make_owner(db, slug: str = "acme") -> tuple[Tenant, User]:
    tenant = Tenant(slug=slug, name=slug.title())
    db.add(tenant)
    db.flush()
    user = User(
        email=f"owner@{slug}.io",
        password_hash=hash_password("supersecret123"),
        full_name="Owner",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(TeamMember(user_id=user.id, tenant_id=tenant.id, role="owner"))
    db.commit()
    return tenant, user


def _login(client, email: str, password: str = "supersecret123") -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["accessToken"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_invitation(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    r = client.post(
        "/api/v1/team/invitations",
        json={"email": "newuser@example.com", "role": "member"},
        headers=_h(token),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "newuser@example.com"
    assert body["role"] == "member"
    assert body["status"] == "pending"
    assert body["inviteUrl"] is not None


def test_invite_duplicate_returns_409(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)
    payload = {"email": "dup@example.com", "role": "member"}
    first = client.post("/api/v1/team/invitations", json=payload, headers=_h(token))
    assert first.status_code == 201
    second = client.post("/api/v1/team/invitations", json=payload, headers=_h(token))
    assert second.status_code == 409


def test_invite_existing_member_returns_409(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    r = client.post(
        "/api/v1/team/invitations",
        json={"email": owner.email, "role": "member"},
        headers=_h(token),
    )
    assert r.status_code == 409


def test_non_owner_cannot_invite(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    member = User(
        email="member@acme.io",
        password_hash=hash_password("supersecret123"),
        full_name="Member",
        is_active=True,
    )
    db.add(member)
    db.flush()
    db.add(TeamMember(user_id=member.id, tenant_id=tenant.id, role="member"))
    db.commit()

    token = _login(client, member.email)
    r = client.post(
        "/api/v1/team/invitations",
        json={"email": "someone@example.com", "role": "member"},
        headers=_h(token),
    )
    assert r.status_code == 403


def test_list_invitations(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    client.post(
        "/api/v1/team/invitations",
        json={"email": "one@example.com", "role": "member"},
        headers=_h(token),
    )
    client.post(
        "/api/v1/team/invitations",
        json={"email": "two@example.com", "role": "admin"},
        headers=_h(token),
    )

    r = client.get("/api/v1/team/invitations", headers=_h(token))
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_revoke_invitation(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    created = client.post(
        "/api/v1/team/invitations",
        json={"email": "revoke@example.com", "role": "member"},
        headers=_h(token),
    ).json()

    r = client.delete(f"/api/v1/team/invitations/{created['id']}", headers=_h(token))
    assert r.status_code == 204


def test_preview_invitation(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    created = client.post(
        "/api/v1/team/invitations",
        json={"email": "preview@example.com", "role": "member"},
        headers=_h(token),
    ).json()

    invite_token = created["inviteUrl"].split("token=")[1]
    r = client.get(f"/api/v1/auth/invitations/{invite_token}")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "preview@example.com"
    assert body["tenantName"] == "Acme"


def test_accept_invitation_creates_user(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    created = client.post(
        "/api/v1/team/invitations",
        json={"email": "accept@example.com", "role": "admin"},
        headers=_h(token),
    ).json()
    invite_token = created["inviteUrl"].split("token=")[1]

    r = client.post(
        f"/api/v1/auth/invitations/{invite_token}/accept",
        json={"password": "supersecret456", "fullName": "New Admin"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant"]["role"] == "admin"
    assert body["user"]["email"] == "accept@example.com"

    user = db.query(User).filter(User.email == "accept@example.com").first()
    assert user is not None


def test_accept_short_password_rejected(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    created = client.post(
        "/api/v1/team/invitations",
        json={"email": "short@example.com", "role": "member"},
        headers=_h(token),
    ).json()
    invite_token = created["inviteUrl"].split("token=")[1]

    r = client.post(
        f"/api/v1/auth/invitations/{invite_token}/accept",
        json={"password": "123"},
    )
    assert r.status_code == 400


def test_accept_expired_invitation(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    created = client.post(
        "/api/v1/team/invitations",
        json={"email": "expired@example.com", "role": "member"},
        headers=_h(token),
    ).json()

    invitation = db.get(Invitation, uuid.UUID(created["id"]))
    invitation.expires_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    invite_token = created["inviteUrl"].split("token=")[1]
    r = client.post(
        f"/api/v1/auth/invitations/{invite_token}/accept",
        json={"password": "supersecret789"},
    )
    assert r.status_code == 400


def test_invite_url_hidden_when_smtp_enabled(invite_client):
    client, db = invite_client
    tenant, owner = _make_owner(db)
    token = _login(client, owner.email)

    __import__("os").environ["SMTP_ENABLED"] = "true"
    get_settings.cache_clear()
    try:
        r = client.post(
            "/api/v1/team/invitations",
            json={"email": "hidden@example.com", "role": "member"},
            headers=_h(token),
        )
        assert r.status_code == 201
        assert r.json()["inviteUrl"] is None
    finally:
        __import__("os").environ["SMTP_ENABLED"] = "false"
        get_settings.cache_clear()