import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_role, get_current_tenant, require_permission
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.api.deps import get_current_user
from app.config import get_settings
from app.models.user import User
from app.schemas.invitation import (
    InvitationCreateIn,
    InvitationListOut,
    InvitationOut,
)
from app.schemas.team import (
    TeamListOut,
    TeamMemberOut,
    TeamMemberUpdateIn,
    TeamMemberUser,
)
from app.services.invitations import (
    InvitationError,
    create_invitation,
    invite_url,
    list_invitations,
    revoke_invitation,
)
from app.services.permissions import Permission

router = APIRouter(prefix="/team", tags=["team"])


def _to_out(member: TeamMember, user: User) -> TeamMemberOut:
    return TeamMemberOut(
        id=member.id,
        user=TeamMemberUser(id=user.id, email=user.email, full_name=user.full_name),
        role=member.role,
        created_at=member.created_at,
    )


@router.get("", response_model=TeamListOut)
def list_members(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    current_role: str = Depends(get_current_role),
) -> TeamListOut:
    stmt = (
        select(TeamMember)
        .where(TeamMember.tenant_id == tenant.id)
        .order_by(TeamMember.created_at.asc())
    )
    members = list(db.execute(stmt).scalars().all())
    user_ids = {m.user_id for m in members}
    users: dict[uuid.UUID, User] = {}
    if user_ids:
        users_stmt = select(User).where(User.id.in_(user_ids))
        for u in db.execute(users_stmt).scalars().all():
            users[u.id] = u

    items: list[TeamMemberOut] = []
    for m in members:
        user = users.get(m.user_id)
        if user is None:
            continue
        items.append(_to_out(m, user))

    return TeamListOut(items=items, total=len(items), current_role=current_role)


@router.patch(
    "/{member_id}",
    response_model=TeamMemberOut,
    dependencies=[Depends(require_permission(Permission.MANAGE_TEAM))],
)
def update_member_role(
    member_id: uuid.UUID,
    payload: TeamMemberUpdateIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> TeamMemberOut:
    member = db.get(TeamMember, member_id)
    if member is None or member.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.role == "owner" and payload.role != "owner":
        owners = db.execute(
            select(TeamMember).where(
                TeamMember.tenant_id == tenant.id,
                TeamMember.role == "owner",
            )
        ).scalars().all()
        if len(owners) <= 1:
            raise HTTPException(status_code=409, detail="Cannot demote the last owner")

    member.role = payload.role
    db.commit()
    db.refresh(member)

    user = db.get(User, member.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_out(member, user)


@router.delete(
    "/{member_id}",
    status_code=204,
    dependencies=[Depends(require_permission(Permission.MANAGE_TEAM))],
)
def remove_member(
    member_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    member = db.get(TeamMember, member_id)
    if member is None or member.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.role == "owner":
        owners = db.execute(
            select(TeamMember).where(
                TeamMember.tenant_id == tenant.id,
                TeamMember.role == "owner",
            )
        ).scalars().all()
        if len(owners) <= 1:
            raise HTTPException(status_code=409, detail="Cannot remove the last owner")

    db.delete(member)
    db.commit()
    return None


def _invitation_to_out(invitation, invited_by: User | None, include_url: bool) -> InvitationOut:
    out = InvitationOut.model_validate(invitation)
    out.invited_by_name = invited_by.full_name or invited_by.email if invited_by else None
    if include_url and invitation.status == "pending":
        out.invite_url = invite_url(invitation.token)
    return out


@router.get("/invitations", response_model=InvitationListOut)
def list_team_invitations(
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    status: str | None = "pending",
) -> InvitationListOut:
    rows = list_invitations(db, tenant, status=status)
    inviter_ids = {r.invited_by_user_id for r in rows if r.invited_by_user_id}
    inviters: dict[uuid.UUID, User] = {}
    if inviter_ids:
        for u in db.execute(select(User).where(User.id.in_(inviter_ids))).scalars().all():
            inviters[u.id] = u

    settings = get_settings()
    expose_url = not settings.smtp_enabled
    items = [
        _invitation_to_out(r, inviters.get(r.invited_by_user_id) if r.invited_by_user_id else None, expose_url)
        for r in rows
    ]
    return InvitationListOut(items=items, total=len(items))


@router.post(
    "/invitations",
    response_model=InvitationOut,
    status_code=201,
    dependencies=[Depends(require_permission(Permission.MANAGE_TEAM))],
)
def create_team_invitation(
    payload: InvitationCreateIn,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> InvitationOut:
    try:
        invitation = create_invitation(db, tenant, user, payload.email, payload.role)
    except InvitationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    settings = get_settings()
    expose_url = not settings.smtp_enabled
    return _invitation_to_out(invitation, user, expose_url)


@router.delete(
    "/invitations/{invitation_id}",
    status_code=204,
    dependencies=[Depends(require_permission(Permission.MANAGE_TEAM))],
)
def revoke_team_invitation(
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> None:
    if not revoke_invitation(db, tenant, invitation_id):
        raise HTTPException(status_code=404, detail="Invitation not found or already resolved")
    return None