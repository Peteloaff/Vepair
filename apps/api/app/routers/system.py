from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.reminders import send_daily_checkin_reminders

router = APIRouter(prefix="/api/v1/system", tags=["system"])
settings = get_settings()


def _require_internal_job_secret(x_internal_job_secret: str | None = Header(default=None)) -> None:
    """Auth for unattended scheduled jobs (Cloud Scheduler), not a human user -- a shared
    secret compared against INTERNAL_JOB_SECRET, not a JWT. A 15-minute admin access token is
    the wrong credential for something that fires once a day with no one signed in. An unset
    (empty-string default) secret rejects every call, never leaving this open by accident in
    an environment where the env var was simply never configured."""
    if not settings.internal_job_secret or x_internal_job_secret != settings.internal_job_secret:
        raise HTTPException(
            status_code=403,
            detail={"code": "invalid_job_secret", "message": "Invalid or missing job secret."},
        )


@router.post("/send-reminders")
def send_reminders(
    _auth: None = Depends(_require_internal_job_secret),
    db: Session = Depends(get_db),
) -> dict:
    """Meant to be called once daily by an external scheduler -- see TECHNICAL_GUIDE.md for
    the Cloud Scheduler setup. Safe to call more than once in a day: app/reminders.py's own
    NotificationLog dedup means a second call the same day sends nothing further."""
    sent = send_daily_checkin_reminders(db)
    return {"sent": sent}
