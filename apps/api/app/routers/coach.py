import logging
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.coach_auth import get_current_coach, require_coach_access
from app.coach_notes import find_flagged_terms
from app.database import get_db
from app.exercise_routine import VALID_ROUTINE_LENGTHS_MINUTES, build_routine_for_user
from app.exercise_trends import compute_exercise_trends
from app.models import (
    CoachAccess,
    CoachAccessCategoryGrant,
    CoachAssignment,
    CoachInvite,
    CoachNote,
    CoachProfile,
    ConsentRecord,
    DailyCheckIn,
    Exercise,
    Recording,
    User,
    UserProfile,
    VoiceSession,
)
from app.recovery_score import compute_and_store_recovery_score
from app.routers.recovery_score import _to_out as _recovery_score_to_out
from app.schemas_coach import (
    CoachAssignmentCreate,
    CoachAssignmentOut,
    CoachExerciseCreate,
    CoachInviteCreate,
    CoachInviteOut,
    CoachNoteCreate,
    CoachNoteOut,
    CoachProfileOut,
    CoachSingerListItemOut,
    CoachSingerSummaryOut,
    CoachVoiceSessionOut,
)
from app.schemas_exercise import ExerciseOut, RoutineOut
from app.schemas_exercise_trend import ExerciseTrendOut
from app.schemas_recording import RecordingOut
from app.schemas_training_consistency import ConsistencyDayOut, TrainingConsistencyOut
from app.schemas_vocal_range import RangeChangeOut, VocalRangeSummaryOut
from app.storage import get_storage
from app.training_consistency import build_training_consistency
from app.vocal_range import build_summary

logger = logging.getLogger("vepair.coach")

router = APIRouter(prefix="/api/v1/coach", tags=["coach"])


@router.get("/profile", response_model=CoachProfileOut)
def get_coach_profile(coach: CoachProfile = Depends(get_current_coach)) -> CoachProfile:
    return coach


@router.post("/exercises", response_model=ExerciseOut, status_code=201)
def create_coach_exercise(
    payload: CoachExerciseCreate,
    coach: CoachProfile = Depends(get_current_coach),
    db: Session = Depends(get_db),
) -> Exercise:
    """A coach-authored exercise. Immediately active and immediately eligible for the general
    adaptive routine pool used by every user, not just this coach's own singers -- the
    category whitelist (CoachExerciseCreate's validator) is what keeps it inside the same
    intensity-cap safety gate as every seed exercise; there is no separate review step."""
    exercise = Exercise(
        name=payload.name,
        category=payload.category,
        purpose=payload.purpose or f"A custom exercise added by {coach.display_name}.",
        instructions=payload.instructions,
        duration_seconds=payload.duration_seconds,
        difficulty=payload.difficulty,
        expected_result="As described by your coach.",
        is_active=True,
        created_by_coach_id=coach.id,
    )
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.get("/exercises", response_model=list[ExerciseOut])
def list_coach_exercises(
    coach: CoachProfile = Depends(get_current_coach), db: Session = Depends(get_db)
) -> list[Exercise]:
    """This coach's own created exercises only -- for managing/reviewing what they've added, not
    a general library browse (GET /api/v1/exercises already covers the full active library,
    including these once created)."""
    return list(
        db.scalars(
            select(Exercise)
            .where(Exercise.created_by_coach_id == coach.id)
            .order_by(Exercise.created_at.desc())
        ).all()
    )


@router.post("/invites", response_model=CoachInviteOut, status_code=201)
def create_invite(
    payload: CoachInviteCreate,
    coach: CoachProfile = Depends(get_current_coach),
    db: Session = Depends(get_db),
) -> CoachInviteOut:
    singer = db.scalar(select(User).where(User.email == payload.singer_email.lower()))
    if singer is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "singer_not_found",
                "message": (
                    "No VepAIr account exists for this email yet — ask them to sign up first."
                ),
            },
        )

    existing = db.scalar(
        select(CoachInvite).where(
            CoachInvite.coach_id == coach.id,
            CoachInvite.singer_user_id == singer.id,
            CoachInvite.status == "pending",
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invite_already_pending",
                "message": "An invite to this singer is already pending.",
            },
        )

    invite = CoachInvite(coach_id=coach.id, singer_user_id=singer.id, message=payload.message)
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return CoachInviteOut(
        id=invite.id,
        singer_email=singer.email,
        status=invite.status,
        message=invite.message,
        created_at=invite.created_at,
        responded_at=invite.responded_at,
    )


