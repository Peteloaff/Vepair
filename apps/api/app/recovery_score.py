"""VepAIr Daily Recovery Score (Stage 5).

Per the product brief: "This is NOT a medical score. It is an individualized training/recovery
indicator." Nothing here observes anatomy or names a pathology — see MEDICAL_SAFETY.md.

**Every component is either an objective measurement compared to the user's own history, or a
direct readout of something the user self-reported that day** — never a population norm, never
an invented "normal" jitter/shimmer/sleep threshold presented as clinical fact. This keeps faith
with the product's core principle ("personal baseline before population assumptions",
ROADMAP.md) even in a component the brief calls "Acoustic Stability": rather than scoring
today's jitter/shimmer against some external "healthy voice" range (which would be exactly the
kind of population-norm claim VepAIr avoids), it's scored against the user's own historical
typical range via the same modified-z-score machinery Stage 4 already built.

**Two components from the brief's list are deliberately deferred, not fabricated:**
- *Vocal Range* needs Stage 8's range-mapping data, which doesn't exist yet.
- *Vocal Endurance* needs within/across-session decline tracking, which nothing captures yet.

**"Recording Confidence" is not a weighted component here.** Folding "how much data do we have"
into the same weighted average as "how good is today" would conflate two different questions.
Instead it drives the separate `confidence_label` returned alongside the score — matching the
brief's own worked example ("Score 72 / Confidence: Moderate": two separate numbers, not one).
"""

import statistics
import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from vepair_audio_engine.measurements import SUSTAINED_PHONATION_SAMPLE_TYPES

from app.baseline import (
    MIN_SAMPLES_FOR_ANOMALY_DETECTION,
    VOICE_METRICS,
    AnomalyResult,
    BaselineStats,
    detect_anomaly,
)
from app.models import (
    AcousticMeasurement,
    Baseline,
    DailyCheckIn,
    Recording,
    RecoveryScore,
    VoiceSession,
)

# Acoustic-only "how steady was today's voice" signal (within-recording periodicity/clarity
# measures) versus "are today's overall readings typical for you" (levels, not steadiness).
# Together they cover exactly the 9 VOICE_METRICS from app/baseline.py — nothing invented, no
# metric double-counted.
ACOUSTIC_STABILITY_METRICS: tuple[str, ...] = (
    "jitter_percent",
    "shimmer_percent",
    "hnr_db",
    "pitch_stability_semitones",
)
CONSISTENCY_METRICS: tuple[str, ...] = (
    "f0_mean_hz",
    "f0_min_hz",
    "f0_max_hz",
    "rms_loudness",
    "duration_seconds",
)
assert set(ACOUSTIC_STABILITY_METRICS) | set(CONSISTENCY_METRICS) == set(VOICE_METRICS)

# Weights sum to 1.0. Objective/measured components (consistency + acoustic stability, 0.40
# combined) are weighted about as heavily as all four subjective self-report components
# combined (0.60) — reflecting "measurement before AI" from ROADMAP.md's guiding principles —
# but no single component exceeds 0.20 of the total, so no one factor (e.g. one bad night's
# sleep) can single-handedly crater the score. Directly supports the Stage 5 test requirement
# "poor sleep alone doesn't falsely indicate vocal injury."
COMPONENT_WEIGHTS: dict[str, float] = {
    "consistency_vs_baseline": 0.20,
    "acoustic_stability": 0.20,
    "subjective_fatigue": 0.20,
    "sleep": 0.15,
    "recent_vocal_load": 0.15,
    "hydration": 0.10,
}

COMPONENT_LABELS: dict[str, str] = {
    "consistency_vs_baseline": "Consistency vs. personal baseline",
    "acoustic_stability": "Acoustic stability",
    "subjective_fatigue": "Subjective fatigue",
    "sleep": "Sleep",
    "recent_vocal_load": "Recent vocal load",
    "hydration": "Hydration self-report",
}

