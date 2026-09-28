"""Standalone, on-demand Warm Up / Cool Down routines -- a sibling to exercise_routine.py, not
an extension of it. The daily adaptive routine bin-packs a time budget across a 10-category
sequence; a quick routine is a short, fixed progression (one exercise per category, no time
budget), so it gets its own, much smaller selector rather than growing that one's already-large
surface.

Reuses exercise_routine.py's safety-signal gathering unchanged -- a quick routine goes through
the exact same intensity-cap rules (including the hard discomfort override) as the daily
adaptive routine, via the same build_signals_for_user/propose_intensity_caps this module
imports rather than reimplementing."""

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exercise_library import CATEGORY_INTENSITY
from app.exercise_routine import (
    INTENSITY_ORDER,
    ExerciseInfo,
    build_signals_for_user,
    propose_intensity_caps,
    to_exercise_info,
)
from app.models import Exercise

# A short, deliberate "ease in" progression -- not the full adaptive category mix. All three are
# already "low" intensity today, so the cap filter below is a no-op in practice right now; it's
# still applied every time so a future category addition (or a rough day, if these categories
# ever gain a moderate/high exercise) is handled correctly rather than assumed away.
WARM_UP_CATEGORIES: tuple[str, ...] = ("Breathing", "Gentle humming", "SOVT")

# "Vocal cooldown" is already purpose-built for exactly this -- see exercise_library.py's
# CLOSING_CATEGORY, which every daily adaptive routine already closes with. No progression
# needed, just the category as-is.
COOL_DOWN_CATEGORIES: tuple[str, ...] = ("Vocal cooldown",)

QUICK_ROUTINE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "warm_up": WARM_UP_CATEGORIES,
    "cool_down": COOL_DOWN_CATEGORIES,
}


@dataclass
class QuickRoutineResult:
    kind: str  # "warm_up" | "cool_down"
    intensity_cap: str
    items: list[ExerciseInfo]
    total_duration_seconds: int
    safety_message: str | None
    reasons: list[str] = field(default_factory=list)


def _select_one_per_category(
    exercises: list[ExerciseInfo], categories: tuple[str, ...], intensity_cap: str
) -> list[ExerciseInfo]:
    cap_rank = INTENSITY_ORDER[intensity_cap]
    by_category: dict[str, list[ExerciseInfo]] = {}
    for e in exercises:
        if INTENSITY_ORDER[CATEGORY_INTENSITY[e.category]] <= cap_rank:
            by_category.setdefault(e.category, []).append(e)

    selected: list[ExerciseInfo] = []
    for category in categories:
        candidates = by_category.get(category)
        if candidates:
            selected.append(candidates[0])
    return selected


def generate_quick_routine(
    exercises: list[ExerciseInfo], kind: str, signals
) -> QuickRoutineResult:
    categories = QUICK_ROUTINE_CATEGORIES[kind]
    proposals, safety_message = propose_intensity_caps(signals)
    if proposals:
        intensity_cap = min((cap for cap, _ in proposals), key=lambda c: INTENSITY_ORDER[c])
        reasons = [reason for _, reason in proposals]
    else:
        intensity_cap = "high"
        reasons = []

    items = _select_one_per_category(exercises, categories, intensity_cap)
    return QuickRoutineResult(
        kind=kind,
        intensity_cap=intensity_cap,
        items=items,
        total_duration_seconds=sum(e.duration_seconds for e in items),
        safety_message=safety_message,
        reasons=reasons,
    )


def build_quick_routine_for_user(
    db: Session, user_id: uuid.UUID, kind: str, for_date: date
) -> QuickRoutineResult:
    exercises = [
        to_exercise_info(row)
        for row in db.scalars(select(Exercise).where(Exercise.is_active.is_(True))).all()
    ]
    signals = build_signals_for_user(db, user_id, for_date)
    return generate_quick_routine(exercises, kind, signals)
