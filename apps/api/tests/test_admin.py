import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db, set_session_factory
from app.main import app
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.services.auth import hash_password


@pytest.fixture()
def admin_client():
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

    original_auth = __import__("os").environ.get("AUTH_DISABLED")
    original_demo = __import__("os").environ.get("DEMO_MODE")
    __import__("os").environ["AUTH_DISABLED"] = "false"
    __import__("os").environ["DEMO_MODE"] = "false"
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
    set_session_factory(None)
    get_settings.cache_clear()
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(engine)


def _make_user(db, tenant: Tenant, email: str, role: str, superuser: bool = False) -> User:
    user = User(
        email=email,
        password_hash=hash_password("supersecret123"),
        full_name=email.split("@")[0],
        is_active=True,
        is_superuser=superuser,
    )
    db.add(user)
    db.flush()
    db.add(TeamMember(user_id=user.id, tenant_id=tenant.id, role=role))
    db.commit()
    return user


def _login(client: TestClient, email: str) -> str:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "supersecret123"},
    )
    assert r.status_code == 200, r.text
    return r.json()["accessToken"]


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_requires_superuser(admin_client):
    client, db = admin_client
    t = Tenant(slug="acme", name="Acme")
    db.add(t)
    db.flush()
    _make_user(db, t, "member@acme.io", "member")
    token = _login(client, "member@acme.io")

    r = client.get("/api/v1/admin/stats", headers=_h(token))
    assert r.status_code == 403


def test_admin_stats(admin_client):
    client, db = admin_client
    t = Tenant(slug="acme", name="Acme")
    db.add(t)
    db.flush()
    _make_user(db, t, "root@acme.io", "owner", superuser=True)
    token = _login(client, "root@acme.io")

    r = client.get("/api/v1/admin/stats", headers=_h(token))
    assert r.status_code == 200
    body = r.json()
    assert body["tenantCount"] == 1
    assert body["userCount"] == 1
    assert "accounts_by_provider" in body["breakdown"]


def test_admin_lists_tenants(admin_client):
    client, db = admin_client
    for slug in ("one", "two", "three"):
        db.add(Tenant(slug=slug, name=slug.title()))
    db.flush()
    first = db.query(Tenant).first()
    _make_user(db, first, "root@one.io", "owner", superuser=True)
    token = _login(client, "root@one.io")

    r = client.get("/api/v1/admin/tenants", headers=_h(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert all("userCount" in t for t in body["items"])


def test_admin_tenant_detail(admin_client):
    client, db = admin_client
    t = Tenant(slug="acme", name="Acme")
    db.add(t)
    db.flush()
    _make_user(db, t, "root@acme.io", "owner", superuser=True)

    r = client.get(f"/api/v1/admin/tenants/{t.id}", headers=_h(token := _login(client, "root@acme.io")))
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "acme"
    assert len(body["members"]) == 1
    assert body["members"][0]["email"] == "root@acme.io"


def test_admin_lists_users(admin_client):
    client, db = admin_client
    t = Tenant(slug="acme", name="Acme")
    db.add(t)
    db.flush()
    _make_user(db, t, "root@acme.io", "owner", superuser=True)
    _make_user(db, t, "alice@acme.io", "member")
    token = _login(client, "root@acme.io")

    r = client.get("/api/v1/admin/users", headers=_h(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    emails = {u["email"] for u in body["items"]}
    assert emails == {"root@acme.io", "alice@acme.io"}


def test_admin_can_disable_user(admin_client):
    client, db = admin_client
    t = Tenant(slug="acme", name="Acme")
    db.add(t)
    db.flush()
    _make_user(db, t, "root@acme.io", "owner", superuser=True)
    alice = _make_user(db, t, "alice@acme.io", "member")
    token = _login(client, "root@acme.io")

    r = client.patch(
        f"/api/v1/admin/users/{alice.id}",
        json={"isActive": False},
        headers=_h(token),
    )
    assert r.status_code == 200
    assert r.json()["isActive"] is False

    r2 = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@acme.io", "password": "supersecret123"},
    )
    assert r2.status_code == 403


def test_admin_cannot_disable_self(admin_client):
    client, db = admin_client
    t = Tenant(slug="acme", name="Acme")
    db.add(t)
    db.flush()
    root = _make_user(db, t, "root@acme.io", "owner", superuser=True)
    token = _login(client, "root@acme.io")

    r = client.patch(
        f"/api/v1/admin/users/{root.id}",
        json={"isActive": False},
        headers=_h(token),
    )
    assert r.status_code == 409


def test_admin_can_promote_user(admin_client):
    client, db = admin_client
    t = Tenant(slug="acme", name="Acme")
    db.add(t)
    db.flush()
    _make_user(db, t, "root@acme.io", "owner", superuser=True)
    alice = _make_user(db, t, "alice@acme.io", "member")
    token = _login(client, "root@acme.io")

    r = client.patch(
        f"/api/v1/admin/users/{alice.id}",
        json={"isSuperuser": True},
        headers=_h(token),
    )
    assert r.status_code == 200
    assert r.json()["isSuperuser"] is True


def test_admin_tenant_404(admin_client):
    import uuid

    client, db = admin_client
    t = Tenant(slug="acme", name="Acme")
    db.add(t)
    db.flush()
    _make_user(db, t, "root@acme.io", "owner", superuser=True)
    token = _login(client, "root@acme.io")

    r = client.get(f"/api/v1/admin/tenants/{uuid.uuid4()}", headers=_h(token))
    assert r.status_code == 404