from pydantic import EmailStr, Field

from app.schemas.base import CamelModel


class PasswordResetRequestIn(CamelModel):
    email: EmailStr


class PasswordResetRequestOut(CamelModel):
    ok: bool = True
    message: str = "If an account exists for that email, a reset link has been sent."
    reset_url: str | None = None


class PasswordResetConfirmIn(CamelModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class PasswordResetConfirmOut(CamelModel):
    ok: bool = True
    message: str = "Password updated. You can now sign in."