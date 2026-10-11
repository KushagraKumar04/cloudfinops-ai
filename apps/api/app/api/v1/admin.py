import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_superuser
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminUserListOut,
    AdminUserRow,
    AdminUserUpdate,
    PlatformStats,
    TenantDetail,
    TenantListOut,
)
from app.services.admin import (
    get_tenant_detail,
    list_tenants,
    list_users,
    platform_stats,
    update_user,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_superuser)],
)


@router.get("/stats", response_model=PlatformStats)
def get_platform_stats(db: Session = Depends(get_db)) -> PlatformStats:
    return platform_stats(db)


@router.get("/tenants", response_model=TenantListOut)
def list_all_tenants(db: Session = Depends(get_db)) -> TenantListOut:
    items = list_tenants(db)
    return TenantListOut(items=items, total=len(items))


@router.get("/tenants/{tenant_id}", response_model=TenantDetail)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> TenantDetail:
    detail = get_tenant_detail(db, tenant_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return detail


@router.get("/users", response_model=AdminUserListOut)
def list_all_users(db: Session = Depends(get_db)) -> AdminUserListOut:
    items = list_users(db)
    return AdminUserListOut(items=items, total=len(items))


@router.patch("/users/{user_id}", response_model=AdminUserRow)
def update_user_endpoint(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_superuser),
) -> AdminUserRow:
    try:
        user = update_user(
            db,
            user_id,
            payload.is_active,
            payload.is_superuser,
            current.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    from sqlalchemy import func, select

    from app.models.user import TeamMember

    count = int(
        db.execute(
            select(func.count(TeamMember.id)).where(TeamMember.user_id == user.id)
        ).scalar()
        or 0
    )
    return AdminUserRow(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        tenant_count=count,
    )