@router.get("/invites", response_model=list[CoachInviteOut])
def list_sent_invites(
    coach: CoachProfile = Depends(get_current_coach), db: Session = Depends(get_db)
) -> list[CoachInviteOut]:
    rows = db.execute(
        select(CoachInvite, User.email)
        .join(User, User.id == CoachInvite.singer_user_id)
        .where(CoachInvite.coach_id == coach.id)
        .order_by(CoachInvite.created_at.desc())
    ).all()
    return [
        CoachInviteOut(
            id=invite.id,
            singer_email=email,
            status=invite.status,
            message=invite.message,
            created_at=invite.created_at,
            responded_at=invite.responded_at,
        )
        for invite, email in rows
    ]


@router.delete("/invites/{invite_id}", status_code=204)
def cancel_invite(
    invite_id: uuid.UUID,
    coach: CoachProfile = Depends(get_current_coach),
    db: Session = Depends(get_db),
) -> None:
    invite = db.scalar(
        select(CoachInvite).where(
            CoachInvite.id == invite_id, CoachInvite.coach_id == coach.id
        )
    )
    if invite is None:
        raise HTTPException(
            status_code=404, detail={"code": "invite_not_found", "message": "Invite not found."}
        )
    if invite.status != "pending":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invite_not_pending",
                "message": "Only pending invites can be cancelled.",
            },
        )
    invite.status = "revoked"
    db.commit()


@router.get("/singers", response_model=list[CoachSingerListItemOut])
def list_my_singers(
    coach: CoachProfile = Depends(get_current_coach), db: Session = Depends(get_db)
) -> list[CoachSingerListItemOut]:
    rows = db.execute(
        select(CoachAccess, User.email)
        .join(User, User.id == CoachAccess.singer_user_id)
        .where(CoachAccess.coach_id == coach.id, CoachAccess.status == "active")
        .order_by(CoachAccess.granted_at.desc())
    ).all()
    return [
        CoachSingerListItemOut(
            singer_user_id=access.singer_user_id,
            singer_email=email,
            coach_access_id=access.id,
            granted_categories=sorted(_granted_categories(db, access)),
            granted_at=access.granted_at,
        )
        for access, email in rows
    ]


def _granted_categories(db: Session, access: CoachAccess) -> set[str]:
    grants = db.scalars(
        select(CoachAccessCategoryGrant.category).where(
            CoachAccessCategoryGrant.coach_access_id == access.id,
            CoachAccessCategoryGrant.granted.is_(True),
        )
    ).all()
    return set(grants)


@router.delete("/singers/{singer_user_id}", status_code=204)
def remove_singer(
    access: CoachAccess = Depends(require_coach_access()),
    db: Session = Depends(get_db),
) -> None:
    """Coach-initiated disconnect — the mirror of the singer's own
    DELETE /api/v1/coach-connections/{id} (app/routers/coach_access.py), just from the other
    side. Same semantics: immediate for future access (the coach's own next request 403s, since
    require_coach_access checks CoachAccess.status == "active"), forward-only for the past
    (CoachAssignment/CoachNote rows are never deleted, and the singer keeps permanent read
    access to notes already written about them). The singer's account and all their own data
    are untouched — this only ends the coach's access to it."""
    access.status = "revoked"
    access.revoked_at = datetime.now(UTC)
    access.revoked_by = "coach"

    grants = db.scalars(
        select(CoachAccessCategoryGrant).where(
            CoachAccessCategoryGrant.coach_access_id == access.id,
            CoachAccessCategoryGrant.granted.is_(True),
        )
    ).all()
    for grant in grants:
        db.add(
            ConsentRecord(
                user_id=access.singer_user_id,
                consent_type="coach_sharing",
                category=grant.category,
                granted=False,
                granted_at=func.clock_timestamp(),
                clinician_id=access.coach_id,
            )
        )
    db.commit()


