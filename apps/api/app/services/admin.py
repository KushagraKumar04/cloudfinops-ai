import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.cloud_account import CloudAccount
from app.models.cost import CostRecord
from app.models.recommendation import Recommendation
from app.models.resource import Resource
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.schemas.admin import (
    AdminCloudAccount,
    AdminMember,
    AdminUserRow,
    PlatformStats,
    TenantDetail,
    TenantSummary,
)


def _count(db: Session, model, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(model.id)).where(model.tenant_id == tenant_id)
    return int(db.execute(stmt).scalar() or 0)


def list_tenants(db: Session) -> list[TenantSummary]:
    tenants = list(db.execute(select(Tenant).order_by(Tenant.created_at.asc())).scalars().all())
    out: list[TenantSummary] = []
    for t in tenants:
        out.append(
            TenantSummary(
                id=t.id,
                slug=t.slug,
                name=t.name,
                created_at=t.created_at,
                user_count=_count(db, TeamMember, t.id),
                cloud_account_count=_count(db, CloudAccount, t.id),
                resource_count=_count(db, Resource, t.id),
                recommendation_count=_count(db, Recommendation, t.id),
                cost_record_count=_count(db, CostRecord, t.id),
                audit_event_count=_count(db, AuditEvent, t.id),
            )
        )
    return out


def get_tenant_detail(db: Session, tenant_id: uuid.UUID) -> TenantDetail | None:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        return None

    summary = TenantSummary(
        id=tenant.id,
        slug=tenant.slug,
        name=tenant.name,
        created_at=tenant.created_at,
        user_count=_count(db, TeamMember, tenant.id),
        cloud_account_count=_count(db, CloudAccount, tenant.id),
        resource_count=_count(db, Resource, tenant.id),
        recommendation_count=_count(db, Recommendation, tenant.id),
        cost_record_count=_count(db, CostRecord, tenant.id),
        audit_event_count=_count(db, AuditEvent, tenant.id),
    )

    memberships = list(
        db.execute(
            select(TeamMember)
            .where(TeamMember.tenant_id == tenant.id)
            .order_by(TeamMember.created_at.asc())
        )
        .scalars()
        .all()
    )
    user_ids = {m.user_id for m in memberships}
    users: dict[uuid.UUID, User] = {}
    if user_ids:
        for u in db.execute(select(User).where(User.id.in_(user_ids))).scalars().all():
            users[u.id] = u

    members = [
        AdminMember(
            user_id=m.user_id,
            email=users[m.user_id].email if m.user_id in users else "",
            full_name=users[m.user_id].full_name if m.user_id in users else "",
            role=m.role,
            is_active=users[m.user_id].is_active if m.user_id in users else False,
            is_superuser=users[m.user_id].is_superuser if m.user_id in users else False,
            joined_at=m.created_at,
        )
        for m in memberships
    ]

    accounts = list(
        db.execute(
            select(CloudAccount)
            .where(CloudAccount.tenant_id == tenant.id)
            .order_by(CloudAccount.created_at.asc())
        )
        .scalars()
        .all()
    )
    cloud_accounts = [
        AdminCloudAccount(
            id=a.id,
            name=a.name,
            provider=a.provider,
            environment=a.environment,
            status=a.status,
            resource_count=a.resource_count,
            monthly_spend=float(a.monthly_spend or 0),
            disabled=a.disabled_at is not None,
        )
        for a in accounts
    ]

    return TenantDetail(
        **summary.model_dump(),
        members=members,
        cloud_accounts=cloud_accounts,
        recent_recommendations=summary.recommendation_count,
    )


def list_users(db: Session) -> list[AdminUserRow]:
    users = list(db.execute(select(User).order_by(User.created_at.desc())).scalars().all())
    counts: dict[uuid.UUID, int] = {}
    if users:
        rows = db.execute(
            select(TeamMember.user_id, func.count(TeamMember.id))
            .where(TeamMember.user_id.in_({u.id for u in users}))
            .group_by(TeamMember.user_id)
        ).all()
        counts = {user_id: int(count) for user_id, count in rows}

    return [
        AdminUserRow(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            is_superuser=u.is_superuser,
            created_at=u.created_at,
            tenant_count=counts.get(u.id, 0),
        )
        for u in users
    ]


def update_user(
    db: Session,
    user_id: uuid.UUID,
    is_active: bool | None,
    is_superuser: bool | None,
    acting_user_id: uuid.UUID | None,
) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None

    if acting_user_id == user.id:
        if is_active is False:
            raise ValueError("You cannot disable your own account")
        if is_superuser is False:
            raise ValueError("You cannot remove your own superuser flag")

    if is_active is not None:
        user.is_active = is_active
    if is_superuser is not None:
        user.is_superuser = is_superuser

    membership = db.execute(
        select(TeamMember).where(TeamMember.user_id == user.id).limit(1)
    ).scalar_one_or_none()
    tenant_id = membership.tenant_id if membership else None

    if tenant_id is not None:
        db.add(
            AuditEvent(
                tenant_id=tenant_id,
                at=datetime.now(UTC),
                category="auth",
                severity="info",
                actor=str(acting_user_id) if acting_user_id else "system",
                action="User updated",
                subject=user.email,
                details=f"is_active={user.is_active} is_superuser={user.is_superuser}",
                event_metadata=[{"key": "user_id", "value": str(user.id)}],
            )
        )
    db.commit()
    db.refresh(user)
    return user


def platform_stats(db: Session) -> PlatformStats:
    tenant_count = int(db.execute(select(func.count(Tenant.id))).scalar() or 0)
    user_count = int(db.execute(select(func.count(User.id))).scalar() or 0)
    active_user_count = int(
        db.execute(select(func.count(User.id)).where(User.is_active.is_(True))).scalar() or 0
    )
    cloud_account_count = int(db.execute(select(func.count(CloudAccount.id))).scalar() or 0)
    resource_count = int(db.execute(select(func.count(Resource.id))).scalar() or 0)
    recommendation_count = int(db.execute(select(func.count(Recommendation.id))).scalar() or 0)
    cost_record_count = int(db.execute(select(func.count(CostRecord.id))).scalar() or 0)
    audit_event_count = int(db.execute(select(func.count(AuditEvent.id))).scalar() or 0)
    total_spend = float(
        db.execute(select(func.coalesce(func.sum(CloudAccount.monthly_spend), 0))).scalar() or 0
    )

    provider_rows = db.execute(
        select(CloudAccount.provider, func.count(CloudAccount.id))
        .group_by(CloudAccount.provider)
    ).all()
    providers = {str(p): int(c) for p, c in provider_rows}

    return PlatformStats(
        tenant_count=tenant_count,
        user_count=user_count,
        active_user_count=active_user_count,
        cloud_account_count=cloud_account_count,
        resource_count=resource_count,
        recommendation_count=recommendation_count,
        cost_record_count=cost_record_count,
        audit_event_count=audit_event_count,
        total_monthly_spend=round(total_spend, 2),
        breakdown={"accounts_by_provider": providers},
    )