# 0-10 scale (matches DailyCheckIn.throat_discomfort). At or above this, the day is always
# recovery-focused regardless of every other component — a hard safety rule, not something
# that can be outvoted by good acoustic numbers or a good night's sleep. See MEDICAL_SAFETY.md
# section 3 (escalation language).
DISCOMFORT_SAFETY_THRESHOLD = 7

SAFETY_MESSAGE = (
    "Consider reducing vocal load and consulting a qualified voice professional if this "
    "persists, or if you have pain, sudden voice loss, breathing difficulty, coughing blood, "
    "or other concerning symptoms."
)

GREEN_THRESHOLD = 70
YELLOW_THRESHOLD = 40

# What a component with no data today is treated as when blending into the total — see
# compute_recovery_score. Deliberately the exact midpoint of the 0-100 scale: "unknown" must
# never read as either good or bad.
NEUTRAL_COMPONENT_SCORE = 50.0

STATUS_LABELS: dict[str, str] = {
    "green": "Normal training",
    "yellow": "Reduced vocal load recommended",
    "red": "Recovery-focused day",
    "unknown": "Not enough data yet",
}

# A factor is only surfaced in the "why did I get this score?" explanation if it's clearly
# above/below neutral (50) — small, unremarkable deviations aren't worth mentioning, matching
# the brief's own example (which lists several factors, not every component).
POSITIVE_FACTOR_THRESHOLD = 75.0
NEGATIVE_FACTOR_THRESHOLD = 35.0

_LOAD_SCORES: dict[str, float] = {"none": 100.0, "low": 80.0, "moderate": 50.0, "high": 20.0}
# "Hydration" is a plain self-report of how hydrated the user felt, not an exposure/risk field
# (contrast alcohol_exposure/smoke_vape_exposure, which are genuinely risk fields) — "high"
# reads as well-hydrated, "none" as not hydrated at all.
_HYDRATION_SCORES: dict[str, float] = {"none": 20.0, "low": 40.0, "moderate": 70.0, "high": 100.0}


@dataclass
class ComponentScore:
    key: str
    label: str
    score: float | None  # 0-100; None means excluded from the weighted average (no data today)
    weight: float


@dataclass
class RecoveryScoreResult:
    score_date: date
    score_value: int | None
    confidence_label: str
    status: str
    status_label: str
    safety_message: str | None
    components: list[ComponentScore]
    factors: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "score_date": self.score_date.isoformat(),
            "score_value": self.score_value,
            "confidence_label": self.confidence_label,
            "status": self.status,
            "status_label": self.status_label,
            "safety_message": self.safety_message,
            "components": [
                {
                    "key": c.key,
                    "label": c.label,
                    "score": c.score,
                    "weight": c.weight,
                    "included": c.score is not None,
                }
                for c in self.components
            ],
            "factors": self.factors,
        }


def _typicality_score_from_z(modified_z_score: float) -> float:
    """Maps a modified z-score (see app/baseline.py) to a 0-100 "how typical is this for you"
    score: 0 -> 100, Stage 4's own anomaly threshold (3.5) -> 50, 7+ -> 0 (clamped). Linear and
    simple on purpose — this score is shown to users, and a more elaborate curve would imply
    more statistical rigor than a home-recorded voice sample actually supports. Handles the
    zero-MAD fallback's `inf` z-score (see app/baseline.py) as the same floor as any other
    far-outside-normal value, rather than propagating infinity into the score."""
    if modified_z_score == float("inf") or modified_z_score == float("-inf"):
        return 0.0
    return max(0.0, 100.0 - (abs(modified_z_score) / 7.0) * 100.0)


def score_from_anomaly_results(results: list[AnomalyResult]) -> float | None:
    if not results:
        return None
    return statistics.mean(_typicality_score_from_z(r.modified_z_score) for r in results)


def score_subjective_fatigue(fatigue: int | None) -> float | None:
    """fatigue is 1 (none) - 10 (severe); score is the inverse, 0-100."""
    if fatigue is None:
        return None
    return max(0.0, min(100.0, (10 - fatigue) / 9 * 100))