@router.get("/singers/{singer_user_id}/summary", response_model=CoachSingerSummaryOut)
def get_singer_summary(
    singer_user_id: uuid.UUID,
    for_date: date = Query(..., alias="date"),
    length_minutes: int = Query(10),
    access: CoachAccess = Depends(require_coach_access()),
    db: Session = Depends(get_db),
) -> CoachSingerSummaryOut:
    """Every section below is built by calling the exact same pure functions and response
    schemas the singer's own endpoints use (app/routers/recovery_score.py,
    app/routers/vocal_range.py, app/routers/exercises.py) — parameterized by singer_user_id
    instead of the caller's own id. None of those functions read `current_user` internally, so
    this requires zero changes to any of them. See test_coach_access.py's
    test_coach_dashboard_recovery_score_matches_singers_own_endpoint for the regression test
    that enforces this stays true.

    Each field is populated only if the singer granted that specific category — never a
    blanket single-category gate on the whole endpoint (see require_coach_access() above,
    called with no category, which only proves *some* active access exists)."""
    if length_minutes not in VALID_ROUTINE_LENGTHS_MINUTES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_length_minutes",
                "message": f"length_minutes must be one of {VALID_ROUTINE_LENGTHS_MINUTES}.",
            },
        )

    granted = _granted_categories(db, access)

    # Computed at most once and reused — compute_and_store_recovery_score is idempotent
    # (upserts the same row), but there's no reason to call it twice in one request.
    recovery_result = None
    if "recovery_trends" in granted or "vocal_range" in granted:
        recovery_result = compute_and_store_recovery_score(db, singer_user_id, for_date)

    recovery_score_out = None
    if "recovery_trends" in granted:
        recovery_score_out = _recovery_score_to_out(recovery_result)

    vocal_range_out = None
    if "vocal_range" in granted:
        checkin = db.scalar(
            select(DailyCheckIn).where(
                DailyCheckIn.user_id == singer_user_id, DailyCheckIn.checkin_date == for_date
            )
        )
        profile = db.scalar(select(UserProfile).where(UserProfile.user_id == singer_user_id))
        summary = build_summary(
            db,
            singer_user_id,
            recovery_status=recovery_result.status,
            throat_discomfort=checkin.throat_discomfort if checkin else None,
            track=profile.track if profile else None,
        )
        vocal_range_out = VocalRangeSummaryOut(
            current_low_note=summary.current_low_note,
            current_high_note=summary.current_high_note,
            current_falsetto_note=summary.current_falsetto_note,
            historical_best_low_note=summary.historical_best_low_note,
            historical_best_high_note=summary.historical_best_high_note,
            change_30d_high=RangeChangeOut(**summary.change_30d_high.__dict__),
            change_90d_high=RangeChangeOut(**summary.change_90d_high.__dict__),
            change_30d_low=RangeChangeOut(**summary.change_30d_low.__dict__),
            change_90d_low=RangeChangeOut(**summary.change_90d_low.__dict__),
            history=summary.history,
            stretch_target_note=summary.stretch_target_note,
            stretch_target_reason=summary.stretch_target_reason,
            stretch_target_low_note=summary.stretch_target_low_note,
            stretch_target_low_reason=summary.stretch_target_low_reason,
        )

    exercise_trends_out = None
    todays_routine_out = None
    if "exercise_history" in granted:
        trends = compute_exercise_trends(db, singer_user_id)
        exercise_trends_out = [
            ExerciseTrendOut(
                exercise_id=t.exercise_id,
                exercise_name=t.exercise_name,
                metric_name=t.metric_name,
                direction=t.direction,
                recent_median=t.recent_median,
                prior_median=t.prior_median,
                attempt_count=t.attempt_count,
            )
            for t in trends
        ]

        routine_result = build_routine_for_user(db, singer_user_id, length_minutes, for_date)
        todays_routine_out = RoutineOut(
            length_minutes=routine_result.length_minutes,
            intensity_cap=routine_result.intensity_cap,
            total_duration_seconds=routine_result.total_duration_seconds,
            safety_message=routine_result.safety_message,
            reasons=routine_result.reasons,
            items=[
                ExerciseOut(audio_demo_url=None, **vars(item)) for item in routine_result.items
            ],
            assigned_exercise_ids=routine_result.assigned_exercise_ids,
        )

        consistency = build_training_consistency(
            db, singer_user_id, for_date, for_date, for_date
        )
        training_consistency_out = TrainingConsistencyOut(
            days=[
                ConsistencyDayOut(for_date=d.for_date, sessions_completed=d.sessions_completed)
                for d in consistency.days
            ],
            current_streak_days=consistency.current_streak_days,
            longest_streak_days=consistency.longest_streak_days,
            total_sessions_in_range=consistency.total_sessions_in_range,
        )
    else:
        training_consistency_out = None

    return CoachSingerSummaryOut(
        singer_id=singer_user_id,
        granted_categories=sorted(granted),
        recovery_score=recovery_score_out,
        vocal_range=vocal_range_out,
        exercise_trends=exercise_trends_out,
        training_consistency=training_consistency_out,
        todays_routine=todays_routine_out,
    )


