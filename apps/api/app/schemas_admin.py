import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


class AdminSetAdminIn(BaseModel):
    is_admin: bool


class AdminSetPasswordIn(BaseModel):
    new_password: str = Field(min_length=8, max_length=200)


class AdminCreateUserIn(BaseModel):
    """Admin-authorized account creation -- bypasses the public signup lockdown (see
    AdminSiteSettingsIn / app/site_settings.py), since this is an operator deliberately
    creating one account, not the public signup form."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    account_type: Literal["singer", "coach"] = "singer"
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    studio_name: str | None = Field(default=None, max_length=200)
    is_admin: bool = False

    @model_validator(mode="after")
    def _require_display_name_for_coach(self) -> "AdminCreateUserIn":
        if self.account_type == "coach" and not self.display_name:
            raise ValueError("display_name is required when account_type is 'coach'")
        return self


class AdminSiteSettingsOut(BaseModel):
    signups_enabled: bool
    nda_required: bool
    recording_retention_days: int
    checkin_notes_retention_days: int


class AdminSiteSettingsIn(BaseModel):
    signups_enabled: bool
    nda_required: bool
    recording_retention_days: int = Field(gt=0)
    checkin_notes_retention_days: int = Field(gt=0)


class AdminSetCoachIn(BaseModel):
    is_coach: bool
    # Required the first time an account becomes a coach (CoachProfile.display_name is
    # NOT NULL); ignored when is_coach=False. If the account is already a coach and this is
    # provided again, it updates the existing display_name.
    display_name: str | None = Field(default=None, min_length=1, max_length=200)


class AdminUserListItemOut(BaseModel):
    id: uuid.UUID
    email: str
    account_type: str  # "singer" | "coach"
    created_at: datetime
    is_active: bool
    is_admin: bool
    onboarding_complete: bool


class AdminUserDetailOut(AdminUserListItemOut):
    # True "last login" isn't tracked anywhere in the app today (no login-event table) --
    # the most recent RefreshToken issued for this account is used as a proxy for v1, see
    # app/routers/admin.py's get_user_detail. A known, documented gap, not a fabricated metric.
    last_session_at: datetime | None
    last_checkin_date: date | None
    last_recording_at: datetime | None


class AdminSetCoachProIn(BaseModel):
    is_coach_pro_active: bool
    # Only meaningful when activating (is_coach_pro_active=True); ignored when deactivating.
    # Defaults to a one-year period from now if omitted, matching the decided annual cadence.
    period_months: int = Field(default=12, ge=1, le=24)


class AdminOrganizationOut(BaseModel):
    id: uuid.UUID
    name: str | None
    coach_email: str
    coach_display_name: str
    is_coach_pro_active: bool
    coach_pro_period_start: datetime | None
    coach_pro_period_end: datetime | None
    invite_quota_included: int
    invites_used_this_period: int


class AdminReportsSummaryOut(BaseModel):
    total_users: int
    singer_count: int
    coach_count: int
    active_count: int
    deactivated_count: int
    onboarding_completion_rate: float
    signups_last_7_days: int
    signups_last_90_days: int
    dau: int  # distinct users with a check-in or recording in the last 1 day
    wau: int  # same, over the last 7 days
