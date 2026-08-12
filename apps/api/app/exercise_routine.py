"""Stage 6 adaptive exercise routine generator.

A rule-based, fully inspectable selector — not a black box — per MEDICAL_SAFETY.md section 5
("recommendation logic must stay inspectable"). Every routine comes with a `reasons` list
explaining exactly which signals pushed it toward a gentler or fuller routine, the same
transparency pattern as Stage 5's "why did I get this score?"

**The one rule that can never be overridden**: reported pain/discomfort never gets a "push
through it" response (per the product brief, verbatim). High `throat_discomfort` forces the
lowest intensity tier and a safety message, regardless of every other signal — checked first,
same hard-override pattern as Stage 5's recovery-score discomfort rule.

Every other signal (recovery status, fatigue, recent load, poor sleep, baseline deviation, long
rest gaps) independently proposes how cautious today's routine should be; the routine uses the
*most* conservative of everything that fired, and lists all of them, not just the binding one —
a day can be held back for more than one reason at once, and the user should see all of them.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exercise_library import CATEGORY_INTENSITY, CLOSING_CATEGORY, OPENING_CATEGORY
from app.exercise_trends import compute_exercise_trends, overall_trend_is_positive
from app.models import DailyCheckIn, Exercise, ExerciseSession, UserProfile
from app.recovery_score import SAFETY_MESSAGE, compute_and_store_recovery_score

VALID_ROUTINE_LENGTHS_MINUTES: tuple[int, ...] = (5, 10, 15, 20)

INTENSITY_ORDER: dict[str, int] = {"low": 0, "moderate": 1, "high": 2}

# Deterministic fill order for the "middle" of a routine (after the opening breathing exercise,
# before the closing cooldown) — gentlest categories first, building toward more demanding ones.
# A routine capped at "moderate" simply never reaches the last two entries; capped at "low", it
# never reaches past the SOVT/straw/humming group. Not a clinical sequencing requirement, just
# the standard "start light, build up" warmup structure.
MIDDLE_CATEGORY_ORDER: tuple[str, ...] = (
    "SOVT",
    "Straw phonation",
    "Gentle humming",
    "Lip trill",
    "Tongue trill",
    "Resonant voice exercises",
    "Speaking voice recovery",
    "Gentle sirens",
    "Pitch glides",
    "Range exploration",
)

# Very small, best-effort keyword tie-breaker for "adapt based on ... user goal" — reorders
# which allowed categories are tried first, never adds a category the intensity cap excludes.
# Deliberately not NLP: a handful of literal substrings, documented as exactly what it is.
GOAL_KEYWORD_PRIORITY: dict[str, tuple[str, ...]] = {
    "range": ("Range exploration", "Pitch glides"),
    "speak": ("Speaking voice recovery",),
    "recovery": ("Speaking voice recovery", "Vocal cooldown"),
    "rest": ("Speaking voice recovery", "Vocal cooldown"),
}

FATIGUE_MODERATE_THRESHOLD = 8
POOR_SLEEP_HOURS_THRESHOLD = 5.0
REST_GAP_DAYS_THRESHOLD = 5
BASELINE_DEVIATION_COMPONENT_THRESHOLD = 40.0


@dataclass(frozen=True)
class ExerciseInfo:
    id: uuid.UUID
    name: str
    category: str
    purpose: str
    instructions: str
    duration_seconds: int
    difficulty: str
    contraindications: str | None
    target_measurement: str | None
    expected_result: str


@dataclass
class RoutineSignals:
    recovery_status: str  # "green" | "yellow" | "red" | "unknown"
    throat_discomfort: int | None
    fatigue: int | None
    sleep_hours: float | None
    rehearsal_or_performance_yesterday: bool | None
    baseline_deviation: bool
    days_since_last_exercise: int | None
    goal_text: str | None
    # Stage 8: "as you get better the AI needs to challenge your voice to get better as well."
    # True only when the user's own exercise-trend history (app/exercise_trends.py) shows more
    # improving trends than declining ones. This can only ever bias *which* already-allowed
    # exercises get picked (harder-first instead of gentlest-first) — it never raises
    # intensity_cap itself, so every safety rule above still applies exactly as before.
    trending_positive: bool = False
    # Stage 9: "repair" | "improvement" | None. Only ever adjusts how readily challenge_mode
    # engages (see _resolve_challenge_mode) — never touches intensity_cap or any hard safety
    # rule above, which apply identically regardless of track.
    track: str | None = None


@dataclass
class RoutineResult:
    length_minutes: int
    intensity_cap: str
    items: list[ExerciseInfo]
    total_duration_seconds: int
    safety_message: str | None
    reasons: list[str] = field(default_factory=list)


def _propose_intensity_caps(signals: RoutineSignals) -> tuple[list[tuple[str, str]], str | None]:
    """Every independent rule that fires proposes a (cap, reason) pair. Discomfort also carries
    the fixed safety message. Nothing here picks a "final" cap — the caller takes the strictest
    (lowest) of everything proposed."""
    proposals: list[tuple[str, str]] = []
    safety_message = None

    if signals.throat_discomfort is not None and signals.throat_discomfort >= 7:
        proposals.append(
            (
                "low",
                "You reported significant discomfort — keeping today to the gentlest exercises "
                "only, never pushing through it.",
            )
        )
        safety_message = SAFETY_MESSAGE

    if signals.recovery_status == "red":
        proposals.append(
            ("low", "Today's recovery status is red — sticking to low-demand exercises.")
        )

    if signals.rehearsal_or_performance_yesterday and (
        signals.fatigue is not None and signals.fatigue >= FATIGUE_MODERATE_THRESHOLD
    ):
        proposals.append(
            (
                "low",
                "Heavy vocal load yesterday combined with high reported fatigue — easing off "
                "today rather than stacking demanding exercises on an already-tired voice.",
            )
        )
    elif signals.fatigue is not None and signals.fatigue >= FATIGUE_MODERATE_THRESHOLD:
        proposals.append(("moderate", "High reported fatigue — keeping today's routine moderate."))

    if signals.recovery_status == "yellow":
        proposals.append(
            ("moderate", "Today's recovery status is yellow — moderate exercises only.")
        )

    if signals.sleep_hours is not None and signals.sleep_hours < POOR_SLEEP_HOURS_THRESHOLD:
        proposals.append(("moderate", "Poor reported sleep — keeping today's routine moderate."))

    if (
        signals.days_since_last_exercise is not None
        and signals.days_since_last_exercise >= REST_GAP_DAYS_THRESHOLD
    ):
        proposals.append(
            ("moderate", "It's been several days since your last routine — easing back in.")
        )

    if signals.baseline_deviation:
        proposals.append(
            (
                "moderate",
                "Today's voice measurements look different from your usual baseline — playing "
                "it a bit safer.",
            )
        )

    return proposals, safety_message


DIFFICULTY_ORDER: dict[str, int] = {"easy": 0, "moderate": 1, "hard": 2}


def _select_exercises(
    exercises: list[ExerciseInfo],
    length_minutes: int,
    intensity_cap: str,
    goal_text: str | None,
    challenge_mode: bool = False,
) -> list[ExerciseInfo]:
    budget_seconds = length_minutes * 60
    cap_rank = INTENSITY_ORDER[intensity_cap]
    allowed = [e for e in exercises if INTENSITY_ORDER[CATEGORY_INTENSITY[e.category]] <= cap_rank]
    by_category: dict[str, list[ExerciseInfo]] = {}
    for e in allowed:
        by_category.setdefault(e.category, []).append(e)
    if challenge_mode:
        # Within each category, try the more demanding (but still fully-allowed) exercise
        # first — never reaches past what intensity_cap already permits, just changes which of
        # the allowed options gets picked when there's more than one per category.
        for category_exercises in by_category.values():
            category_exercises.sort(key=lambda e: DIFFICULTY_ORDER[e.difficulty], reverse=True)

    selected: list[ExerciseInfo] = []
    used_ids: set[uuid.UUID] = set()
    remaining = budget_seconds

    def try_add(exercise: ExerciseInfo, reserve: int = 0) -> bool:
        """Adds the exercise if it fits without dipping into `reserve` seconds held back for
        something else (the closing cooldown) — skips it and keeps looking rather than
        stopping the whole fill, so a later, smaller exercise still gets a chance."""
        nonlocal remaining
        if exercise.id in used_ids or exercise.duration_seconds > remaining - reserve:
            return False
        selected.append(exercise)
        used_ids.add(exercise.id)
        remaining -= exercise.duration_seconds
        return True

    opening = by_category.get(OPENING_CATEGORY, [])
    if opening:
        try_add(opening[0])

    closing = by_category.get(CLOSING_CATEGORY, [])
    closing_reserved = closing[0].duration_seconds if closing else 0

    middle_order = (
        list(reversed(MIDDLE_CATEGORY_ORDER)) if challenge_mode else list(MIDDLE_CATEGORY_ORDER)
    )
    if goal_text:
        goal_lower = goal_text.lower()
        boosted: list[str] = []
        for keyword, categories in GOAL_KEYWORD_PRIORITY.items():
            if keyword in goal_lower:
                boosted.extend(c for c in categories if c not in boosted)
        middle_order = boosted + [c for c in middle_order if c not in boosted]

    for category in middle_order:
        for exercise in by_category.get(category, []):
            try_add(exercise, reserve=closing_reserved)

    if closing:
        try_add(closing[0])

    return selected


def _resolve_challenge_mode(
    intensity_cap: str, signals: RoutineSignals
) -> tuple[bool, str | None]:
    """Only ever applies on an already-uncapped day (`intensity_cap == "high"`) — challenge
    mode reorders which allowed exercises get picked, it never unlocks anything the safety
    rules above wouldn't already allow. Stage 9's track adjusts how *readily* it engages:
    Repair never enters it (a repair program is about steadiness, not stretch); Improvement
    engages it by default whenever the day is safe (choosing that track is itself the signal —
    it doesn't need to wait for confirmed positive trend data first); with no track selected,
    Stage 8's original behavior is unchanged (requires an actual positive trend)."""
    if intensity_cap != "high":
        return False, None

    if signals.track == "repair":
        return False, None

    if signals.track == "improvement":
        return True, (
            "You're on an Improvement track — today leans toward slightly more demanding "
            "exercises within what's already safe for today."
        )

    if signals.trending_positive:
        return True, (
            "Your recent trends look positive — today leans toward slightly more demanding "
            "exercises within what's already safe for today."
        )

    return False, None


def generate_routine(
    exercises: list[ExerciseInfo], length_minutes: int, signals: RoutineSignals
) -> RoutineResult:
    proposals, safety_message = _propose_intensity_caps(signals)
    if proposals:
        intensity_cap = min((cap for cap, _ in proposals), key=lambda c: INTENSITY_ORDER[c])
        reasons = [reason for _, reason in proposals]
    else:
        intensity_cap = "high"
        reasons = ["Nothing today suggests holding back — the full routine is available."]

    challenge_mode, challenge_reason = _resolve_challenge_mode(intensity_cap, signals)
    if challenge_reason:
        reasons.append(challenge_reason)

    items = _select_exercises(
        exercises, length_minutes, intensity_cap, signals.goal_text, challenge_mode
    )
    total_duration_seconds = sum(e.duration_seconds for e in items)

    return RoutineResult(
        length_minutes=length_minutes,
        intensity_cap=intensity_cap,
        items=items,
        total_duration_seconds=total_duration_seconds,
        safety_message=safety_message,
        reasons=reasons,
    )


# --- Data access & orchestration (talks to the DB; pure functions above don't) ---


def _to_exercise_info(row: Exercise) -> ExerciseInfo:
    return ExerciseInfo(
        id=row.id,
        name=row.name,
        category=row.category,
        purpose=row.purpose,
        instructions=row.instructions,
        duration_seconds=row.duration_seconds,
        difficulty=row.difficulty,
        contraindications=row.contraindications,
        target_measurement=row.target_measurement,
        expected_result=row.expected_result,
    )


def build_routine_for_user(
    db: Session, user_id: uuid.UUID, length_minutes: int, for_date: date
) -> RoutineResult:
    exercises = [
        _to_exercise_info(row)
        for row in db.scalars(select(Exercise).where(Exercise.is_active.is_(True))).all()
    ]

    checkin = db.scalar(
        select(DailyCheckIn).where(
            DailyCheckIn.user_id == user_id, DailyCheckIn.checkin_date == for_date
        )
    )

    score_result = compute_and_store_recovery_score(db, user_id, for_date)
    baseline_deviation = any(
        c.key in ("consistency_vs_baseline", "acoustic_stability")
        and c.score is not None
        and c.score < BASELINE_DEVIATION_COMPONENT_THRESHOLD
        for c in score_result.components
    )

    last_session = db.scalar(
        select(ExerciseSession)
        .where(ExerciseSession.user_id == user_id, ExerciseSession.completed_at.isnot(None))
        .order_by(ExerciseSession.completed_at.desc())
    )
    days_since_last_exercise = (
        (for_date - last_session.completed_at.date()).days if last_session else None
    )

    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    trends = compute_exercise_trends(db, user_id)

    signals = RoutineSignals(
        recovery_status=score_result.status,
        throat_discomfort=checkin.throat_discomfort if checkin else None,
        fatigue=checkin.fatigue if checkin else None,
        sleep_hours=checkin.sleep_hours if checkin else None,
        rehearsal_or_performance_yesterday=(
            checkin.rehearsal_or_performance_yesterday if checkin else None
        ),
        baseline_deviation=baseline_deviation,
        days_since_last_exercise=days_since_last_exercise,
        goal_text=profile.goals if profile else None,
        trending_positive=overall_trend_is_positive(trends),
        track=profile.track if profile else None,
    )

    return generate_routine(exercises, length_minutes, signals)
