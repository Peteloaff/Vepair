from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, UserProfile
from app.schemas_profile import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserProfile:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "profile_not_found",
                "message": "Onboarding has not been completed yet.",
            },
        )
    return profile


@router.put("", response_model=ProfileOut)
def upsert_profile(
    payload: ProfileIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Full replace: the client must send the whole profile. Omitted fields are cleared,
    not left unchanged — the frontend always submits the complete onboarding form state."""
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))
    if profile is None:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in payload.model_dump().items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile
