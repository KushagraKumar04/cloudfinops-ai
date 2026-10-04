from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.services.auth import AuthError, decode_token


def _get_or_create_demo_tenant(db: Session) -> Tenant:
    settings = get_settings()
    stmt = select(Tenant).where(Tenant.slug == settings.default_tenant_slug).limit(1)
    tenant = db.execute(stmt).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(slug=settings.default_tenant_slug, name="Demo Tenant")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    return tenant


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    settings = get_settings()
    if settings.auth_disabled:
        return None
    token = _extract_token(authorization)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except AuthError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    try:
        import uuid as _uuid

        user_uuid = _uuid.UUID(user_id)
    except (ValueError, TypeError):
        return None
    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    settings = get_settings()
    if settings.auth_disabled:
        import uuid as _uuid

        return User(
            id=_uuid.UUID(int=0),
            email="dev@localhost",
            password_hash="",
            full_name="Dev User",
            is_active=True,
            is_superuser=True,
        )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_tenant(
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> Tenant:
    settings = get_settings()
    if settings.auth_disabled:
        return _get_or_create_demo_tenant(db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = (
        select(TeamMember)
        .where(TeamMember.user_id == user.id)
        .order_by(TeamMember.created_at.asc())
        .limit(1)
    )
    membership = db.execute(stmt).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="No tenant associated with this user")
    tenant = db.get(Tenant, membership.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=403, detail="Tenant not found")
    return tenant