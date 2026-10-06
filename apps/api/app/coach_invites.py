"""Coach invites addressed to an email that may not have an account yet."""

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import CoachInvite, User


def attach_pending_invites(db: Session, user: User) -> None:
    """Links every still-unclaimed invite addressed to this user's email to their new account, so
    an invitee who signs up from the invitation email finds the invite waiting. Does not commit
    -- the caller's own signup transaction does."""
    db.execute(
        update(CoachInvite)
        .where(
            CoachInvite.singer_email == user.email.lower(),
            CoachInvite.singer_user_id.is_(None),
        )
        .values(singer_user_id=user.id)
    )
