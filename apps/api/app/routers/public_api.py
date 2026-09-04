"""The read-only public API (`/api/public/v1/*`) -- a personal-access-token-gated surface for
pulling a user's own VepAIr data into external tools. Kept in its own versioned namespace,
separate from `/api/v1` (the internal namespace the web app itself calls), so future internal
refactors never become a breaking change for whatever's on the other end of a token. See
app/api_token_auth.py for the auth/scope/rate-limit machinery and PRIVACY.md for why raw audio
and check-in free text are never reachable here.

Every endpoint reuses the exact same pure functions the singer's own dashboard and the coach
portal already call (compute_and_store_recovery_score, build_summary, compute_exercise_trends)
-- one shared Voice Intelligence engine, not a parallel implementation for this surface."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_token_auth import require_api_scope
from app.database import get_db
from app.exercise_trends import compute_exercise_trends
from app.models import DailyCheckIn, User, UserProfile
from app.recovery_score import compute_and_store_recovery_score, fetch_score_history
from app.routers.recovery_score import _to_out as _recovery_score_to_out
from app.schemas_exercise_trend import ExerciseTrendOut
from app.schemas_recovery_score import RecoveryScoreOut, ScoreHistoryPointOut
from app.schemas_vocal_range import RangeChangeOut, VocalRangeSummaryOut
from app.vocal_goals import get_active_goals
from app.vocal_range import build_summary

router = APIRouter(prefix="/api/public/v1", tags=["public-api"])


@router.get("/recovery-score", response_model=RecoveryScoreOut)
def get_recovery_score(
    for_date: date = Query(default_factory=date.today, alias="date"),
    current_user: User = Depends(require_api_scope("recovery_trends")),
    db: Session = Depends(get_db),
) -> RecoveryScoreOut:
    result = compute_and_store_recovery_score(db, current_user.id, for_date)
    return _recovery_score_to_out(result)


@router.get("/recovery-score/history", response_model=list[ScoreHistoryPointOut])
def get_recovery_score_history(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: User = Depends(require_api_scope("recovery_trends")),
    db: Session = Depends(get_db),
) -> list[ScoreHistoryPointOut]:
    history = fetch_score_history(db, current_user.id, from_date, to_date)
    return [
        ScoreHistoryPointOut(
            score_date=p.score_date,
            score_value=p.score_value,
            confidence_label=p.confidence_label,
            status=p.status,
            acoustic_stability_score=p.acoustic_stability_score,
        )
        for p in history
    ]


@router.get("/vocal-range", response_model=VocalRangeSummaryOut)
def get_vocal_range(
    current_user: User = Depends(require_api_scope("vocal_range")),
    db: Session = Depends(get_db),
) -> VocalRangeSummaryOut:
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


@router.get("/exercise-trends", response_model=list[ExerciseTrendOut])
def get_exercise_trends(
    current_user: User = Depends(require_api_scope("exercise_history")),
    db: Session = Depends(get_db),
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