def score_sleep(sleep_hours: float | None) -> float | None:
    """Peaks at 8 hours, falls off symmetrically, reaching 0 at 2h or 14h. A general
    wellness heuristic, not a vocal-health-specific or clinical claim."""
    if sleep_hours is None:
        return None
    return max(0.0, 100.0 - abs(sleep_hours - 8.0) * (100.0 / 6.0))


def score_recent_vocal_load(
    speaking_load: str | None,
    singing_load: str | None,
    rehearsal_or_performance_yesterday: bool | None,
) -> float | None:
    loads = [
        _LOAD_SCORES[load] for load in (speaking_load, singing_load) if load in _LOAD_SCORES
    ]
    if not loads:
        return None
    # The more demanding of the two reported loads dominates — a light speaking day doesn't
    # cancel out a heavy singing day.
    result = min(loads)
    if rehearsal_or_performance_yesterday:
        result = max(0.0, result - 15.0)
    return result


def score_hydration(hydration_estimate: str | None) -> float | None:
    if hydration_estimate not in _HYDRATION_SCORES:
        return None
    return _HYDRATION_SCORES[hydration_estimate]


def confidence_label_from_coverage(available_count: int, total_count: int) -> str:
    """Data-sufficiency indicator, not a statistical probability — see MEDICAL_SAFETY.md
    section 4. Based on how many of today's possible components actually had data, not on how
    good the score is."""
    if available_count <= 0:
        return "insufficient"
    ratio = available_count / total_count
    if ratio >= 5 / 6:
        return "high"
    if ratio >= 3 / 6:
        return "moderate"
    return "low"


def status_from_score(
    score_value: int | None, throat_discomfort: int | None
) -> tuple[str, str, str | None]:
    """Returns (status, status_label, safety_message). Discomfort is a hard override, never
    just one weighted factor among others — see DISCOMFORT_SAFETY_THRESHOLD."""
    if throat_discomfort is not None and throat_discomfort >= DISCOMFORT_SAFETY_THRESHOLD:
        return "red", STATUS_LABELS["red"], SAFETY_MESSAGE
    if score_value is None:
        return "unknown", STATUS_LABELS["unknown"], None
    if score_value >= GREEN_THRESHOLD:
        return "green", STATUS_LABELS["green"], None
    if score_value >= YELLOW_THRESHOLD:
        return "yellow", STATUS_LABELS["yellow"], None
    return "red", STATUS_LABELS["red"], None


_FACTOR_TEXT: dict[str, dict[str, str]] = {
    "consistency_vs_baseline": {
        "positive": "Today's voice measurements are close to your personal baseline.",
        "negative": "Several acoustic measurements are different from your personal baseline.",
    },
    "acoustic_stability": {
        "positive": "Your voice sounded steady in today's recording.",
        "negative": "Your voice sounded less steady than usual in today's recording.",
    },
    "subjective_fatigue": {
        "positive": "You reported low fatigue.",
        "negative": "You reported higher-than-usual fatigue.",
    },
    "sleep": {
        "positive": "You got a good night's sleep.",
        "negative": "Your reported sleep was outside your comfortable range.",
    },
    "recent_vocal_load": {
        "positive": "Low reported vocal load recently.",
        "negative": "Heavy reported vocal load recently.",
    },
    "hydration": {
        "positive": "Good reported hydration.",
        "negative": "Low reported hydration.",
    },
}


def build_factors(components: list[ComponentScore]) -> list[dict]:
    """Derived directly from the same component scores the total is computed from — never a
    separate narrative-generation path — so the explanation is guaranteed to mathematically
    match the score, not just plausibly describe it."""
    factors = []
    for c in components:
        if c.score is None:
            continue
        if c.score >= POSITIVE_FACTOR_THRESHOLD:
            factors.append({"direction": "positive", "text": _FACTOR_TEXT[c.key]["positive"]})
        elif c.score <= NEGATIVE_FACTOR_THRESHOLD:
            factors.append({"direction": "negative", "text": _FACTOR_TEXT[c.key]["negative"]})
    return factors


