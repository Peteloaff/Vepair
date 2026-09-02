"""Shared notifications-consent lookup — used by app/reminders.py's daily batch and by the
coach<->Vrotégé messaging endpoints (app/routers/coach.py, app/routers/coach_access.py) before
sending a new-message email. Same query GET /api/v1/consent/notifications already uses."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConsentRecord


def has_notifications_consent(db: Session, user_id: uuid.UUID) -> bool:
    """Only ever true for an explicit, current `granted=True` -- never for null (undecided)
    or an explicit decline."""
    latest = db.scalar(
        select(ConsentRecord)
        .where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == "notifications",
        )
        .order_by(ConsentRecord.granted_at.desc())
        .limit(1)
    )
    return latest is not None and latest.granted
