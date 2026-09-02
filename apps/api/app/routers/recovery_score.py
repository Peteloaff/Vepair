from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.recovery_score import (
    RecoveryScoreResult,
    compute_and_store_recovery_score,
    fetch_score_history,
)
from app.schemas_recovery_score import (
    RecoveryScoreComponentOut,
    RecoveryScoreFactorOut,
    RecoveryScoreOut,
    ScoreHistoryPointOut,
)

router = APIRouter(prefix="/api/v1", tags=["recovery-score"])


def _to_out(result: RecoveryScoreResult) -> RecoveryScoreOut:
    return RecoveryScoreOut(
        score_date=result.score_date,
        score_value=result.score_value,
        confidence_label=result.confidence_label,
        status=result.status,
        status_label=result.status_label,
        safety_message=result.safety_message,
        components=[
            RecoveryScoreComponentOut(
                key=c.key,
                label=c.label,
                score=c.score,
                weight=c.weight,
                included=c.score is not None,
            )
            for c in result.components
        ],
        factors=[RecoveryScoreFactorOut(**f) for f in result.factors],
    )


@router.get("/recovery-score", response_model=RecoveryScoreOut)
def get_recovery_score(
    for_date: date = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecoveryScoreOut:
    """Computed fresh from the current check-in/recording/baseline data every call — always
    reflects the latest data for that date, and (per app/recovery_score.py) is fully
    deterministic given the same underlying rows. `date` is required and must be supplied by
    the client's own local date, the same reasoning as checkin_date in POST /api/v1/checkins:
    the server never assumes its own clock matches the user's "today"."""
    result = compute_and_store_recovery_score(db, current_user.id, for_date)
    return _to_out(result)


@router.get("/recovery-score/history", response_model=list[ScoreHistoryPointOut])
def get_recovery_score_history(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScoreHistoryPointOut]:
    """Stage 11: read-only over already-stored scores in the range — see
    `app/recovery_score.py`'s `fetch_score_history` for why this never backfills a day that
    was never computed."""
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
