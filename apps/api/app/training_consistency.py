"""Stage 11: training consistency (streaks + a per-day completed-session count).

Pure functions plus a thin DB-aware orchestration layer, the same split used throughout the
app. "Completed a session" is the same signal `ExerciseSession.completed_at` already uses
everywhere else (Stage 6) — no new definition of what counts as a training day.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExerciseSession

# A day-by-day grid beyond this many days stops being a useful visualization (and is wasteful
# to build/transfer) — streaks themselves are always computed over the user's full history
# regardless of this cap, only the per-day grid is bounded.
MAX_CONSISTENCY_DAYS = 400


def compute_streaks(session_dates: set[date], as_of: date) -> tuple[int, int]:
    """`current_streak`: consecutive days with a completed session, walking backward from
    `as_of` — but if `as_of` itself has no session yet, today isn't "broken" until the day is
    over, so walking starts from yesterday instead. `longest_streak`: the longest run of
    consecutive days anywhere in `session_dates`, independent of `as_of`. Pure: no I/O, no
    clock reads — `as_of` is supplied by the caller."""
    if not session_dates:
        return 0, 0

    current = 0
    day = as_of if as_of in session_dates else as_of - timedelta(days=1)
    while day in session_dates:
        current += 1
        day -= timedelta(days=1)

    longest = 0
    running = 0
    prev: date | None = None
    for d in sorted(session_dates):
        running = running + 1 if prev is not None and d == prev + timedelta(days=1) else 1
        longest = max(longest, running)
        prev = d

    return current, longest


@dataclass
class ConsistencyDay:
    for_date: date
    sessions_completed: int


@dataclass
class TrainingConsistency:
    days: list[ConsistencyDay] = field(default_factory=list)
    current_streak_days: int = 0
    longest_streak_days: int = 0
    total_sessions_in_range: int = 0


def _date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def build_training_consistency(
    db: Session, user_id: uuid.UUID, from_date: date, to_date: date, as_of: date
) -> TrainingConsistency:
    """Streaks are computed over the user's *entire* completed-session history, never bounded
    by `from_date`/`to_date` — a streak that started before the requested display window is
    still real and shouldn't be reported as shorter than it is. Only the per-day grid
    (`days`) is bounded to the requested range, and further clamped to `MAX_CONSISTENCY_DAYS`."""
    completed_at_values = db.scalars(
        select(ExerciseSession.completed_at).where(
            ExerciseSession.user_id == user_id, ExerciseSession.completed_at.isnot(None)
        )
    ).all()
    all_dates = [dt.date() for dt in completed_at_values]

    current_streak, longest_streak = compute_streaks(set(all_dates), as_of)

    grid_start = max(from_date, to_date - timedelta(days=MAX_CONSISTENCY_DAYS - 1))
    counts: dict[date, int] = {}
    for d in all_dates:
        if grid_start <= d <= to_date:
            counts[d] = counts.get(d, 0) + 1

    days = [
        ConsistencyDay(for_date=d, sessions_completed=counts.get(d, 0))
        for d in _date_range(grid_start, to_date)
    ]

    return TrainingConsistency(
        days=days,
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        total_sessions_in_range=sum(counts.values()),
    )
