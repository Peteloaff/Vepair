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
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coach_assignment import (
    get_active_assigned_exercise_ids,
    get_active_assigned_exercise_tone_targets,
)
from app.exercise_library import CATEGORY_INTENSITY, CLOSING_CATEGORY, OPENING_CATEGORY
from app.exercise_trends import compute_exercise_trends, overall_trend_is_positive
from app.models import DailyCheckIn, Exercise, ExerciseSession, UserProfile
from app.recovery_score import (
    SAFETY_MESSAGE,
    compute_and_store_recovery_score,
    fetch_score_history,
)
from app.vocal_goals import get_active_goals
from app.vocal_range import build_summary as build_vocal_range_summary
from app.vocal_range import note_name_to_midi

VALID_ROUTINE_LENGTHS_MINUTES: tuple[int, ...] = (5, 10, 15, 20)

INTENSITY_ORDER: dict[str, int] = {"low": 0, "moderate": 1, "high": 2}

# A rest day is a stricter tier above the existing "gentlest exercises only" cutoff
# (throat_discomfort >= 7, see _propose_intensity_caps) — reserved for the cases where even the
# gentlest routine isn't the right call today. Never a hard block: generate_routine still
# returns a valid (lowest-intensity) routine underneath, so someone who chooses to exercise
# anyway still gets something appropriate, matching how discomfort already works.
REST_DAY_DISCOMFORT_THRESHOLD = 9
REST_DAY_CONSECUTIVE_RED_DAYS_THRESHOLD = 3

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
    # Stage 12 Phase II: an active coach assignment, if any (see app/coach_assignment.py).
    # These exercises get priority within the budget in _select_exercises, but only from the
    # exact same intensity-cap-filtered candidate list every adaptively-chosen exercise is
    # drawn from — see _select_exercises's `allowed` list. There is no code path where an
    # assigned exercise can exceed today's intensity_cap; this field can never weaken or
    # bypass any rule in _propose_intensity_caps.
    coach_assigned_exercise_ids: list[uuid.UUID] | None = None
    # How many days up to and including today have a stored "red" recovery status, with no gap
    # (see _consecutive_red_days) — feeds the rest-day recommendation below. Never inferred from
    # a day with no stored score; a missing day always breaks the streak.
    consecutive_red_days: int = 0
    # Goal Tones (app/vocal_goals.py): set only when there's an *active, not-yet-reached* goal
    # in that direction — build_signals_for_user does that comparison against the user's current
    # measured range before populating these, so _select_exercises never has to re-derive it.
    # Only ever biases which already-allowed categories get tried first (Range exploration /
    # Pitch glides) — never raises intensity_cap or bypasses any safety rule above.
    goal_high_note: str | None = None
    goal_low_note: str | None = None
    # Stage 12 Phase II: a coach's per-exercise target note (app/coach_assignment.py), if any --
    # purely informational, surfaced back out on RoutineResult for whichever assigned exercises
    # actually make it into today's routine. Never affects selection or safety in any way.
    coach_exercise_tone_targets: dict[uuid.UUID, str] = field(default_factory=dict)


@dataclass
class RoutineResult:
    length_minutes: int
    intensity_cap: str
    items: list[ExerciseInfo]
    total_duration_seconds: int
    safety_message: str | None
    reasons: list[str] = field(default_factory=list)
    # Which coach-assigned exercise ids (if any) actually made it into `items` — see
    # generate_routine. Empty when there was no assignment, or none of it fit today's safety
    # limits (in which case `reasons` explains why, never silently).
    assigned_exercise_ids: list[uuid.UUID] = field(default_factory=list)
    # A strong recommendation, never a block — `items` above is still a valid, safe routine
    # (the lowest intensity tier) even when this is True, for anyone who chooses to exercise
    # anyway. See REST_DAY_DISCOMFORT_THRESHOLD / REST_DAY_CONSECUTIVE_RED_DAYS_THRESHOLD.
    rest_day_recommended: bool = False
    rest_day_reason: str | None = None
    # Coach-set per-exercise target notes (see coach_exercise_tone_targets on RoutineSignals),
    # filtered down to only the exercises that actually made it into `items` today.
    exercise_tone_targets: dict[uuid.UUID, str] = field(default_factory=dict)


