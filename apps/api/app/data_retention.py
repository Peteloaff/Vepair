"""Data minimization: two independent daily purge policies, both triggered by
POST /api/v1/system/purge-stale-data (app/routers/system.py) -- the same shared-secret,
external-scheduler pattern app/reminders.py already established, see that module's docstring
for the "no in-process scheduler on Cloud Run" reasoning.

purge_stale_recordings: deletes raw audio (the object storage file + Recording.file_path)
once it's older than SiteSettings.recording_retention_days -- but keeps the Recording row and
its AcousticMeasurement, since those derived numbers (not the audio itself) are what actually
power recovery scores, trends, and baselines. This is deliberately NOT the same as a user's own
DELETE /api/v1/recordings/{id} (app/routers/recordings.py), which removes everything -- this
is a passive policy default that preserves trend continuity, that's a user's explicit choice to
lose it.

purge_stale_checkin_notes: nulls out just the three most sensitive DailyCheckIn free-text
fields (illness_symptoms, reflux_symptoms, notes) once they're older than
SiteSettings.checkin_notes_retention_days -- every quantitative check-in field
(voice_quality, fatigue, sleep_hours, etc.) is untouched, so trend charts keep full history.

Both commit once per row, not once at the end -- same crash-safety reasoning as
app/reminders.py's send_daily_checkin_reminders: a mid-batch crash never leaves a retry to
redo work that already succeeded.
"""

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyCheckIn, Recording
from app.site_settings import get_site_settings
from app.storage import get_storage

logger = logging.getLogger("vepair.data_retention")


def purge_stale_recordings(db: Session, *, older_than_days: int | None = None) -> int:
    retention_days = older_than_days or get_site_settings(db).recording_retention_days
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)

    candidates = db.scalars(
        select(Recording).where(
            Recording.created_at < cutoff,
            Recording.file_path.is_not(None),
        )
    ).all()

    storage = get_storage()
    purged = 0
    for recording in candidates:
        try:
            storage.delete(recording.file_path)
        except Exception:
            # A flaky storage call must never block the rest of the batch -- log it and move
            # on, same posture as app/account_deletion.py's per-recording delete loop. An
            # orphaned file is a smaller problem than a purge job that silently stalls.
            logger.error(
                "Failed to delete recording file during retention purge: recording_id=%s "
                "file_path=%s",
                recording.id,
                recording.file_path,
                exc_info=True,
            )
            continue
        recording.file_path = None
        recording.audio_purged_at = datetime.now(UTC)
        db.commit()
        purged += 1

    return purged


def purge_stale_checkin_notes(db: Session, *, older_than_days: int | None = None) -> int:
    retention_days = older_than_days or get_site_settings(db).checkin_notes_retention_days
    cutoff: date = (datetime.now(UTC) - timedelta(days=retention_days)).date()

    candidates = db.scalars(
        select(DailyCheckIn).where(
            DailyCheckIn.checkin_date < cutoff,
            (
                DailyCheckIn.illness_symptoms.is_not(None)
                | DailyCheckIn.reflux_symptoms.is_not(None)
                | DailyCheckIn.notes.is_not(None)
            ),
        )
    ).all()

    purged = 0
    for checkin in candidates:
        checkin.illness_symptoms = None
        checkin.reflux_symptoms = None
        checkin.notes = None
        db.commit()
        purged += 1

    return purged
