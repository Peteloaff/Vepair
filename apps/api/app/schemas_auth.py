import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class CoachSignupRequest(BaseModel):
    """A coach account is a coach account from creation — see app.models.CoachProfile. There
    is no separate "become a coach" upgrade path on an existing (singer) account."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    studio_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetConfirmSchema(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=200)


class AccountDeletionRequest(BaseModel):
    """Requires the current password, same security bar as changing a password -- this is
    permanent and cannot be undone, so it should never be a single accidental click away."""

    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime
    # Surfaced here (not just via /api/v1/admin/profile) so the frontend's global auth
    # context already knows this on every page load without a second request -- used only
    # to decide whether to show a link to /admin, never trusted as the actual authorization
    # check (every /api/v1/admin/* route re-verifies server-side via get_current_admin).
    is_admin: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
