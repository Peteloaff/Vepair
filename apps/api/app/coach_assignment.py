"""Stage 12 Phase II. Resolves whether a coach's exercise assignment should influence today's
routine — a pure lookup layered on top of app/exercise_routine.py's existing signal-gathering in
build_routine_for_user, never a second routine-generation path."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CoachAccess, CoachAssignment


def get_active_assigned_exercise_ids(
    db: Session, singer_user_id: uuid.UUID
) -> list[uuid.UUID] | None:
    """None unless there is BOTH an active CoachAssignment AND its linked CoachAccess is still
    active — revoking access silently stops an assignment's influence on future routines
    without deleting the assignment's own history row. CoachAssignment.status
    (active/superseded) tracks whether a *newer* assignment replaced this one; this join adds
    the independent "is the coach relationship itself still live" check on top of that."""
    assignment = db.scalar(
        select(CoachAssignment)
        .join(CoachAccess, CoachAssignment.coach_access_id == CoachAccess.id)
        .where(
            CoachAssignment.singer_user_id == singer_user_id,
            CoachAssignment.status == "active",
            CoachAccess.status == "active",
        )
    )
    if assignment is None:
        return None
    return [uuid.UUID(x) for x in assignment.exercise_ids]
