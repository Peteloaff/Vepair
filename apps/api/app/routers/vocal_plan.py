from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, UserProfile
from app.schemas_vocal_plan import (
    ReadinessOut,
    TrackIn,
    TrackSetOut,
    VocalPlanOut,
    VocalPlanViewOut,
)
from app.vocal_plan import TRACKS, get_active_plan, sync_plan_to_track

router = APIRouter(prefix="/api/v1", tags=["vocal-plan"])

PLAN_PENDING_REASON = (
    "We'll build your 90-day plan as soon as we have a recent recording and a vocal range "
    "test to base it on — head over to Record or Vocal Range to get started."
)


@router.patch("/profile/track", response_model=TrackSetOut)
def set_track(
    payload: TrackIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrackSetOut:
    if payload.track not in TRACKS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_track",
                "message": f"track must be one of {TRACKS}",
            },
        )

    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "profile_not_found",
                "message": "Complete onboarding before choosing a track.",
            },
        )

    profile.track = payload.track
    db.commit()

    plan = sync_plan_to_track(db, current_user.id, payload.track, date.today())
    return TrackSetOut(
        track=payload.track,
        plan=VocalPlanOut.model_validate(plan) if plan else None,
        plan_pending_reason=None if plan else PLAN_PENDING_REASON,
    )


@router.get("/vocal-plan", response_model=VocalPlanViewOut)
def get_plan(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> VocalPlanViewOut:
    view = get_active_plan(db, current_user.id, date.today())
    return VocalPlanViewOut(
        plan=VocalPlanOut.model_validate(view.plan) if view.plan else None,
        readiness=(
            ReadinessOut(ready=view.readiness.ready, reasons=view.readiness.reasons)
            if view.readiness
            else None
        ),
        just_graduated=view.just_graduated,
    )
