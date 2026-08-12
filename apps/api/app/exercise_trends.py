"""Stage 8: "keep track if you are getting better, and any trends the internal system can pick
up." A trend classifier, built the same way Stage 4's personal baseline was: compare a recent
window of a user's own real measurements against an earlier window of their own real
measurements, using medians (resistant to one noisy attempt) rather than a black-box model.
This is genuinely "the internal AI" in the sense the product uses that phrase everywhere else —
real statistics over real measurements, described plainly, never oversold as more than it is.

Trends are computed **per exercise**, not per category or globally — different exercises target
different things (a lip trill and a range-exploration exercise aren't comparable), so mixing
their histories together would produce a meaningless average. Only exercises with a
`target_measurement` are ever trended (matches Stage 6's own design: that field exists
specifically to say "this is the one thing this exercise is meant to move").
"""

import statistics
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exercise, ExerciseResult, ExerciseSession

# Below this many attempts, splitting into "recent" vs. "prior" windows isn't meaningful yet —
# matches Stage 4's MIN_SAMPLES_FOR_ANOMALY_DETECTION principle: not enough data to trust a
# comparison, so "insufficient_data" is returned, never a guess dressed up as a trend.
MIN_ATTEMPTS_FOR_TREND = 4
RECENT_WINDOW_SIZE = 3

# Which direction is "better" for each metric — framed plainly (less cycle-to-cycle pitch
# variation, more harmonic clarity), never as a health claim. Metrics with no entry here are
# never trended — an unlisted metric returns "stable" rather than guessing a direction.
METRIC_DIRECTION: dict[str, str] = {
    "jitter_percent": "lower",
    "shimmer_percent": "lower",
    "hnr_db": "higher",
    "pitch_stability_semitones": "lower",
    "f0_max_hz": "higher",
    "f0_min_hz": "lower",
    "duration_seconds": "higher",
    "longest_voiced_run_seconds": "higher",
}

# Minimum |recent_median - prior_median| before a difference counts as a trend at all, in each
# metric's own units — avoids reporting "improving" on ordinary attempt-to-attempt noise.
METRIC_MEANINGFUL_DIFFERENCE: dict[str, float] = {
    "jitter_percent": 0.05,
    "shimmer_percent": 0.05,
    "hnr_db": 1.0,
    "pitch_stability_semitones": 0.2,
    "f0_max_hz": 0.5,
    "f0_min_hz": 0.5,
    "duration_seconds": 0.2,
    "longest_voiced_run_seconds": 0.5,
}


@dataclass
class ExerciseTrend:
    exercise_id: uuid.UUID
    exercise_name: str
    metric_name: str
    direction: str  # "improving" | "declining" | "stable" | "insufficient_data"
    recent_median: float | None
    prior_median: float | None
    attempt_count: int


def classify_trend(values_oldest_first: list[float], metric_name: str) -> ExerciseTrend:
    """Pure: given a metric's historical values in chronological order, classifies the trend.
    Caller fills in exercise_id/exercise_name afterward — kept out of this function so it stays
    trivially testable with plain float lists."""
    count = len(values_oldest_first)
    if count < MIN_ATTEMPTS_FOR_TREND:
        return ExerciseTrend(
            exercise_id=uuid.UUID(int=0),
            exercise_name="",
            metric_name=metric_name,
            direction="insufficient_data",
            recent_median=None,
            prior_median=None,
            attempt_count=count,
        )

    recent = values_oldest_first[-RECENT_WINDOW_SIZE:]
    prior = values_oldest_first[:-RECENT_WINDOW_SIZE]
    recent_median = statistics.median(recent)
    prior_median = statistics.median(prior)
    diff = recent_median - prior_median

    direction_pref = METRIC_DIRECTION.get(metric_name)
    threshold = METRIC_MEANINGFUL_DIFFERENCE.get(metric_name, 0.0)

    if direction_pref is None or abs(diff) < threshold:
        direction = "stable"
    elif direction_pref == "lower":
        direction = "improving" if diff < 0 else "declining"
    else:
        direction = "improving" if diff > 0 else "declining"

    return ExerciseTrend(
        exercise_id=uuid.UUID(int=0),
        exercise_name="",
        metric_name=metric_name,
        direction=direction,
        recent_median=recent_median,
        prior_median=prior_median,
        attempt_count=count,
    )


def overall_trend_is_positive(trends: list[ExerciseTrend]) -> bool:
    """Used by app/exercise_routine.py's adaptive-challenge bias — strictly more improving than
    declining trends, among exercises with an actual classification either way. Ties or no data
    at all are not "positive" (never nudges toward more demanding exercises without real
    evidence of improvement)."""
    scored = [t for t in trends if t.direction in ("improving", "declining")]
    if not scored:
        return False
    improving = sum(1 for t in scored if t.direction == "improving")
    declining = sum(1 for t in scored if t.direction == "declining")
    return improving > declining


# --- Data access & orchestration (talks to the DB; pure functions above don't) ---


def compute_exercise_trends(db: Session, user_id: uuid.UUID) -> list[ExerciseTrend]:
    rows = db.execute(
        select(ExerciseResult, Exercise)
        .join(Exercise, Exercise.id == ExerciseResult.exercise_id)
        .join(ExerciseSession, ExerciseSession.id == ExerciseResult.exercise_session_id)
        .where(ExerciseSession.user_id == user_id, ExerciseResult.measured_result.isnot(None))
        .order_by(ExerciseResult.created_at)
    ).all()

    by_exercise: dict[uuid.UUID, tuple[Exercise, list[float]]] = {}
    for result, exercise in rows:
        if exercise.target_measurement is None:
            continue
        acoustic = (result.measured_result or {}).get("acoustic") or {}
        value = acoustic.get(exercise.target_measurement)
        if value is None:
            continue
        if exercise.id not in by_exercise:
            by_exercise[exercise.id] = (exercise, [])
        by_exercise[exercise.id][1].append(value)

    trends = []
    for exercise, values in by_exercise.values():
        trend = classify_trend(values, exercise.target_measurement)
        trend.exercise_id = exercise.id
        trend.exercise_name = exercise.name
        trends.append(trend)
    return trends
