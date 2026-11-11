from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.oauth import (
    OAuthUserInfo,
    PROVIDER_CONFIG,
    STATE_STORE,
    _fetch_user_info,
    _exchange_code,
    resolve_oauth_user,
)


class _FakeResponse:
    def __init__(self, status_code: int, body: dict) -> None:
        self.status_code = status_code
        self._body = body
        self.text = str(body)

    def json(self) -> dict:
        return self._body


@pytest.fixture()
def oauth_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_providers_list_disabled_when_no_config():
    with TestClient(app) as client:
        r = client.get("/api/v1/auth/oauth/providers")
        assert r.status_code == 200
        providers = r.json()
        ids = {p["id"] for p in providers}
        assert ids == {"github", "google"}
        for p in providers:
            assert p["enabled"] is False


def test_authorize_unknown_provider():
    with TestClient(app) as client:
        r = client.get("/api/v1/auth/oauth/unknown/authorize")
        assert r.status_code == 400


def test_authorize_without_client_id():
    with TestClient(app) as client:
        r = client.get("/api/v1/auth/oauth/github/authorize", follow_redirects=False)
        assert r.status_code == 400


def test_callback_invalid_state_redirects_with_error():
    with TestClient(app) as client:
        r = client.get(
            "/api/v1/auth/oauth/github/callback",
            params={"code": "abc", "state": "not-real"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


def test_exchange_code_returns_token(monkeypatch):
    def fake_post(self, url, data=None, headers=None, json=None):
        assert url == PROVIDER_CONFIG["github"]["token_url"]
        return _FakeResponse(200, {"access_token": "gho_test", "token_type": "bearer"})

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    __import__("os").environ["GITHUB_CLIENT_ID"] = "id"
    __import__("os").environ["GITHUB_CLIENT_SECRET"] = "secret"
    get_settings.cache_clear()
    try:
        token = _exchange_code("github", "code")
        assert token == "gho_test"
    finally:
        __import__("os").environ.pop("GITHUB_CLIENT_ID", None)
        __import__("os").environ.pop("GITHUB_CLIENT_SECRET", None)
        get_settings.cache_clear()


def test_fetch_user_info_github_uses_primary_email(monkeypatch):
    responses = iter(
        [
            _FakeResponse(200, {"id": 12345, "login": "octocat", "name": "Octo Cat", "email": None}),
            _FakeResponse(
                200,
                [
                    {"email": "second@example.com", "primary": False, "verified": True},
                    {"email": "primary@example.com", "primary": True, "verified": True},
                ],
            ),
        ]
    )

    def fake_get(self, url, headers=None):
        return next(responses)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    info = _fetch_user_info("github", "token")
    assert info.provider == "github"
    assert info.provider_user_id == "12345"
    assert info.email == "primary@example.com"
    assert info.display_name == "Octo Cat"


def test_resolve_oauth_creates_user_and_tenant(oauth_db):
    info = OAuthUserInfo(
        provider="github",
        provider_user_id="999",
        email="fresh@example.com",
        display_name="Fresh User",
    )
    user = resolve_oauth_user(oauth_db, info)
    assert user.email == "fresh@example.com"
    assert len(user.memberships) >= 1
    assert user.memberships[0].role == "owner"


def test_resolve_oauth_existing_user_links(oauth_db):
    info = OAuthUserInfo(
        provider="github",
        provider_user_id="111",
        email="link@example.com",
        display_name="Link User",
    )
    first = resolve_oauth_user(oauth_db, info)
    second = resolve_oauth_user(oauth_db, info)
    assert first.id == second.id