from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas_share_progress import (
    NumericProgressOut,
    ProgressSnapshotOut,
    RangeProgressOut,
    TodaySnapshotOut,
)
from app.share_progress import (
    NumericProgress,
    ProgressSnapshot,
    RangeProgress,
    build_progress_snapshot,
    build_today_snapshot,
)

router = APIRouter(prefix="/api/v1/share-progress", tags=["share-progress"])


def _numeric_out(p: NumericProgress | None) -> NumericProgressOut | None:
    return NumericProgressOut(**vars(p)) if p is not None else None


def _range_out(r: RangeProgress | None) -> RangeProgressOut | None:
    return RangeProgressOut(**vars(r)) if r is not None else None


@router.get("/today", response_model=TodaySnapshotOut)
def get_today_snapshot(
    for_date: date = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TodaySnapshotOut:
    """Read-only — the only side effect is compute_and_store_recovery_score's existing
    today's-row upsert (unchanged from Stage 5), never a new one. `date` is required and
    client-supplied, the same reasoning as GET /api/v1/recovery-score."""
    snapshot = build_today_snapshot(db, current_user.id, for_date)
    return TodaySnapshotOut(**vars(snapshot))


@router.get("/progress", response_model=ProgressSnapshotOut)
def get_progress_snapshot(
    for_date: date = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressSnapshotOut:
    """Read-only — never recomputes or overwrites a past day's stored data; see
    app/share_progress.py's module docstring."""
    snapshot: ProgressSnapshot = build_progress_snapshot(db, current_user.id, for_date)
    return ProgressSnapshotOut(
        for_date=snapshot.for_date,
        insufficient_data=snapshot.insufficient_data,
        valid_session_count=snapshot.valid_session_count,
        comfortable_range=_range_out(snapshot.comfortable_range),
        pitch_stability_pct=_numeric_out(snapshot.pitch_stability_pct),
        vocal_endurance_seconds=_numeric_out(snapshot.vocal_endurance_seconds),
        reported_fatigue=_numeric_out(snapshot.reported_fatigue),
        days_tracked=snapshot.days_tracked,
        sessions_completed=snapshot.sessions_completed,
        training_compliance_pct=snapshot.training_compliance_pct,
    )
