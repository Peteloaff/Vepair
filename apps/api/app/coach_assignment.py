"""Stage 12 Phase II. Resolves whether a coach's exercise assignment should influence today's
routine — a pure lookup layered on top of app/exercise_routine.py's existing signal-gathering in
build_routine_for_user, never a second routine-generation path."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CoachAccess, CoachAssignment


def _get_active_assignment(db: Session, singer_user_id: uuid.UUID) -> CoachAssignment | None:
    """None unless there is BOTH an active CoachAssignment AND its linked CoachAccess is still
    active — revoking access silently stops an assignment's influence on future routines
    without deleting the assignment's own history row. CoachAssignment.status
    (active/superseded) tracks whether a *newer* assignment replaced this one; this join adds
    the independent "is the coach relationship itself still live" check on top of that."""
    return db.scalar(
        select(CoachAssignment)
        .join(CoachAccess, CoachAssignment.coach_access_id == CoachAccess.id)
        .where(
            CoachAssignment.singer_user_id == singer_user_id,
            CoachAssignment.status == "active",
            CoachAccess.status == "active",
        )
    )


def get_active_assigned_exercise_ids(
    db: Session, singer_user_id: uuid.UUID
) -> list[uuid.UUID] | None:
    assignment = _get_active_assignment(db, singer_user_id)
    if assignment is None:
        return None
    return [uuid.UUID(x) for x in assignment.exercise_ids]


def get_active_assigned_exercise_tone_targets(
    db: Session, singer_user_id: uuid.UUID
) -> dict[uuid.UUID, str]:
    """The per-exercise target notes a coach set on the currently-active assignment, if any --
    same active-assignment-and-access gating as get_active_assigned_exercise_ids. Returns an
    empty dict (never None) when there's no active assignment or no targets were set on it, so
    callers can always do a plain `.get(exercise_id)` without a None check first."""
    assignment = _get_active_assignment(db, singer_user_id)
    if assignment is None or not assignment.exercise_tone_targets:
        return {}
    return {uuid.UUID(k): v for k, v in assignment.exercise_tone_targets.items()}
