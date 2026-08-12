import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import DailyCheckIn, User
from app.schemas_checkin import CheckInCreate, CheckInOut, CheckInUpdate

router = APIRouter(prefix="/api/v1/checkins", tags=["checkins"])


def _get_owned_checkin(db: Session, current_user: User, checkin_id: uuid.UUID) -> DailyCheckIn:
    checkin = db.scalar(
        select(DailyCheckIn).where(
            DailyCheckIn.id == checkin_id, DailyCheckIn.user_id == current_user.id
        )
    )
    if checkin is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "checkin_not_found", "message": "Check-in not found."},
        )
    return checkin


@router.post("", response_model=CheckInOut, status_code=201)
def create_checkin(
    payload: CheckInCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyCheckIn:
    checkin_date = payload.checkin_date
    checkin = DailyCheckIn(
        user_id=current_user.id,
        checkin_date=checkin_date,
        **payload.model_dump(exclude={"checkin_date"}),
    )
    db.add(checkin)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "checkin_already_exists",
                "message": (
                    f"A check-in for {checkin_date.isoformat()} already exists. "
                    "Edit it instead."
                ),
            },
        ) from None
    db.refresh(checkin)
    return checkin


@router.get("", response_model=list[CheckInOut])
def list_checkins(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DailyCheckIn]:
    stmt = select(DailyCheckIn).where(DailyCheckIn.user_id == current_user.id)
    if from_date is not None:
        stmt = stmt.where(DailyCheckIn.checkin_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(DailyCheckIn.checkin_date <= to_date)
    stmt = stmt.order_by(DailyCheckIn.checkin_date.desc())
    return list(db.scalars(stmt).all())


@router.get("/{checkin_id}", response_model=CheckInOut)
def get_checkin(
    checkin_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyCheckIn:
    return _get_owned_checkin(db, current_user, checkin_id)


@router.patch("/{checkin_id}", response_model=CheckInOut)
def update_checkin(
    checkin_id: uuid.UUID,
    payload: CheckInUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyCheckIn:
    checkin = _get_owned_checkin(db, current_user, checkin_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(checkin, field, value)
    db.commit()
    db.refresh(checkin)
    return checkin
