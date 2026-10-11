import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from datetime import UTC, datetime

from app.api.deps import get_current_tenant, get_current_user, get_current_user_optional
from app.config import get_settings
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.schemas.auth import LoginIn, RegisterIn, TenantOut, TokenOut, UserOut
from app.schemas.invitation import (
    InvitationAcceptIn,
    InvitationPreview,
    OAuthProvider,
)
from app.schemas.password_reset import (
    PasswordResetConfirmIn,
    PasswordResetConfirmOut,
    PasswordResetRequestIn,
    PasswordResetRequestOut,
)
from app.services.password_reset import (
    PasswordResetError,
    consume_reset,
    request_reset,
)
from app.services.auth import AuthError, create_access_token, hash_password, verify_password
from app.services.invitations import (
    InvitationError,
    accept_invitation,
    get_invitation_by_token,
)
from app.services.oauth import (
    OAuthError,
    build_authorize_url,
    exchange_code_for_user,
    verify_state,
)
from app.services.permissions import permissions_for_role

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    cleaned = cleaned.strip("-")
    return cleaned[:48] or "organization"


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    suffix = 1
    while True:
        exists = db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
        if exists is None:
            return slug
        suffix += 1
        slug = f"{base}-{suffix}"


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at or datetime.now(UTC),
    )


def _tenant_out(tenant: Tenant, role: str) -> TenantOut:
    return TenantOut(id=tenant.id, slug=tenant.slug, name=tenant.name, role=role)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(
    payload: RegisterIn,
    db: Session = Depends(get_db),
) -> TokenOut:
    email = payload.email.strip().lower()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        hashed = hash_password(payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    now = datetime.now(UTC)
    user = User(
        email=email,
        password_hash=hashed,
        full_name=payload.full_name.strip(),
        is_active=True,
    )
    user.created_at = now
    user.updated_at = now
    db.add(user)
    db.flush()

    org_name = payload.organization_name.strip() or f"{email.split('@')[0]}'s workspace"
    slug = _unique_slug(db, _slugify(org_name))
    tenant = Tenant(slug=slug, name=org_name, settings={})
    tenant.created_at = now
    tenant.updated_at = now
    db.add(tenant)
    db.flush()

    db.add(TeamMember(user_id=user.id, tenant_id=tenant.id, role="owner"))
    db.commit()
    db.refresh(user)
    db.refresh(tenant)

    if get_settings().demo_mode:
        import logging

        logger = logging.getLogger("app.auth")
        try:
            from app.cli.seed import seed_tenant_data

            seed_tenant_data(db, tenant)
            db.commit()
        except Exception:
            logger.exception("Demo seed failed for tenant %s", tenant.id)
            db.rollback()

    token = create_access_token(user.id, user.email)
    expires_in = get_settings().jwt_expires_minutes * 60
    return TokenOut(
        access_token=token,
        expires_in=expires_in,
        user=_user_out(user),
        tenant=_tenant_out(tenant, "owner"),
    )


@router.post("/login", response_model=TokenOut)
def login(
    payload: LoginIn,
    db: Session = Depends(get_db),
) -> TokenOut:
    email = payload.email.strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(user.id, user.email)

    membership = db.execute(
        select(TeamMember).where(TeamMember.user_id == user.id).limit(1)
    ).scalar_one_or_none()
    tenant_info: TenantOut | None = None
    if membership is not None:
        tenant = db.get(Tenant, membership.tenant_id)
        if tenant is not None:
            tenant_info = _tenant_out(tenant, membership.role)

    expires_in = get_settings().jwt_expires_minutes * 60
    return TokenOut(
        access_token=token,
        expires_in=expires_in,
        user=_user_out(user),
        tenant=tenant_info,
    )


@router.get("/me")
def me(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    role = "owner"
    if not get_settings().auth_disabled:
        membership = user.memberships[0] if user.memberships else None
        if membership is not None:
            role = membership.role
    return {
        "user": _user_out(user).model_dump(by_alias=True),
        "tenant": _tenant_out(tenant, role).model_dump(by_alias=True),
        "permissions": permissions_for_role(role),
    }


@router.post("/logout", status_code=204)
def logout() -> None:
    return None


@router.get("/invitations/{token}", response_model=InvitationPreview)
def preview_invitation(
    token: str,
    db: Session = Depends(get_db),
) -> InvitationPreview:
    invitation = get_invitation_by_token(db, token)
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    tenant = db.get(Tenant, invitation.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return InvitationPreview(
        email=invitation.email,
        role=invitation.role,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        expires_at=invitation.expires_at,
        status=invitation.status,
    )


@router.post("/invitations/{token}/accept", response_model=TokenOut)
def accept_invitation_endpoint(
    token: str,
    payload: InvitationAcceptIn,
    db: Session = Depends(get_db),
) -> TokenOut:
    try:
        user, tenant, role = accept_invitation(db, token, payload.password, payload.full_name)
    except InvitationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    access_token = create_access_token(user.id, user.email)
    expires_in = get_settings().jwt_expires_minutes * 60
    return TokenOut(
        access_token=access_token,
        expires_in=expires_in,
        user=_user_out(user),
        tenant=_tenant_out(tenant, role),
    )


@router.post("/password-reset/request", response_model=PasswordResetRequestOut)
def password_reset_request(
    payload: PasswordResetRequestIn,
    db: Session = Depends(get_db),
) -> PasswordResetRequestOut:
    settings = get_settings()
    reset_url = request_reset(db, payload.email)
    expose_url = reset_url if not settings.smtp_enabled else None
    return PasswordResetRequestOut(reset_url=expose_url)


@router.post("/password-reset/confirm", response_model=PasswordResetConfirmOut)
def password_reset_confirm(
    payload: PasswordResetConfirmIn,
    db: Session = Depends(get_db),
) -> PasswordResetConfirmOut:
    try:
        consume_reset(db, payload.token, payload.password)
    except PasswordResetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PasswordResetConfirmOut()


@router.get("/oauth/providers", response_model=list[OAuthProvider])
def list_oauth_providers() -> list[OAuthProvider]:
    settings = get_settings()
    enabled = settings.oauth_enabled
    return [
        OAuthProvider(id="github", label="GitHub", enabled=enabled and bool(settings.github_client_id)),
        OAuthProvider(id="google", label="Google", enabled=enabled and bool(settings.google_client_id)),
    ]


@router.get("/oauth/{provider}/authorize")
def oauth_authorize(provider: str) -> RedirectResponse:
    try:
        url, _ = build_authorize_url(provider)
    except OAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=url)


@router.get("/oauth/{provider}/callback")
def oauth_callback(
    provider: str,
    code: str,
    state: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    try:
        verify_state(state, provider)
        user = exchange_code_for_user(db, provider, code)
    except OAuthError as exc:
        failure = f"{settings.frontend_base_url}/oauth/callback#error={exc}"
        return RedirectResponse(url=failure, status_code=302)

    access_token = create_access_token(user.id, user.email)
    target = f"{settings.frontend_base_url}/oauth/callback#token={access_token}"
    return RedirectResponse(url=target, status_code=302)