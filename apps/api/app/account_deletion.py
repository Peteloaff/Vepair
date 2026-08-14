"""Permanent account deletion -- the single deletion code path in the app, used by both
self-serve delete (DELETE /api/v1/auth/me) and admin hard-delete (POST
/api/v1/admin/users/{id}/delete), so there is exactly one place this logic lives rather than two
that can drift.

Deletes every stored recording's actual audio file from object storage *before* deleting the
User row: the row's ON DELETE CASCADE foreign keys already remove every database record
(profile, check-ins, recordings, measurements, baselines, scores, vocal range history, exercise
history, coach connections, notes, consent records, everything), but cascade never touches object
storage -- a Recording row disappearing doesn't delete the WAV file behind it.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recording, User, VoiceSession
from app.storage import get_storage

logger = logging.getLogger("vepair.auth")


def delete_user_and_storage(db: Session, user: User) -> None:
    recordings = db.scalars(
        select(Recording).join(VoiceSession).where(VoiceSession.user_id == user.id)
    ).all()
    storage = get_storage()
    for recording in recordings:
        try:
            storage.delete(recording.file_path)
        except Exception:
            # A single flaky storage call must never block a deletion -- log it and keep going;
            # an orphaned file is a smaller problem than an account that cannot be removed.
            logger.error(
                "Failed to delete recording file during account deletion: user_id=%s "
                "recording_id=%s file_path=%s",
                user.id,
                recording.id,
                recording.file_path,
                exc_info=True,
            )

    db.delete(user)
    db.commit()
