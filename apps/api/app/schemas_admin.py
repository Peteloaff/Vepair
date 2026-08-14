import uuid
from datetime import date, datetime

from pydantic import BaseModel


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
