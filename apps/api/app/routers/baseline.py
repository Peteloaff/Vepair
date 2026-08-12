from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.baseline import (
    VOICE_METRICS,
    compute_fatigue_baseline,
    confidence_from_session_count,
    usable_voice_session_count,
)
from app.database import get_db
from app.models import Baseline, User
from app.schemas_baseline import BaselineOut, BaselineSummaryOut

router = APIRouter(prefix="/api/v1", tags=["baseline"])


@router.get("/baseline", response_model=BaselineSummaryOut)
def get_baseline_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> BaselineSummaryOut:
    stored = {
        b.metric_name: b
        for b in db.scalars(select(Baseline).where(Baseline.user_id == current_user.id)).all()
    }

    voice_baselines = [
        BaselineOut.model_validate(stored[m]) for m in VOICE_METRICS if m in stored
    ]

    session_count = usable_voice_session_count(db, current_user.id)
    confidence_pct, confidence_label = confidence_from_session_count(session_count)

    fatigue_stats = compute_fatigue_baseline(db, current_user.id)
    fatigue_confidence_pct, fatigue_confidence_label = confidence_from_session_count(
        fatigue_stats.sample_count
    )
    fatigue_out = (
        BaselineOut(
            metric_name="fatigue",
            median_value=fatigue_stats.median_value,
            mad_value=fatigue_stats.mad_value,
            sample_count=fatigue_stats.sample_count,
            confidence_pct=fatigue_confidence_pct,
            confidence_label=fatigue_confidence_label,
            window_start=fatigue_stats.window_start,
            window_end=fatigue_stats.window_end,
        )
        if fatigue_stats.sample_count > 0
        else None
    )

    return BaselineSummaryOut(
        voice_baselines=voice_baselines,
        voice_confidence_pct=confidence_pct,
        voice_confidence_label=confidence_label,
        usable_session_count=session_count,
        fatigue_baseline=fatigue_out,
    )
