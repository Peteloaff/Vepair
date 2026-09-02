from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.data_export import build_user_data_export
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


@router.get("/export")
def export_my_data(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> JSONResponse:
    """Self-serve "download my data" -- see app/data_export.py for exactly what's included
    (structured data only, no raw audio bytes). A direct browser download via
    Content-Disposition, not a JSON API response a client is expected to parse."""
    export = build_user_data_export(db, current_user)
    filename = f"vepair-data-export-{datetime.now(UTC).date().isoformat()}.json"
    return JSONResponse(
        content=jsonable_encoder(export),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
