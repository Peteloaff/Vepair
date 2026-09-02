"""Practice reminders -- the single v1 reminder type: a "how's your voice today?" email for
every singer who hasn't checked in yet today and has opted into notifications. Triggered by
POST /api/v1/system/send-reminders (app/routers/system.py), meant to be called once daily by
an external scheduler (Cloud Scheduler) -- see TECHNICAL_GUIDE.md for the setup.

Kept as a plain function, not inline in the router, so it's directly unit-testable without an
HTTP round trip -- same split every other stage in this app uses between pure/orchestration
logic and its router.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.email import send_checkin_reminder_email
from app.models import DailyCheckIn, NotificationLog, User, UserProfile
from app.notifications import has_notifications_consent

NOTIFICATION_TYPE_CHECKIN_REMINDER = "checkin_reminder"


def send_daily_checkin_reminders(db: Session, *, for_date: date | None = None) -> int:
    """Sends the reminder to every eligible singer and returns how many were sent.

    Eligible: has a UserProfile (a coach-only account has nothing to check in about), is
    active, has not already submitted a DailyCheckIn for `for_date` (server-side date --
    a per-user-timezone version of "today" would need a stored timezone this app doesn't
    have yet, a known, acceptable simplification for v1), has not already been sent this
    exact reminder today (NotificationLog dedup -- safe to call this function twice in a day),
    and has explicit notifications consent granted.

    Commits once per user sent, not once at the end -- if this crashes partway through a large
    batch, everyone already sent stays logged and is never double-emailed on a retry."""
    today = for_date or date.today()

    already_checked_in = select(DailyCheckIn.user_id).where(DailyCheckIn.checkin_date == today)
    already_sent = select(NotificationLog.user_id).where(
        NotificationLog.notification_type == NOTIFICATION_TYPE_CHECKIN_REMINDER,
        NotificationLog.sent_for_date == today,
    )

    candidates = db.scalars(
        select(User)
        .join(UserProfile, UserProfile.user_id == User.id)
        .where(
            User.is_active.is_(True),
            User.id.notin_(already_checked_in),
            User.id.notin_(already_sent),
        )
    ).all()

    sent = 0
    for user in candidates:
        if not has_notifications_consent(db, user.id):
            continue
        send_checkin_reminder_email(user.email)
        db.add(
            NotificationLog(
                user_id=user.id,
                notification_type=NOTIFICATION_TYPE_CHECKIN_REMINDER,
                sent_for_date=today,
            )
        )
        db.commit()
        sent += 1

    return sent
