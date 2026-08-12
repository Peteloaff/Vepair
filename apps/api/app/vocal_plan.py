"""Stage 9: personalized Repair/Improvement track and 90-day plan.

**A plan doesn't replace the adaptive systems already built — it steers them.** Day-to-day
exercise selection still runs entirely through `app/exercise_routine.py`; day-to-day range
stretch suggestions still run through `app/vocal_range.py`. A `VocalPlan` only supplies the
track (which those two modules read to decide how conservative or how encouraging to be) and a
long-term target, captured once at plan creation from real, already-measured data — never a
second, competing scheduling engine.

**"Repair" and "Improvement" are self-selected programs, never diagnoses.** VepAIr has no way
to know whether a user ever had a real vocal injury — the track is what the user picked, and
"graduating" from Repair to Improvement means "your recent data has been consistently stable,"
never "you are healed." See MEDICAL_SAFETY.md.

**Auto-graduation is a transparent, rule-based check, not a black box** — every criterion and
its pass/fail reason is returned alongside the yes/no answer, the same "show your work" pattern
used by Stage 5's recovery score and Stage 6's routine generator.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exercise_trends import compute_exercise_trends
from app.models import (
    AcousticMeasurement,
    Baseline,
    Recording,
    RecoveryScore,
    UserProfile,
    VocalPlan,
    VocalRange,
    VoiceSession,
)

TRACKS = ("repair", "improvement")

PLAN_DURATION_DAYS = 90
REPAIR_TARGET_STABLE_DAYS = 30
IMPROVEMENT_TARGET_SEMITONES = 3

# Graduation-readiness thresholds. All chosen to require sustained, real evidence rather than a
# lucky week — see assess_graduation_readiness for how each is used.
READINESS_LOOKBACK_DAYS = 14
READINESS_MIN_NONRED_RATIO = 0.7
READY_BASELINE_CONFIDENCE_LABELS = frozenset({"developing", "established"})


@dataclass
class ReadinessResult:
    ready: bool
    reasons: list[str] = field(default_factory=list)


def assess_graduation_readiness(
    recent_statuses: list[str],
    latest_baseline_confidence: str | None,
    trend_directions: list[str],
) -> ReadinessResult:
    """Pure: every input is already-computed data (Stage 5 recovery-score statuses, Stage 4
    baseline confidence, Stage 8 exercise-trend directions) — this function only classifies,
    never fetches. `ready` requires every criterion to pass; `reasons` explains all of them,
    not just the binding one, so a "not ready yet" answer is never a mystery."""
    reasons: list[str] = []
    ready = True

    if len(recent_statuses) < READINESS_LOOKBACK_DAYS:
        reasons.append(
            f"Needs at least {READINESS_LOOKBACK_DAYS} days of recent data "
            f"(has {len(recent_statuses)})."
        )
        ready = False
    else:
        nonred = sum(1 for s in recent_statuses if s != "red")
        ratio = nonred / len(recent_statuses)
        if ratio >= READINESS_MIN_NONRED_RATIO:
            reasons.append(
                f"{nonred} of your last {len(recent_statuses)} days have been steady, not "
                "recovery-focused."
            )
        else:
            reasons.append(
                f"Only {nonred} of your last {len(recent_statuses)} days have been steady — "
                "not quite consistent enough yet."
            )
            ready = False

    if latest_baseline_confidence in READY_BASELINE_CONFIDENCE_LABELS:
        reasons.append(
            f"Your personal baseline confidence is '{latest_baseline_confidence}' — enough "
            "data to trust it."
        )
    else:
        reasons.append("Your personal baseline needs a bit more data before it's reliable.")
        ready = False

    declining = sum(1 for d in trend_directions if d == "declining")
    if declining == 0:
        reasons.append("None of your tracked exercises are trending down.")
    else:
        reasons.append(
            f"{declining} of your tracked exercises {'is' if declining == 1 else 'are'} "
            "trending down — worth giving it more time."
        )
        ready = False

    return ReadinessResult(ready=ready, reasons=reasons)


def build_target_milestones(track: str, snapshot: dict) -> dict:
    if track == "repair":
        return {
            "goal": "stability",
            "target_stable_days": REPAIR_TARGET_STABLE_DAYS,
            "description": (
                "Maintain consistent, comfortable measurements with no flagged anomalies for "
                f"{REPAIR_TARGET_STABLE_DAYS} days."
            ),
        }
    if track == "improvement":
        return {
            "goal": "range_extension",
            "target_semitones": IMPROVEMENT_TARGET_SEMITONES,
            "from_note": snapshot.get("comfortable_high_note"),
            "description": (
                "Gently extend your comfortable high note by about "
                f"{IMPROVEMENT_TARGET_SEMITONES} semitones over 90 days — only ever when it "
                "feels safe, never forced."
            ),
        }
    raise ValueError(f"Unknown track: {track!r}")


def plan_end_date(start_date: date) -> date:
    return start_date + timedelta(days=PLAN_DURATION_DAYS)


# --- Data access & orchestration (talks to the DB; pure functions above don't) ---


def build_assessment_snapshot(db: Session, user_id: uuid.UUID) -> dict | None:
    """A plan needs *some* real, already-measured data before it can be generated — reuses the
    most recent sustained-phonation recording (Stage 2/3) and the most recent vocal range entry
    (Stage 8) rather than requiring a new, separate "assessment" recording flow. Returns None
    (never a fabricated plan) if either is missing."""
    latest_measurement = db.execute(
        select(AcousticMeasurement)
        .join(Recording, Recording.id == AcousticMeasurement.recording_id)
        .join(VoiceSession, VoiceSession.id == Recording.voice_session_id)
        .where(VoiceSession.user_id == user_id)
        .order_by(Recording.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    latest_range = db.scalar(
        select(VocalRange)
        .where(VocalRange.user_id == user_id)
        .order_by(VocalRange.measured_at.desc())
    )

    if latest_measurement is None or latest_range is None:
        return None
    if latest_range.comfortable_low_note is None and latest_range.comfortable_high_note is None:
        return None

    return {
        "f0_mean_hz": latest_measurement.f0_mean_hz,
        "jitter_percent": latest_measurement.jitter_percent,
        "shimmer_percent": latest_measurement.shimmer_percent,
        "hnr_db": latest_measurement.hnr_db,
        "comfortable_low_note": latest_range.comfortable_low_note,
        "comfortable_high_note": latest_range.comfortable_high_note,
        "falsetto_high_note": latest_range.falsetto_high_note,
    }


def create_plan(db: Session, user_id: uuid.UUID, track: str, for_date: date) -> VocalPlan | None:
    """Supersedes any current active plan and creates a new one from the latest available
    assessment data. Returns None (never fabricates a plan) if there isn't enough data yet."""
    snapshot = build_assessment_snapshot(db, user_id)
    if snapshot is None:
        return None

    existing_active = db.scalars(
        select(VocalPlan).where(VocalPlan.user_id == user_id, VocalPlan.status == "active")
    ).all()
    for old_plan in existing_active:
        old_plan.status = "superseded"

    new_plan = VocalPlan(
        user_id=user_id,
        track=track,
        start_date=for_date,
        target_end_date=plan_end_date(for_date),
        status="active",
        baseline_snapshot=snapshot,
        target_milestones=build_target_milestones(track, snapshot),
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan


def ensure_plan_exists(db: Session, user_id: uuid.UUID, for_date: date) -> VocalPlan | None:
    """Called again after each new recording/vocal-range submission, so the very first plan
    appears as soon as there's enough data to build one, without waiting on any other action —
    matching "it will start you ... with a recommended 90-day plan" as soon as the AI has heard
    the user's voice. A no-op once any active plan exists, whatever its track: `create_plan`
    always supersedes the current active plan, so calling it unconditionally here would restart
    the 90-day clock on every unrelated submission. See `sync_plan_to_track` for the "user just
    changed their track" case, which this deliberately does not handle."""
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is None or profile.track is None:
        return None

    existing = db.scalar(
        select(VocalPlan).where(VocalPlan.user_id == user_id, VocalPlan.status == "active")
    )
    if existing is not None:
        return existing

    return create_plan(db, user_id, profile.track, for_date)


def sync_plan_to_track(
    db: Session, user_id: uuid.UUID, track: str, for_date: date
) -> VocalPlan | None:
    """Called right after the user explicitly chooses a track (PATCH /profile/track) — unlike
    `ensure_plan_exists`, which never touches an already-active plan, this always produces a
    plan matching the track just chosen: creating one if none exists yet, and replacing a
    still-active plan that's left over from a different track (a deliberate manual switch is a
    strong enough signal to restart the 90-day clock, unlike an unrelated data submission)."""
    existing = db.scalar(
        select(VocalPlan).where(VocalPlan.user_id == user_id, VocalPlan.status == "active")
    )
    if existing is not None and existing.track == track:
        return existing

    return create_plan(db, user_id, track, for_date)


def _gather_readiness_inputs(
    db: Session, user_id: uuid.UUID, for_date: date
) -> tuple[list[str], str | None, list[str]]:
    cutoff = for_date - timedelta(days=READINESS_LOOKBACK_DAYS)
    score_rows = db.scalars(
        select(RecoveryScore)
        .where(
            RecoveryScore.user_id == user_id,
            RecoveryScore.score_date >= cutoff,
            RecoveryScore.score_date <= for_date,
        )
        .order_by(RecoveryScore.score_date)
    ).all()
    statuses = [
        row.components["status"]
        for row in score_rows
        if row.components and "status" in row.components
    ]

    latest_baseline = db.scalar(
        select(Baseline).where(Baseline.user_id == user_id).order_by(Baseline.updated_at.desc())
    )
    confidence = latest_baseline.confidence_label if latest_baseline else None

    trends = compute_exercise_trends(db, user_id)
    directions = [t.direction for t in trends]

    return statuses, confidence, directions


@dataclass
class PlanView:
    plan: VocalPlan | None
    readiness: ReadinessResult | None
    just_graduated: bool


def get_active_plan(db: Session, user_id: uuid.UUID, for_date: date) -> PlanView:
    """The read path for GET /api/v1/vocal-plan. On a Repair-track plan, also checks
    graduation readiness and auto-graduates to Improvement (superseding the old plan, flipping
    UserProfile.track, generating a fresh plan from current data) when every criterion passes —
    matching "once it feels like you have repaired your voice it will move you to
    improvement... after hearing your voice with a recommended 90-day plan.\""""
    plan = db.scalar(
        select(VocalPlan)
        .where(VocalPlan.user_id == user_id, VocalPlan.status == "active")
        .order_by(VocalPlan.created_at.desc())
    )

    if plan is None or plan.track != "repair":
        return PlanView(plan=plan, readiness=None, just_graduated=False)

    statuses, confidence, directions = _gather_readiness_inputs(db, user_id, for_date)
    readiness = assess_graduation_readiness(statuses, confidence, directions)

    if not readiness.ready:
        return PlanView(plan=plan, readiness=readiness, just_graduated=False)

    graduated_plan = create_plan(db, user_id, "improvement", for_date)
    if graduated_plan is None:
        # Snapshot data disappeared between the readiness check and now (shouldn't happen in
        # practice) -- stay on the current plan rather than graduate without a real plan.
        return PlanView(plan=plan, readiness=readiness, just_graduated=False)

    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is not None:
        profile.track = "improvement"
        db.commit()

    return PlanView(plan=graduated_plan, readiness=readiness, just_graduated=True)
