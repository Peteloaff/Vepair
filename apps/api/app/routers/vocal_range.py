from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import DailyCheckIn, User, UserProfile
from app.recovery_score import compute_and_store_recovery_score
from app.schemas_vocal_range import (
    RangeChangeOut,
    VocalRangeAttemptIn,
    VocalRangeEntryOut,
    VocalRangeSummaryOut,
)
from app.vocal_goals import get_active_goals
from app.vocal_plan import ensure_plan_exists
from app.vocal_range import build_summary, record_range_attempt

router = APIRouter(prefix="/api/v1/vocal-range", tags=["vocal-range"])


@router.post("", response_model=VocalRangeEntryOut, status_code=201)
def submit_range_attempt(
    payload: VocalRangeAttemptIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VocalRangeEntryOut:
    entry = record_range_attempt(
        db,
        current_user.id,
        payload.low_recording_id,
        payload.high_recording_id,
        payload.falsetto_recording_id,
    )
    # Stage 9: a track may have been chosen before enough data existed for a plan yet — a
    # fresh vocal-range entry is exactly the missing piece, so try again now.
    ensure_plan_exists(db, current_user.id, date.today())
    return VocalRangeEntryOut.model_validate(entry)


@router.get("/summary", response_model=VocalRangeSummaryOut)
def get_range_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> VocalRangeSummaryOut:
    # The optional stretch-target suggestion needs today's recovery signals (status + reported
    # discomfort) — reuses Stage 5's recovery score exactly as computed for the dashboard, not a
    # second implementation of the same safety checks.
    today = date.today()
    score = compute_and_store_recovery_score(db, current_user.id, today)
    checkin = db.scalar(
        select(DailyCheckIn).where(
            DailyCheckIn.user_id == current_user.id, DailyCheckIn.checkin_date == today
        )
    )
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))
    goals = get_active_goals(db, current_user.id)
    summary = build_summary(
        db,
        current_user.id,
        recovery_status=score.status,
        throat_discomfort=checkin.throat_discomfort if checkin else None,
        track=profile.track if profile else None,
        goal_high_note=goals.target_high_note,
        goal_low_note=goals.target_low_note,
    )
    return VocalRangeSummaryOut(
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