def _should_recommend_rest_day(signals: RoutineSignals) -> tuple[bool, str | None]:
    """A stricter tier above _propose_intensity_caps's existing "low" cutoff
    (throat_discomfort >= 7) — reserved for when even the gentlest routine isn't the right call.
    Escalation language follows MEDICAL_SAFETY.md section 2/3's style: never an order, never a
    diagnosis, always pointing toward a qualified professional if it persists."""
    if (
        signals.throat_discomfort is not None
        and signals.throat_discomfort >= REST_DAY_DISCOMFORT_THRESHOLD
    ):
        return True, (
            "Today's reported discomfort is severe. Today looks like a good day to rest your "
            "voice completely rather than exercise. If this continues, consider checking in "
            "with a qualified voice professional."
        )
    if signals.consecutive_red_days >= REST_DAY_CONSECUTIVE_RED_DAYS_THRESHOLD:
        return True, (
            f"Your recovery status has been red for {signals.consecutive_red_days} days in a "
            "row. Today looks like a good day to rest your voice completely rather than "
            "exercise. If this continues, consider checking in with a qualified voice "
            "professional."
        )
    return False, None


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
    assigned_exercise_ids: list[uuid.UUID] | None = None,
    boost_range_categories: bool = False,
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

    # Coach-assigned exercises (Stage 12 Phase II) get priority within the budget, tried right
    # after the opening exercise — but only ever from `allowed`, the exact same
    # intensity-cap-filtered list every adaptively-chosen exercise below is drawn from. An
    # assigned exercise that exceeds today's cap was already excluded from `allowed` above and
    # is never even a candidate here.
    if assigned_exercise_ids:
        allowed_by_id = {e.id: e for e in allowed}
        for exercise_id in assigned_exercise_ids:
            exercise = allowed_by_id.get(exercise_id)
            if exercise is not None:
                try_add(exercise, reserve=closing_reserved)

    middle_order = (
        list(reversed(MIDDLE_CATEGORY_ORDER)) if challenge_mode else list(MIDDLE_CATEGORY_ORDER)
    )
    boosted: list[str] = []
    if goal_text:
        goal_lower = goal_text.lower()
        for keyword, categories in GOAL_KEYWORD_PRIORITY.items():
            if keyword in goal_lower:
                boosted.extend(c for c in categories if c not in boosted)
    if boost_range_categories:
        # Goal Tones (app/vocal_goals.py): the user has an active target they haven't reached
        # yet — bias toward the categories that actually work the edges of range, same
        # mechanism as the goal_text keyword boost above, still fully bounded by intensity_cap.
        boosted.extend(c for c in ("Range exploration", "Pitch glides") if c not in boosted)
    if boosted:
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

    boost_range_categories = bool(signals.goal_high_note or signals.goal_low_note)
    if boost_range_categories:
        reasons.append(
            "You have an active target tone you haven't reached yet — today's routine leans "
            "toward range-stretching exercises within what's already safe for today."
        )

    items = _select_exercises(
        exercises,
        length_minutes,
        intensity_cap,
        signals.goal_text,
        challenge_mode,
        signals.coach_assigned_exercise_ids,
        boost_range_categories,
    )
    total_duration_seconds = sum(e.duration_seconds for e in items)

    assigned_included: list[uuid.UUID] = []
    if signals.coach_assigned_exercise_ids:
        included_ids = {e.id for e in items}
        assigned_included = [
            eid for eid in signals.coach_assigned_exercise_ids if eid in included_ids
        ]
        # Never silent either way — a coach or singer could otherwise wonder why an
        # assignment "didn't work" on a day the safety check held the routine back.
        if assigned_included:
            reasons.append(
                "Your coach assigned specific exercises for today — included where today's "
                "safety limits allow."
            )
        else:
            reasons.append(
                "Your coach assigned exercises for today, but today's safety check kept the "
                "routine to gentler options instead."
            )

    rest_day_recommended, rest_day_reason = _should_recommend_rest_day(signals)

    exercise_tone_targets: dict[uuid.UUID, str] = {}
    if signals.coach_exercise_tone_targets:
        included_ids = {e.id for e in items}
        exercise_tone_targets = {
            eid: note
            for eid, note in signals.coach_exercise_tone_targets.items()
            if eid in included_ids
        }

    return RoutineResult(
        length_minutes=length_minutes,
        intensity_cap=intensity_cap,
        items=items,
        total_duration_seconds=total_duration_seconds,
        safety_message=safety_message,
        reasons=reasons,
        assigned_exercise_ids=assigned_included,
        rest_day_recommended=rest_day_recommended,
        rest_day_reason=rest_day_reason,
        exercise_tone_targets=exercise_tone_targets,
    )


