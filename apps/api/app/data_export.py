"""Self-serve "download my data" export -- GET /api/v1/profile/export
(app/routers/profile.py). Structured data only: raw audio bytes are deliberately excluded
(each recording links back to the existing GET /api/v1/recordings/{id}/audio endpoint instead
of embedding binary data), so this stays a small, synchronous, single-request response -- no
async job needed at this data scale.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AcousticMeasurement,
    Baseline,
    CoachAccess,
    CoachAssignment,
    CoachInvite,
    CoachMessage,
    CoachNote,
    CoachProfile,
    ConsentRecord,
    DailyCheckIn,
    ExerciseResult,
    ExerciseSession,
    RecoveryScore,
    ToneGameAttempt,
    ToneGameSession,
    User,
    UserProfile,
    VocalGoal,
    VocalPlan,
    VocalRange,
    VoiceSession,
)


def _row_dict(row, *, omit: tuple[str, ...] = ()) -> dict:
    """Every column of one ORM row as a plain dict, minus anything in `omit`. Only ever called
    on rows already scoped to the exporting user, and never on User/AuthCredential/
    RefreshToken/PasswordResetToken -- so "every column" is safe here without a per-table
    allowlist."""
    return {c.name: getattr(row, c.name) for c in row.__table__.columns if c.name not in omit}


def _rows(db: Session, model, **filters) -> list[dict]:
    stmt = select(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    return [_row_dict(row) for row in db.scalars(stmt).all()]


def _row(db: Session, model, **filters) -> dict | None:
    stmt = select(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    row = db.scalar(stmt)
    return _row_dict(row) if row is not None else None


def build_user_data_export(db: Session, user: User) -> dict:
    """Everything keyed to this user's own id, across every table that references it, plus
    (if they're also a coach) what they've authored for others. Deliberately excludes anything
    password/token-related (AuthCredential, RefreshToken, PasswordResetToken) -- those aren't
    data *about* the user in the sense this export means."""
    voice_sessions = db.scalars(select(VoiceSession).where(VoiceSession.user_id == user.id)).all()

    export: dict = {
        "exported_at": datetime.now(UTC).isoformat(),
        "account": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at.isoformat(),
        },
        "profile": _row(db, UserProfile, user_id=user.id),
        "consent_history": _rows(db, ConsentRecord, user_id=user.id),
        "checkins": _rows(db, DailyCheckIn, user_id=user.id),
        "voice_sessions": [
            {
                **_row_dict(session),
                "recordings": [
                    {
                        **_row_dict(recording, omit=("file_path",)),
                        "audio_download_url": (
                            f"/api/v1/recordings/{recording.id}/audio"
                            if recording.file_path
                            else None
                        ),
                        "measurement": _row(db, AcousticMeasurement, recording_id=recording.id),
                    }
                    for recording in session.recordings
                ],
            }
            for session in voice_sessions
        ],
        "baselines": _rows(db, Baseline, user_id=user.id),
        "recovery_scores": _rows(db, RecoveryScore, user_id=user.id),
        "vocal_range_history": _rows(db, VocalRange, user_id=user.id),
        "vocal_goal": _row(db, VocalGoal, user_id=user.id),
        "vocal_plans": _rows(db, VocalPlan, user_id=user.id),
        "exercise_sessions": [
            {
                **_row_dict(session),
                "results": _rows(db, ExerciseResult, exercise_session_id=session.id),
            }
            for session in db.scalars(
                select(ExerciseSession).where(ExerciseSession.user_id == user.id)
            ).all()
        ],
        "tone_game_sessions": [
            {**_row_dict(session), "attempts": _rows(db, ToneGameAttempt, session_id=session.id)}
            for session in db.scalars(
                select(ToneGameSession).where(ToneGameSession.user_id == user.id)
            ).all()
        ],
        "coach_connections": [
            {
                **_row_dict(access),
                "notes_from_coach": _rows(db, CoachNote, coach_access_id=access.id),
                "messages": _rows(db, CoachMessage, coach_access_id=access.id),
            }
            for access in db.scalars(
                select(CoachAccess).where(CoachAccess.singer_user_id == user.id)
            ).all()
        ],
    }

    coach_profile = db.scalar(select(CoachProfile).where(CoachProfile.user_id == user.id))
    if coach_profile is not None:
        export["coach_activity"] = {
            "invites_sent": _rows(db, CoachInvite, coach_id=coach_profile.id),
            "assignments_made": _rows(db, CoachAssignment, coach_id=coach_profile.id),
            "notes_authored": _rows(db, CoachNote, coach_id=coach_profile.id),
            "messages_sent": [
                _row_dict(m)
                for access in db.scalars(
                    select(CoachAccess).where(CoachAccess.coach_id == coach_profile.id)
                ).all()
                for m in db.scalars(
                    select(CoachMessage).where(
                        CoachMessage.coach_access_id == access.id,
                        CoachMessage.sender == "coach",
                    )
                ).all()
            ],
        }

    return export
