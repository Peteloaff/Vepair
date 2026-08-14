import json
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.exercise_audio import analyze_exercise_attempt
from app.exercise_routine import (
    VALID_ROUTINE_LENGTHS_MINUTES,
    build_routine_for_user,
    check_rest_day_for_user,
)
from app.exercise_trends import compute_exercise_trends
from app.models import Exercise, ExerciseResult, ExerciseSession, User
from app.schemas_exercise import (
    ExerciseOut,
    ExerciseResultOut,
    ExerciseSessionCreate,
    ExerciseSessionOut,
    ExerciseSessionWithResultsOut,
    RestCheckOut,
    RoutineOut,
)
from app.schemas_exercise_trend import ExerciseTrendOut

router = APIRouter(prefix="/api/v1", tags=["exercises"])


def _get_owned_session(
    db: Session, current_user: User, session_id: uuid.UUID
) -> ExerciseSession:
    session = db.scalar(
        select(ExerciseSession).where(
            ExerciseSession.id == session_id, ExerciseSession.user_id == current_user.id
        )
    )
    if session is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "exercise_session_not_found",
                "message": "Exercise session not found.",
            },
        )
    return session


@router.get("/exercises", response_model=list[ExerciseOut])
def list_exercises(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Exercise]:
    stmt = select(Exercise).where(Exercise.is_active.is_(True)).order_by(Exercise.category)
    return list(db.scalars(stmt).all())


@router.get("/exercise-trends", response_model=list[ExerciseTrendOut])
def get_exercise_trends(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ExerciseTrendOut]:
    trends = compute_exercise_trends(db, current_user.id)
    return [
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


@router.get("/routine", response_model=RoutineOut)
def get_routine(
    length_minutes: int = Query(...),
    for_date: date = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoutineOut:
    if length_minutes not in VALID_ROUTINE_LENGTHS_MINUTES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_length_minutes",
                "message": f"length_minutes must be one of {VALID_ROUTINE_LENGTHS_MINUTES}.",
            },
        )
    result = build_routine_for_user(db, current_user.id, length_minutes, for_date)
    return RoutineOut(
        length_minutes=result.length_minutes,
        intensity_cap=result.intensity_cap,
        total_duration_seconds=result.total_duration_seconds,
        safety_message=result.safety_message,
        reasons=result.reasons,
        items=[ExerciseOut(audio_demo_url=None, **vars(item)) for item in result.items],
        assigned_exercise_ids=result.assigned_exercise_ids,
        rest_day_recommended=result.rest_day_recommended,
        rest_day_reason=result.rest_day_reason,
        exercise_tone_targets=result.exercise_tone_targets,
    )


@router.get("/routine/rest-check", response_model=RestCheckOut)
def get_rest_check(
    for_date: date = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RestCheckOut:
    recommended, reason = check_rest_day_for_user(db, current_user.id, for_date)
    return RestCheckOut(rest_day_recommended=recommended, rest_day_reason=reason)


@router.post("/exercise-sessions", response_model=ExerciseSessionOut, status_code=201)
def create_exercise_session(
    payload: ExerciseSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseSession:
    session = ExerciseSession(
        user_id=current_user.id, routine_length_minutes=payload.routine_length_minutes
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/exercise-sessions", response_model=list[ExerciseSessionOut])
def list_exercise_sessions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ExerciseSession]:
    stmt = (
        select(ExerciseSession)
        .where(ExerciseSession.user_id == current_user.id)
        .order_by(ExerciseSession.started_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/exercise-sessions/{session_id}", response_model=ExerciseSessionWithResultsOut)
def get_exercise_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseSession:
    return _get_owned_session(db, current_user, session_id)


@router.post(
    "/exercise-sessions/{session_id}/results", response_model=ExerciseResultOut, status_code=201
)
async def log_exercise_result(
    session_id: uuid.UUID,
    exercise_id: uuid.UUID = Form(...),
    order_index: int = Form(...),
    completed: bool = Form(...),
    self_reported_difficulty: int | None = Form(default=None),
    # Stage 7's live-coaching telemetry (voiced_ratio, frame_count, average_analysis_latency_ms)
    # as a JSON-encoded string — multipart form fields are always strings/files, never nested
    # JSON, the same reason Stage 2's recording upload uses Form fields throughout.
    live_measured_result: str | None = Form(default=None),
    # Stage 8: optional exercise audio, analyzed in-memory and never stored — see
    # app/exercise_audio.py. Only meaningful for exercises with a target_measurement; omitted
    # entirely for Breathing or when the microphone wasn't available.
    audio: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseResult:
    session = _get_owned_session(db, current_user, session_id)
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "exercise_not_found", "message": "Exercise not found."},
        )

    if self_reported_difficulty is not None and not (1 <= self_reported_difficulty <= 10):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_self_reported_difficulty",
                "message": "self_reported_difficulty must be between 1 and 10.",
            },
        )

    live_telemetry = json.loads(live_measured_result) if live_measured_result else None
    acoustic_measurement = None
    if audio is not None:
        audio_bytes = await audio.read()
        acoustic_measurement = analyze_exercise_attempt(audio_bytes, exercise.category)

    measured_result = None
    if live_telemetry is not None or acoustic_measurement is not None:
        measured_result = {"live": live_telemetry, "acoustic": acoustic_measurement}

    result = ExerciseResult(
        exercise_session_id=session.id,
        exercise_id=exercise_id,
        order_index=order_index,
        completed=completed,
        self_reported_difficulty=self_reported_difficulty,
        measured_result=measured_result,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.patch("/exercise-sessions/{session_id}/complete", response_model=ExerciseSessionOut)
def complete_exercise_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseSession:
    session = _get_owned_session(db, current_user, session_id)
    session.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(session)
    return session