# --- Data access & orchestration (talks to the DB; pure functions above don't) ---


def _consecutive_red_days(db: Session, user_id: uuid.UUID, for_date: date) -> int:
    """How many days up to and including for_date have a stored "red" status, with no gap. Only
    ever looks at scores that were actually already computed and stored (fetch_score_history
    never backfills) — a day with no stored row breaks the streak rather than being assumed
    either way, since there's no way to know what it would have been."""
    history = fetch_score_history(db, user_id, for_date - timedelta(days=6), for_date)
    by_date = {h.score_date: h.status for h in history}
    count = 0
    day = for_date
    while by_date.get(day) == "red":
        count += 1
        day -= timedelta(days=1)
    return count


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


def build_signals_for_user(db: Session, user_id: uuid.UUID, for_date: date) -> RoutineSignals:
    """Gathers every signal generate_routine needs, without selecting any exercises — the part
    build_routine_for_user and the lightweight rest-day check (GET /api/v1/routine/rest-check)
    both need, factored out so the latter never has to build a full routine just to answer
    "should today be a rest day?"."""
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

    # Goal Tones (app/vocal_goals.py): only carried onto signals when there's an active goal in
    # that direction the user hasn't reached yet — the "not yet reached" comparison happens
    # here, once, so _select_exercises never has to re-derive it from raw values.
    goals = get_active_goals(db, user_id)
    range_summary = build_vocal_range_summary(db, user_id)
    goal_high_note = None
    if goals.target_high_note is not None and (
        range_summary.current_high_note is None
        or note_name_to_midi(goals.target_high_note)
        > note_name_to_midi(range_summary.current_high_note)
    ):
        goal_high_note = goals.target_high_note
    goal_low_note = None
    if goals.target_low_note is not None and (
        range_summary.current_low_note is None
        or note_name_to_midi(goals.target_low_note)
        < note_name_to_midi(range_summary.current_low_note)
    ):
        goal_low_note = goals.target_low_note

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
        coach_assigned_exercise_ids=get_active_assigned_exercise_ids(db, user_id),
        consecutive_red_days=_consecutive_red_days(db, user_id, for_date),
        goal_high_note=goal_high_note,
        goal_low_note=goal_low_note,
        coach_exercise_tone_targets=get_active_assigned_exercise_tone_targets(db, user_id),
    )
    return signals


def build_routine_for_user(
    db: Session, user_id: uuid.UUID, length_minutes: int, for_date: date
) -> RoutineResult:
    exercises = [
        _to_exercise_info(row)
        for row in db.scalars(select(Exercise).where(Exercise.is_active.is_(True))).all()
    ]
    signals = build_signals_for_user(db, user_id, for_date)
    return generate_routine(exercises, length_minutes, signals)


def check_rest_day_for_user(
    db: Session, user_id: uuid.UUID, for_date: date
) -> tuple[bool, str | None]:
    """The GET /api/v1/routine/rest-check entrypoint — same signals and same rule as
    build_routine_for_user's routine, just without spending the work of also selecting
    exercises for a length_minutes the caller may not have (e.g. the home page)."""
    signals = build_signals_for_user(db, user_id, for_date)
    return _should_recommend_rest_day(signals)
