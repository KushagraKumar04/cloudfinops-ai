import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.invitation import Invitation
from app.models.tenant import Tenant
from app.models.user import TeamMember, User
from app.services.mailer import send_email
from app.services.permissions import VALID_ROLES

INVITE_TTL_DAYS = 7


class InvitationError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def invite_url(token: str) -> str:
    settings = get_settings()
    return f"{settings.frontend_base_url}/accept-invite?token={token}"


def create_invitation(
    db: Session,
    tenant: Tenant,
    inviter: User | None,
    email: str,
    role: str,
) -> Invitation:
    normalized = email.strip().lower()
    if not normalized:
        raise InvitationError("Email is required")
    if role not in VALID_ROLES:
        raise InvitationError(f"Invalid role: {role}")

    existing_user = db.execute(
        select(User).where(User.email == normalized)
    ).scalar_one_or_none()
    if existing_user is not None:
        already_member = db.execute(
            select(TeamMember).where(
                TeamMember.user_id == existing_user.id,
                TeamMember.tenant_id == tenant.id,
            )
        ).scalar_one_or_none()
        if already_member is not None:
            raise InvitationError("User is already a member of this workspace")

    existing_invite = db.execute(
        select(Invitation).where(
            Invitation.tenant_id == tenant.id,
            Invitation.email == normalized,
            Invitation.status == "pending",
        )
    ).scalar_one_or_none()
    if existing_invite is not None:
        if _as_aware(existing_invite.expires_at) <= _now():
            existing_invite.status = "expired"
            db.flush()
        else:
            raise InvitationError("An invitation is already pending for this email")

    invitation = Invitation(
        tenant_id=tenant.id,
        invited_by_user_id=inviter.id if inviter else None,
        email=normalized,
        role=role,
        token=_generate_token(),
        status="pending",
        expires_at=_now() + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    subject = f"You're invited to {tenant.name} on CloudFinOps AI"
    body = (
        f"{inviter.full_name or inviter.email if inviter else 'An admin'} invited you to join "
        f"{tenant.name} as {role}.\n\n"
        f"Accept the invitation:\n{invite_url(invitation.token)}\n\n"
        f"This link expires on {invitation.expires_at.isoformat()}."
    )
    send_email([normalized], subject, body)
    return invitation


def list_invitations(
    db: Session,
    tenant: Tenant,
    status: str | None = "pending",
) -> list[Invitation]:
    stmt = select(Invitation).where(Invitation.tenant_id == tenant.id)
    if status and status != "all":
        stmt = stmt.where(Invitation.status == status)
    stmt = stmt.order_by(Invitation.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def get_invitation_by_token(db: Session, token: str) -> Invitation | None:
    stmt = select(Invitation).where(Invitation.token == token)
    return db.execute(stmt).scalar_one_or_none()


def revoke_invitation(db: Session, tenant: Tenant, invitation_id: uuid.UUID) -> bool:
    invitation = db.get(Invitation, invitation_id)
    if invitation is None or invitation.tenant_id != tenant.id:
        return False
    if invitation.status != "pending":
        return False
    invitation.status = "revoked"
    db.commit()
    return True


def accept_invitation(
    db: Session,
    token: str,
    password: str | None,
    full_name: str | None,
) -> tuple[User, Tenant, str]:
    from app.services.auth import hash_password

    invitation = get_invitation_by_token(db, token)
    if invitation is None:
        raise InvitationError("Invalid invitation")
    if invitation.status != "pending":
        raise InvitationError(f"Invitation is {invitation.status}")
    if _as_aware(invitation.expires_at) <= _now():
        invitation.status = "expired"
        db.commit()
        raise InvitationError("Invitation has expired")

    tenant = db.get(Tenant, invitation.tenant_id)
    if tenant is None:
        raise InvitationError("Workspace not found")

    user = db.execute(
        select(User).where(User.email == invitation.email)
    ).scalar_one_or_none()

    if user is None:
        if not password or len(password) < 8:
            raise InvitationError("Password must be at least 8 characters")
        user = User(
            email=invitation.email,
            password_hash=hash_password(password),
            full_name=(full_name or invitation.email.split("@")[0]).strip(),
            is_active=True,
        )
        db.add(user)
        db.flush()

    existing_membership = db.execute(
        select(TeamMember).where(
            TeamMember.user_id == user.id,
            TeamMember.tenant_id == tenant.id,
        )
    ).scalar_one_or_none()
    if existing_membership is None:
        db.add(TeamMember(user_id=user.id, tenant_id=tenant.id, role=invitation.role))

    invitation.status = "accepted"
    invitation.accepted_at = _now()
    db.commit()
    db.refresh(user)
    db.refresh(tenant)
    return user, tenant, invitation.role