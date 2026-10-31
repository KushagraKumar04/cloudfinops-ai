import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.auth import hash_password
from app.services.mailer import send_email

RESET_TTL_MINUTES = 60


class PasswordResetError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def request_reset(db: Session, email: str) -> str | None:
    settings = get_settings()
    normalized = email.strip().lower()
    if not normalized:
        return None

    user = db.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if user is None or not user.is_active:
        return None

    stale = db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    ).scalars().all()
    for token in stale:
        token.used_at = _now()

    token = PasswordResetToken(
        user_id=user.id,
        token=_generate_token(),
        expires_at=_now() + timedelta(minutes=RESET_TTL_MINUTES),
    )
    db.add(token)
    db.commit()
    db.refresh(token)

    reset_url = f"{settings.frontend_base_url}/reset-password?token={token.token}"
    subject = "Reset your CloudFinOps AI password"
    body = (
        f"A password reset was requested for your account.\n\n"
        f"Reset your password:\n{reset_url}\n\n"
        f"This link expires in {RESET_TTL_MINUTES} minutes. "
        f"If you did not request a password reset, ignore this email."
    )
    send_email([user.email], subject, body)
    return reset_url


def consume_reset(db: Session, token: str, new_password: str) -> User:
    if not new_password or len(new_password) < 8:
        raise PasswordResetError("Password must be at least 8 characters")

    entry = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    ).scalar_one_or_none()
    if entry is None:
        raise PasswordResetError("Invalid or expired reset link")
    if entry.used_at is not None:
        raise PasswordResetError("This reset link has already been used")
    if _as_aware(entry.expires_at) <= _now():
        entry.used_at = _now()
        db.commit()
        raise PasswordResetError("This reset link has expired")

    user = db.get(User, entry.user_id)
    if user is None or not user.is_active:
        raise PasswordResetError("Account is not accessible")

    user.password_hash = hash_password(new_password)
    entry.used_at = _now()
    db.commit()
    db.refresh(user)
    return user


def purge_expired(db: Session) -> int:
    cutoff = _now() - timedelta(days=7)
    rows = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.created_at <= cutoff)
    ).scalars().all()
    for row in rows:
        db.delete(row)
    db.commit()
    return len(rows)