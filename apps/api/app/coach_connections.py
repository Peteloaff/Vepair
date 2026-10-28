"""The two coach/Vrotégé connection actions that more than one caller performs, kept in one
place so a coach acting for themselves and an organization admin acting for a coach behave
identically: sending an invite, and ending a connection.

Neither function commits -- callers add their own bookkeeping and commit once. Neither ever
reads a Vrotégé's data; ending a connection only closes the coach's access."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    CoachAccess,
    CoachAccessCategoryGrant,
    CoachInvite,
    CoachProfile,
    ConsentRecord,
    User,
)


def new_invite(
    db: Session, coach: CoachProfile, singer_email: str, message: str | None
) -> tuple[CoachInvite, bool]:
    """Creates a pending invite from `coach`. The invitee doesn't need an account yet: if one
    exists the invite is linked to it now, otherwise it's emailed as a sign-up invitation and
    linked when they sign up. Returns (invite, invitee_has_an_account)."""
    email = singer_email.lower()
    singer = db.scalar(select(User).where(User.email == email))

    existing = db.scalar(
        select(CoachInvite).where(
            CoachInvite.coach_id == coach.id,
            CoachInvite.singer_email == email,
            CoachInvite.status == "pending",
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "invite_already_pending",
                "message": "An invite to this Vrotégé is already pending.",
            },
        )

    invite = CoachInvite(
        coach_id=coach.id,
        singer_user_id=singer.id if singer is not None else None,
        singer_email=email,
        message=message,
    )
    db.add(invite)
    db.flush()
    return invite, singer is not None


def end_connection(db: Session, access: CoachAccess, revoked_by: str) -> None:
    """Closes a coach's access to a Vrotégé -- immediate for future access, forward-only for the
    past (notes, assignments and messages are never deleted, and the Vrotégé keeps permanent
    read access to notes already written about them). The Vrotégé's own account and data are
    untouched. `revoked_by` is "coach" or "org_admin" (the column holds up to 10 characters)."""
    access.status = "revoked"
    access.revoked_at = datetime.now(UTC)
    access.revoked_by = revoked_by

    grants = db.scalars(
        select(CoachAccessCategoryGrant).where(
            CoachAccessCategoryGrant.coach_access_id == access.id,
            CoachAccessCategoryGrant.granted.is_(True),
        )
    ).all()
    for grant in grants:
        db.add(
            ConsentRecord(
                user_id=access.singer_user_id,
                consent_type="coach_sharing",
                category=grant.category,
                granted=False,
                granted_at=func.clock_timestamp(),
                clinician_id=access.coach_id,
            )
        )
