from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ConsentRecord, User
from app.schemas_consent import VALID_CONSENT_TYPES, ConsentIn, ConsentOut

router = APIRouter(prefix="/api/v1/consent", tags=["consent"])


def _validate_type(consent_type: str) -> None:
    if consent_type not in VALID_CONSENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_consent_type",
                "message": f"consent_type must be one of {sorted(VALID_CONSENT_TYPES)}",
            },
        )


@router.get("/{consent_type}", response_model=ConsentOut)
def get_consent(
    consent_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentOut:
    _validate_type(consent_type)
    latest = db.scalar(
        select(ConsentRecord)
        .where(
            ConsentRecord.user_id == current_user.id,
            ConsentRecord.consent_type == consent_type,
        )
        .order_by(ConsentRecord.granted_at.desc())
        .limit(1)
    )
    if latest is None:
        return ConsentOut(consent_type=consent_type, granted=None, granted_at=None)
    return ConsentOut(
        consent_type=consent_type, granted=latest.granted, granted_at=latest.granted_at
    )


@router.put("/{consent_type}", response_model=ConsentOut)
def set_consent(
    consent_type: str,
    payload: ConsentIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentOut:
    """Every call inserts a new, timestamped row rather than updating one in place — see
    PRIVACY.md section 4's "auditable access" principle: the full history of what a user
    decided, and when, must never be silently overwritten by a later change of mind.

    granted_at uses clock_timestamp() rather than the TimestampMixin default (now(), which
    is frozen to transaction-start time in Postgres) — two consent changes in quick
    succession must still be orderable, not tied to the same value."""
    _validate_type(consent_type)
    record = ConsentRecord(
        user_id=current_user.id,
        consent_type=consent_type,
        granted=payload.granted,
        granted_at=func.clock_timestamp(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ConsentOut(
        consent_type=consent_type, granted=record.granted, granted_at=record.granted_at
    )
