"""Goal Tones: a singer's target low/avg/high note. Defaults to an AI suggestion derived
entirely from the singer's own measured vocal range history (never a population target — see
compute_ai_recommended_goals), and can be overridden at any time with a manually-set value that
sticks until explicitly cleared. See app/vocal_range.py for the underlying range history this
reads from, and app/exercise_routine.py for how an active goal biases exercise selection.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import VocalGoal
from app.vocal_range import build_summary, note_name_to_midi

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def _midi_to_note_name(midi: int) -> str:
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


@dataclass(frozen=True)
class GoalTones:
    target_low_note: str | None
    target_avg_note: str | None
    target_high_note: str | None
    source: str  # "ai" | "manual"


def compute_ai_recommended_goals(db: Session, user_id: uuid.UUID) -> GoalTones:
    """Low/high default to the user's own historical best measured range (never a population
    target — matches vocal_range.py's existing "never encourage forcing extreme notes"
    discipline everywhere else in this codebase); avg is the semitone midpoint between them.
    Returns all-None fields when there isn't enough vocal range history yet — never fabricated,
    same convention as every other "not enough data" path in this codebase."""
    summary = build_summary(db, user_id)
    low = summary.historical_best_low_note
    high = summary.historical_best_high_note
    avg = None
    if low is not None and high is not None:
        avg = _midi_to_note_name(round((note_name_to_midi(low) + note_name_to_midi(high)) / 2))
    return GoalTones(target_low_note=low, target_avg_note=avg, target_high_note=high, source="ai")


def get_active_goals(db: Session, user_id: uuid.UUID) -> GoalTones:
    """The goals that should actually be used right now: a manually-set row if one exists and
    has at least one note set, otherwise a fresh AI recommendation (never a stale one — always
    recomputed from current range history, so it keeps improving as the user records more)."""
    row = db.scalar(select(VocalGoal).where(VocalGoal.user_id == user_id))
    if row is not None and row.source == "manual":
        return GoalTones(
            target_low_note=row.target_low_note,
            target_avg_note=row.target_avg_note,
            target_high_note=row.target_high_note,
            source="manual",
        )
    return compute_ai_recommended_goals(db, user_id)


def set_manual_goals(
    db: Session,
    user_id: uuid.UUID,
    target_low_note: str | None,
    target_avg_note: str | None,
    target_high_note: str | None,
) -> VocalGoal:
    """Upserts the singer's manual override in place — current-state, not history, same pattern
    as UserProfile. Any field left as None here is simply not overridden by this call; to fully
    clear a manual override, use clear_manual_goals instead."""
    row = db.scalar(select(VocalGoal).where(VocalGoal.user_id == user_id))
    if row is None:
        row = VocalGoal(user_id=user_id, source="manual")
        db.add(row)
    row.target_low_note = target_low_note
    row.target_avg_note = target_avg_note
    row.target_high_note = target_high_note
    row.source = "manual"
    db.commit()
    db.refresh(row)
    return row


def clear_manual_goals(db: Session, user_id: uuid.UUID) -> None:
    """Reverts to the AI recommendation going forward. Deletes the row entirely rather than
    just flipping source back to "ai" with stale note values still sitting in it — the next
    get_active_goals call recomputes fresh from current range history either way."""
    row = db.scalar(select(VocalGoal).where(VocalGoal.user_id == user_id))
    if row is not None:
        db.delete(row)
        db.commit()
