import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class AdminSetAdminIn(BaseModel):
    is_admin: bool


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