@router.get(
    "/singers/{singer_user_id}/recordings", response_model=list[CoachVoiceSessionOut]
)
def list_singer_recordings(
    singer_user_id: uuid.UUID,
    access: CoachAccess = Depends(require_coach_access(category="recordings")),
    db: Session = Depends(get_db),
) -> list[CoachVoiceSessionOut]:
    sessions = db.scalars(
        select(VoiceSession)
        .where(VoiceSession.user_id == singer_user_id)
        .order_by(VoiceSession.started_at.desc())
    ).all()
    return [
        CoachVoiceSessionOut(
            id=s.id,
            started_at=s.started_at,
            completed_at=s.completed_at,
            device_metadata_id=s.device_metadata_id,
            recordings=[RecordingOut.model_validate(r) for r in s.recordings],
        )
        for s in sessions
    ]


@router.get("/singers/{singer_user_id}/recordings/{recording_id}/audio")
def get_singer_recording_audio(
    singer_user_id: uuid.UUID,
    recording_id: uuid.UUID,
    access: CoachAccess = Depends(require_coach_access(category="recordings")),
    db: Session = Depends(get_db),
) -> Response:
    """Deliberately a live link into the singer's own stored copy, never a separate one made
    for the coach — there is exactly one copy of this recording anywhere, ever, and it's the
    singer's. Nothing is downloaded or cached server-side for the coach, and access is gated
    entirely by the existing "recordings" category grant (require_coach_access): revoke that
    category, or the connection outright, and this 403s on the coach's very next request. See
    PRIVACY.md section 3's coach-recordings retention note."""
    recording = db.scalar(
        select(Recording)
        .join(VoiceSession)
        .where(Recording.id == recording_id, VoiceSession.user_id == singer_user_id)
    )
    if recording is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "recording_not_found", "message": "Recording not found."},
        )

    # Audit trail (PRIVACY.md section 4's "auditable access" requirement) — a structured log
    # line is the right amount of tooling for pilot scale; a queryable audit table is
    # explicitly deferred to the future admin backend (see ROADMAP.md Stage 12).
    logger.info(
        "coach_recording_access coach_id=%s singer_user_id=%s recording_id=%s",
        access.coach_id,
        singer_user_id,
        recording_id,
    )

    audio_bytes = get_storage().read(recording.file_path)
    return Response(content=audio_bytes, media_type="audio/wav")


