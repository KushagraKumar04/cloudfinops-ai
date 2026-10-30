import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.invitation import OAuthIdentity
from app.models.user import User

STATE_STORE: dict[str, dict] = {}


class OAuthError(Exception):
    pass


@dataclass
class OAuthUserInfo:
    provider: str
    provider_user_id: str
    email: str
    display_name: str


PROVIDER_CONFIG = {
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scope": "read:user user:email",
    },
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
}


def _client_credentials(provider: str) -> tuple[str, str]:
    settings = get_settings()
    if provider == "github":
        return settings.github_client_id, settings.github_client_secret
    if provider == "google":
        return settings.google_client_id, settings.google_client_secret
    raise OAuthError(f"Unsupported provider: {provider}")


def _redirect_uri(provider: str) -> str:
    settings = get_settings()
    return f"{settings.oauth_redirect_base_url}/api/v1/auth/oauth/{provider}/callback"


def build_authorize_url(provider: str) -> tuple[str, str]:
    if provider not in PROVIDER_CONFIG:
        raise OAuthError(f"Unsupported provider: {provider}")
    client_id, _ = _client_credentials(provider)
    if not client_id:
        raise OAuthError(f"{provider} OAuth is not configured")

    state = secrets.token_urlsafe(24)
    STATE_STORE[state] = {"provider": provider, "created_at": datetime.now(UTC).isoformat()}
    if len(STATE_STORE) > 1000:
        STATE_STORE.clear()

    config = PROVIDER_CONFIG[provider]
    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(provider),
        "scope": config["scope"],
        "state": state,
        "response_type": "code",
    }
    return f"{config['authorize_url']}?{urlencode(params)}", state


def verify_state(state: str, provider: str) -> None:
    entry = STATE_STORE.pop(state, None)
    if entry is None:
        raise OAuthError("Invalid or expired state")
    if entry.get("provider") != provider:
        raise OAuthError("State provider mismatch")


def _exchange_code(provider: str, code: str) -> str:
    client_id, client_secret = _client_credentials(provider)
    config = PROVIDER_CONFIG[provider]
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": _redirect_uri(provider),
    }
    if provider == "google":
        payload["grant_type"] = "authorization_code"

    headers = {"Accept": "application/json"}
    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(config["token_url"], data=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise OAuthError(f"Token exchange failed: {exc}") from exc

    if response.status_code >= 400:
        raise OAuthError(f"Token exchange returned {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise OAuthError("Token exchange returned non-JSON") from exc

    access_token = data.get("access_token")
    if not access_token:
        raise OAuthError("Token exchange did not return an access token")
    return access_token


def _fetch_user_info(provider: str, access_token: str) -> OAuthUserInfo:
    config = PROVIDER_CONFIG[provider]
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    if provider == "github":
        headers["X-GitHub-Api-Version"] = "2022-11-28"

    try:
        with httpx.Client(timeout=15) as client:
            user_response = client.get(config["user_url"], headers=headers)
    except httpx.HTTPError as exc:
        raise OAuthError(f"User fetch failed: {exc}") from exc

    if user_response.status_code >= 400:
        raise OAuthError(f"User fetch returned {user_response.status_code}")

    data = user_response.json()

    if provider == "github":
        provider_user_id = str(data.get("id", ""))
        email = data.get("email") or ""
        display_name = data.get("name") or data.get("login") or ""
        if not email:
            try:
                with httpx.Client(timeout=15) as client:
                    emails_response = client.get(config["emails_url"], headers=headers)
                if emails_response.status_code < 400:
                    emails = emails_response.json()
                    primary = next(
                        (e for e in emails if e.get("primary") and e.get("verified")),
                        next((e for e in emails if e.get("verified")), None),
                    )
                    if primary:
                        email = primary["email"]
            except httpx.HTTPError:
                pass
        return OAuthUserInfo(
            provider=provider,
            provider_user_id=provider_user_id,
            email=email.lower(),
            display_name=display_name,
        )

    if provider == "google":
        return OAuthUserInfo(
            provider=provider,
            provider_user_id=str(data.get("sub", "")),
            email=(data.get("email") or "").lower(),
            display_name=data.get("name") or "",
        )

    raise OAuthError(f"Unsupported provider: {provider}")


def resolve_oauth_user(
    db: Session,
    info: OAuthUserInfo,
    tenant_id: uuid.UUID | None = None,
) -> User:
    identity = db.execute(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == info.provider,
            OAuthIdentity.provider_user_id == info.provider_user_id,
        )
    ).scalar_one_or_none()

    if identity is not None:
        user = db.get(User, identity.user_id)
        if user is None or not user.is_active:
            raise OAuthError("Account is not accessible")
        identity.last_login_at = datetime.now(UTC)
        db.commit()
        return user

    if not info.email:
        raise OAuthError(f"{info.provider} did not return an email address")

    user = db.execute(select(User).where(User.email == info.email)).scalar_one_or_none()
    if user is None:
        from app.models.tenant import Tenant
        from app.models.user import TeamMember

        user = User(
            email=info.email,
            password_hash="",
            full_name=info.display_name or info.email.split("@")[0],
            is_active=True,
        )
        db.add(user)
        db.flush()

        if tenant_id is None:
            tenant = Tenant(
                slug=info.email.split("@")[0] + "-workspace"[:48],
                name=f"{info.display_name or info.email}'s workspace",
                settings={},
            )
            db.add(tenant)
            db.flush()
            tenant_id = tenant.id

        db.add(TeamMember(user_id=user.id, tenant_id=tenant_id, role="owner"))

    identity = OAuthIdentity(
        user_id=user.id,
        provider=info.provider,
        provider_user_id=info.provider_user_id,
        email=info.email,
        display_name=info.display_name,
        last_login_at=datetime.now(UTC),
    )
    db.add(identity)
    db.commit()
    db.refresh(user)
    return user


def exchange_code_for_user(db: Session, provider: str, code: str) -> User:
    token = _exchange_code(provider, code)
    info = _fetch_user_info(provider, token)
    return resolve_oauth_user(db, info)