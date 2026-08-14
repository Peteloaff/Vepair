from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas_vocal_goals import VocalGoalIn, VocalGoalOut
from app.vocal_goals import clear_manual_goals, get_active_goals, set_manual_goals

router = APIRouter(prefix="/api/v1/vocal-goals", tags=["vocal-goals"])


@router.get("", response_model=VocalGoalOut)
def get_goals(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> VocalGoalOut:
    goals = get_active_goals(db, current_user.id)
    return VocalGoalOut(**goals.__dict__)


@router.put("", response_model=VocalGoalOut)
def put_goals(
    payload: VocalGoalIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VocalGoalOut:
    row = set_manual_goals(
        db,
        current_user.id,
        payload.target_low_note,
        payload.target_avg_note,
        payload.target_high_note,
    )
    return VocalGoalOut(
        target_low_note=row.target_low_note,
        target_avg_note=row.target_avg_note,
        target_high_note=row.target_high_note,
        source=row.source,
    )


@router.delete("", status_code=204)
def delete_goals(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    clear_manual_goals(db, current_user.id)