def compute_recovery_score(
    component_scores: dict[str, float | None],
    throat_discomfort: int | None,
    score_date: date,
) -> RecoveryScoreResult:
    """Pure aggregation: given each component's 0-100 score (or None if that component has no
    data today), returns the weighted total, confidence, status, and explanation. Deterministic
    — the same input always produces the same output; `score_date` is a label supplied by the
    caller, never read from the clock."""
    components = [
        ComponentScore(
            key=key, label=COMPONENT_LABELS[key], score=component_scores.get(key), weight=weight
        )
        for key, weight in COMPONENT_WEIGHTS.items()
    ]
    available = [c for c in components if c.score is not None]

    if available:
        # Components with no data today regress toward neutral (50) rather than being
        # dropped and renormalized — otherwise, on a day with only one component available,
        # that single component *would be* the entire score. Weights always sum to 1.0, so a
        # single component (max weight 0.20) can pull the blended score at most 10 points away
        # from neutral in either direction — directly why one bad night's sleep, reported
        # alone, lands in "reduced load" territory rather than a false "recovery-focused day."
        weighted_sum = sum(
            c.weight * (c.score if c.score is not None else NEUTRAL_COMPONENT_SCORE)
            for c in components
        )
        score_value = round(weighted_sum)
    else:
        score_value = None

    confidence_label = confidence_label_from_coverage(len(available), len(COMPONENT_WEIGHTS))
    status, status_label, safety_message = status_from_score(score_value, throat_discomfort)
    factors = build_factors(components)

    return RecoveryScoreResult(
        score_date=score_date,
        score_value=score_value,
        confidence_label=confidence_label,
        status=status,
        status_label=status_label,
        safety_message=safety_message,
        components=components,
        factors=factors,
    )


# --- Data access & orchestration (talks to the DB; pure functions above don't) ---


def _fetch_stored_baselines(db: Session, user_id: uuid.UUID) -> dict[str, Baseline]:
    rows = db.scalars(
        select(Baseline).where(Baseline.user_id == user_id, Baseline.metric_name.in_(VOICE_METRICS))
    ).all()
    return {row.metric_name: row for row in rows}


def _fetch_todays_measurement_values(
    db: Session, user_id: uuid.UUID, score_date: date
) -> dict[str, list[float]]:
    """Every value recorded that day for each voice metric, from sustained-phonation
    recordings only (the same scope Stage 4's baseline is built from)."""
    stmt = (
        select(AcousticMeasurement, Recording)
        .join(Recording, Recording.id == AcousticMeasurement.recording_id)
        .join(VoiceSession, VoiceSession.id == Recording.voice_session_id)
        .where(
            VoiceSession.user_id == user_id,
            Recording.sample_type.in_(SUSTAINED_PHONATION_SAMPLE_TYPES),
            func.date(Recording.created_at) == score_date,
        )
    )
    values: dict[str, list[float]] = {metric: [] for metric in VOICE_METRICS}
    for measurement, recording in db.execute(stmt).all():
        for metric in VOICE_METRICS:
            value = (
                recording.duration_seconds
                if metric == "duration_seconds"
                else getattr(measurement, metric)
            )
            if value is not None:
                values[metric].append(value)
    return values


def _score_metric_group(
    metric_group: tuple[str, ...],
    todays_values: dict[str, list[float]],
    baselines: dict[str, Baseline],
) -> float | None:
    results: list[AnomalyResult] = []
    for metric in metric_group:
        stats_row = baselines.get(metric)
        if stats_row is None or stats_row.sample_count < MIN_SAMPLES_FOR_ANOMALY_DETECTION:
            continue
        stats = BaselineStats(
            metric_name=metric,
            median_value=stats_row.median_value,
            mad_value=stats_row.mad_value,
            sample_count=stats_row.sample_count,
            window_start=stats_row.window_start,
            window_end=stats_row.window_end,
        )
        for value in todays_values.get(metric, []):
            result = detect_anomaly(metric, value, stats)
            if result is not None:
                results.append(result)
    return score_from_anomaly_results(results)


