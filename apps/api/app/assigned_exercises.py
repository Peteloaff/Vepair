"""What a coach has assigned to a singer, resolved for the singer's own screens (the home page's
"Assigned by your coach" card and the standalone runner behind it).

The daily adaptive routine (app/exercise_routine.py) already folds an active assignment into its
time-boxed selection, but only where it fits the length the singer picked and today's safety
cap -- so a singer could be assigned something and never see it. This lists the assignment
itself, always, and splits it into what is runnable today and what today's safety check is
holding back. It reuses the exact same intensity-cap rules as every other routine (via
build_signals_for_user/propose_intensity_caps), so an assignment still can never push a singer
past what is safe for them today."""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coach_assignment import get_active_assignment
from app.exercise_library import CATEGORY_INTENSITY
from app.exercise_routine import (
    INTENSITY_ORDER,
    ExerciseInfo,
    build_signals_for_user,
    propose_intensity_caps,
    to_exercise_info,
)
from app.models import CoachProfile, Exercise


@dataclass
class AssignedExercisesResult:
    has_assignment: bool
    coach_display_name: str | None = None
    coach_studio_name: str | None = None
    note_to_singer: str | None = None
    assigned_at: datetime | None = None
    intensity_cap: str = "high"
    safety_message: str | None = None
    reasons: list[str] = field(default_factory=list)
    items: list[ExerciseInfo] = field(default_factory=list)
    held_back: list[ExerciseInfo] = field(default_factory=list)
    tone_targets: dict[uuid.UUID, str] = field(default_factory=dict)
    total_duration_seconds: int = 0


def build_assigned_exercises_for_user(
    db: Session, user_id: uuid.UUID, for_date: date
) -> AssignedExercisesResult:
    assignment = get_active_assignment(db, user_id)
    if assignment is None:
        return AssignedExercisesResult(has_assignment=False)

    coach = db.get(CoachProfile, assignment.coach_id)

    wanted_ids = [uuid.UUID(x) for x in assignment.exercise_ids]
    rows = {
        row.id: row
        for row in db.scalars(
            select(Exercise).where(Exercise.id.in_(wanted_ids), Exercise.is_active.is_(True))
        ).all()
    }
    # Keep the coach's order; silently drop anything since deactivated or deleted.
    ordered = [to_exercise_info(rows[eid]) for eid in wanted_ids if eid in rows]

    signals = build_signals_for_user(db, user_id, for_date)
    proposals, safety_message = propose_intensity_caps(signals)
    if proposals:
        intensity_cap = min((cap for cap, _ in proposals), key=lambda c: INTENSITY_ORDER[c])
        reasons = [reason for _, reason in proposals]
    else:
        intensity_cap = "high"
        reasons = []

    cap_rank = INTENSITY_ORDER[intensity_cap]
    items = [e for e in ordered if INTENSITY_ORDER[CATEGORY_INTENSITY[e.category]] <= cap_rank]
    held_back = [e for e in ordered if e not in items]

    shown_ids = {e.id for e in ordered}
    tone_targets = {
        uuid.UUID(k): v
        for k, v in (assignment.exercise_tone_targets or {}).items()
        if uuid.UUID(k) in shown_ids
    }

    return AssignedExercisesResult(
        has_assignment=True,
        coach_display_name=coach.display_name if coach else None,
        coach_studio_name=coach.studio_name if coach else None,
        note_to_singer=assignment.note_to_singer,
        assigned_at=assignment.created_at,
        intensity_cap=intensity_cap,
        safety_message=safety_message,
        reasons=reasons,
        items=items,
        held_back=held_back,
        tone_targets=tone_targets,
        total_duration_seconds=sum(e.duration_seconds for e in items),
    )