@router.post(
    "/singers/{singer_user_id}/assignments", response_model=CoachAssignmentOut, status_code=201
)
def create_assignment(
    singer_user_id: uuid.UUID,
    payload: CoachAssignmentCreate,
    access: CoachAccess = Depends(require_coach_access()),
    db: Session = Depends(get_db),
) -> CoachAssignment:
    """Not category-gated — assigning training is the coach acting, not reading a data
    category, so only active access is required (see require_coach_access() with no
    category). Safety enforcement itself lives entirely in app/exercise_routine.py, not here —
    an assignment is just a list of exercise ids; whether any of them actually make it into a
    given day's routine is decided fresh every day against that day's real intensity cap."""
    existing_ids = set(
        db.scalars(
            select(Exercise.id).where(
                Exercise.id.in_(payload.exercise_ids), Exercise.is_active.is_(True)
            )
        ).all()
    )
    unknown = set(payload.exercise_ids) - existing_ids
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unknown_exercise_ids",
                "message": f"Unknown or inactive exercise ids: {sorted(str(i) for i in unknown)}",
            },
        )

    prior_active = db.scalars(
        select(CoachAssignment).where(
            CoachAssignment.singer_user_id == singer_user_id,
            CoachAssignment.status == "active",
        )
    ).all()
    for prior in prior_active:
        prior.status = "superseded"

    assignment = CoachAssignment(
        coach_id=access.coach_id,
        singer_user_id=singer_user_id,
        coach_access_id=access.id,
        exercise_ids=[str(eid) for eid in payload.exercise_ids],
        note_to_singer=payload.note_to_singer,
        status="active",
        exercise_tone_targets=(
            {str(eid): note for eid, note in payload.exercise_tone_targets.items()}
            if payload.exercise_tone_targets
            else None
        ),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/singers/{singer_user_id}/assignments", response_model=list[CoachAssignmentOut])
def list_assignments(
    singer_user_id: uuid.UUID,
    access: CoachAccess = Depends(require_coach_access()),
    db: Session = Depends(get_db),
) -> list[CoachAssignment]:
    return list(
        db.scalars(
            select(CoachAssignment)
            .where(CoachAssignment.singer_user_id == singer_user_id)
            .order_by(CoachAssignment.created_at.desc())
        ).all()
    )


@router.post("/singers/{singer_user_id}/notes", response_model=CoachNoteOut, status_code=201)
def create_note(
    singer_user_id: uuid.UUID,
    payload: CoachNoteCreate,
    access: CoachAccess = Depends(require_coach_access()),
    db: Session = Depends(get_db),
) -> CoachNote:
    """Not category-gated, same reasoning as assignments — writing is the coach acting, not
    reading a data category. The note always saves regardless of flagged_terms (see
    app/coach_notes.py) — this is a review signal, not a block, since legitimate escalation
    language ("consider seeing an ENT") is exactly what MEDICAL_SAFETY.md wants and must never
    be prevented. For pilot scale, review flagged notes with:
    `SELECT * FROM coach_notes WHERE flagged_terms IS NOT NULL AND deleted_at IS NULL;`
    — real moderation tooling is explicitly deferred to the future admin backend
    (ROADMAP.md Stage 12)."""
    note = CoachNote(
        coach_id=access.coach_id,
        singer_user_id=singer_user_id,
        coach_access_id=access.id,
        body=payload.body,
        flagged_terms=find_flagged_terms(payload.body) or None,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/singers/{singer_user_id}/notes", response_model=list[CoachNoteOut])
def list_notes_for_singer(
    singer_user_id: uuid.UUID,
    access: CoachAccess = Depends(require_coach_access()),
    db: Session = Depends(get_db),
) -> list[CoachNote]:
    return list(
        db.scalars(
            select(CoachNote)
            .where(
                CoachNote.singer_user_id == singer_user_id,
                CoachNote.coach_id == access.coach_id,
                CoachNote.deleted_at.is_(None),
            )
            .order_by(CoachNote.created_at.desc())
        ).all()
    )


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: uuid.UUID,
    coach: CoachProfile = Depends(get_current_coach),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete only — the row is retained (deleted_at set) so the audit trail survives,
    same as every other append-only record in this feature. Only the authoring coach may
    delete their own note."""
    note = db.scalar(
        select(CoachNote).where(CoachNote.id == note_id, CoachNote.coach_id == coach.id)
    )
    if note is None:
        raise HTTPException(
            status_code=404, detail={"code": "note_not_found", "message": "Note not found."}
        )
    if note.deleted_at is None:
        note.deleted_at = datetime.now(UTC)
        db.commit()