def compute_and_store_recovery_score(
    db: Session, user_id: uuid.UUID, score_date: date
) -> RecoveryScoreResult:
    checkin = db.scalar(
        select(DailyCheckIn).where(
            DailyCheckIn.user_id == user_id, DailyCheckIn.checkin_date == score_date
        )
    )
    baselines = _fetch_stored_baselines(db, user_id)
    todays_values = _fetch_todays_measurement_values(db, user_id, score_date)

    component_scores = {
        "consistency_vs_baseline": _score_metric_group(
            CONSISTENCY_METRICS, todays_values, baselines
        ),
        "acoustic_stability": _score_metric_group(
            ACOUSTIC_STABILITY_METRICS, todays_values, baselines
        ),
        "subjective_fatigue": score_subjective_fatigue(checkin.fatigue if checkin else None),
        "sleep": score_sleep(checkin.sleep_hours if checkin else None),
        "recent_vocal_load": score_recent_vocal_load(
            checkin.speaking_load if checkin else None,
            checkin.singing_load if checkin else None,
            checkin.rehearsal_or_performance_yesterday if checkin else None,
        ),
        "hydration": score_hydration(checkin.hydration_estimate if checkin else None),
    }

    result = compute_recovery_score(
        component_scores, checkin.throat_discomfort if checkin else None, score_date
    )

    existing = db.scalar(
        select(RecoveryScore).where(
            RecoveryScore.user_id == user_id, RecoveryScore.score_date == score_date
        )
    )
    if existing is None:
        existing = RecoveryScore(user_id=user_id, score_date=score_date)
        db.add(existing)
    existing.score_value = result.score_value
    existing.confidence_label = result.confidence_label
    existing.components = result.as_dict()
    db.commit()

    return result


@dataclass
class ScoreHistoryPoint:
    score_date: date
    score_value: int | None
    confidence_label: str | None
    status: str | None
    # The "acoustic_stability" component's own score (0-100, "how typical vs. your baseline"),
    # pulled back out of the stored components breakdown -- see compute_and_store_recovery_score's
    # `existing.components = result.as_dict()`. Exposed separately (rather than only as part of
    # the blended total) for the coach dashboard's Stability tile, which needs this one component
    # trended on its own, not folded into the six-component weighted score.
    acoustic_stability_score: float | None


def fetch_score_history(
    db: Session, user_id: uuid.UUID, from_date: date, to_date: date
) -> list[ScoreHistoryPoint]:
    """Stage 11: read-only over whatever `RecoveryScore` rows already exist in the range — never
    computes or stores a score for a day that doesn't already have one. A day only has a stored
    row because something (a dashboard visit, an API call) already triggered
    `compute_and_store_recovery_score` for it in the past; this never backfills, since doing so
    would score that old day's raw measurements against *today's* baseline rather than
    whatever was true at the time, silently producing a different number than what may already
    be shown elsewhere for that date. Gaps in the returned list are real — they mean no score
    was ever computed that day, not something to paper over."""
    rows = db.scalars(
        select(RecoveryScore)
        .where(
            RecoveryScore.user_id == user_id,
            RecoveryScore.score_date >= from_date,
            RecoveryScore.score_date <= to_date,
        )
        .order_by(RecoveryScore.score_date)
    ).all()
    result = []
    for row in rows:
        stored = row.components or {}
        stability = next(
            (
                c.get("score")
                for c in stored.get("components", [])
                if c.get("key") == "acoustic_stability"
            ),
            None,
        )
        result.append(
            ScoreHistoryPoint(
                score_date=row.score_date,
                score_value=row.score_value,
                confidence_label=row.confidence_label,
                status=stored.get("status"),
                acoustic_stability_score=stability,
            )
        )
    return result
