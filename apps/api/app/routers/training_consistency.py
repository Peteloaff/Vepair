from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas_training_consistency import ConsistencyDayOut, TrainingConsistencyOut
from app.training_consistency import build_training_consistency

router = APIRouter(prefix="/api/v1", tags=["training-consistency"])


@router.get("/training-consistency", response_model=TrainingConsistencyOut)
def get_training_consistency(
    from_date: date = Query(...),
    to_date: date = Query(...),
    as_of: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingConsistencyOut:
    """`as_of` is the client's own local "today" — required and client-supplied, the same
    reasoning as every other date param in this app: the server never assumes its clock matches
    the user's. Streaks are always computed from full history, not clipped to
    `from_date`/`to_date` — see `app/training_consistency.py`."""
    consistency = build_training_consistency(db, current_user.id, from_date, to_date, as_of)
    return TrainingConsistencyOut(
        days=[
            ConsistencyDayOut(for_date=d.for_date, sessions_completed=d.sessions_completed)
            for d in consistency.days
        ],
        current_streak_days=consistency.current_streak_days,
        longest_streak_days=consistency.longest_streak_days,
        total_sessions_in_range=consistency.total_sessions_in_range,
    )
