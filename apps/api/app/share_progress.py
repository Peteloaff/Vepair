"""Stage 10: Share My Progress.

Builds the data for exactly two read-only summary views — "Today's Voice" (a snapshot) and "My
Progress" (a start-vs-now comparison) — entirely from data VepAIr already measures. **This
module never computes a new statistic that isn't already trusted elsewhere in the app**: it
either reads stored values directly, or re-runs the exact same pure functions
`recovery_score.py`/`baseline.py`/`vocal_range.py` already use, never a second, divergent
implementation of the same calculation. It never writes anything except the one already-existing
side effect `compute_and_store_recovery_score` has always had for *today's* row (unchanged from
Stage 5) — nothing here ever recomputes or overwrites a past day's stored data. See
MEDICAL_SAFETY.md and PRIVACY.md; every field here is either already public elsewhere in the app
or a plain aggregate of the user's own data — no email, account ID, location, or raw notes.

**A field with no real data behind it is omitted, never fabricated or estimated** — every field
below is `None`-able for exactly that reason.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from vepair_audio_engine.measurements import SUSTAINED_PHONATION_SAMPLE_TYPES

from app.baseline import (
    BaselineStats,
    compute_all_voice_baselines,
    compute_fatigue_baseline,
    confidence_from_session_count,
    detect_anomaly,
    usable_voice_session_count,
)
from app.models import (
    AcousticMeasurement,
    DailyCheckIn,
    ExerciseResult,
    ExerciseSession,
    Recording,
    RecoveryScore,
    VoiceSession,
)
from app.recovery_score import (
    ACOUSTIC_STABILITY_METRICS,
    compute_and_store_recovery_score,
    score_from_anomaly_results,
)
from app.vocal_range import build_summary as build_vocal_range_summary
from app.vocal_range import semitones_between

# Mirrors recovery_score.py's own (module-private) load ordering — kept as a small, separately
# maintained copy rather than importing a private name across modules. "The more demanding of
# the two reported loads" is displayed, matching how the daily score already treats load.
_LOAD_RANK: dict[str, int] = {"none": 0, "low": 1, "moderate": 2, "high": 3}

LOW_CONFIDENCE_LABELS = frozenset({"insufficient", "low"})

START_BASIS_ESTABLISHED = "established_baseline"
START_BASIS_FIRST_SESSION = "first_valid_session"


@dataclass
class TodaySnapshot:
    for_date: date
    score_value: int | None
    score_delta: int | None
    measurement_confidence_label: str | None
    low_measurement_confidence: bool
    comfortable_low_note: str | None
    comfortable_high_note: str | None
    range_span_semitones: int | None
    pitch_stability_pct: float | None
    vocal_endurance_seconds: float | None
    reported_fatigue: int | None
    vocal_load: str | None
    training_completed_pct: float | None


@dataclass
class RangeProgress:
    start_low_note: str | None
    start_high_note: str | None
    now_low_note: str | None
    now_high_note: str | None
    high_note_semitone_delta: int | None
    start_basis: str


@dataclass
class NumericProgress:
    start_value: float
    now_value: float
    delta: float
    start_basis: str


@dataclass
class ProgressSnapshot:
    for_date: date
    insufficient_data: bool
    valid_session_count: int
    comfortable_range: RangeProgress | None
    pitch_stability_pct: NumericProgress | None
    vocal_endurance_seconds: NumericProgress | None
    reported_fatigue: NumericProgress | None
    days_tracked: int
    sessions_completed: int
    training_compliance_pct: float | None


def _higher_load(speaking_load: str | None, singing_load: str | None) -> str | None:
    candidates = [load for load in (speaking_load, singing_load) if load in _LOAD_RANK]
    if not candidates:
        return None
    return max(candidates, key=lambda load: _LOAD_RANK[load])


def _sustained_rows(
    db: Session, user_id: uuid.UUID, *, on_date: date | None = None
) -> list[tuple[Recording, AcousticMeasurement]]:
    """All sustained-phonation (Recording, AcousticMeasurement) pairs for a user, oldest first,
    optionally restricted to one calendar date. The same scope baseline.py/recovery_score.py
    already use for these metrics."""
    stmt = (
        select(Recording, AcousticMeasurement)
        .join(AcousticMeasurement, AcousticMeasurement.recording_id == Recording.id)
        .join(VoiceSession, VoiceSession.id == Recording.voice_session_id)
        .where(
            VoiceSession.user_id == user_id,
            Recording.sample_type.in_(SUSTAINED_PHONATION_SAMPLE_TYPES),
        )
        .order_by(Recording.created_at.asc())
    )
    rows = [(r, m) for r, m in db.execute(stmt).all()]
    if on_date is not None:
        rows = [(r, m) for r, m in rows if r.created_at.date() == on_date]
    return rows


def _acoustic_stability_score(
    values: dict[str, float], baselines: dict[str, BaselineStats]
) -> float | None:
    """The exact scoring methodology recovery_score.py's `acoustic_stability` component uses
    (`detect_anomaly` + `score_from_anomaly_results`), applied here to a single recording's raw
    values instead of a whole day's — used to compute a real, non-fabricated "how typical was
    this session" percentage for any historical recording, without ever recomputing or storing
    a past day's RecoveryScore row."""
    results = []
    for metric in ACOUSTIC_STABILITY_METRICS:
        value = values.get(metric)
        stats = baselines.get(metric)
        if value is None or stats is None:
            continue
        result = detect_anomaly(metric, value, stats)
        if result is not None:
            results.append(result)
    return score_from_anomaly_results(results)


# --- Today's Voice ---


def build_today_snapshot(db: Session, user_id: uuid.UUID, for_date: date) -> TodaySnapshot:
    score_result = compute_and_store_recovery_score(db, user_id, for_date)
    yesterday = for_date - timedelta(days=1)
    yesterday_row = db.scalar(
        select(RecoveryScore).where(
            RecoveryScore.user_id == user_id, RecoveryScore.score_date == yesterday
        )
    )
    score_delta = (
        score_result.score_value - yesterday_row.score_value
        if score_result.score_value is not None
        and yesterday_row is not None
        and yesterday_row.score_value is not None
        else None
    )

    low_confidence = score_result.confidence_label in LOW_CONFIDENCE_LABELS
    pitch_stability_pct = None
    if not low_confidence:
        acoustic_stability = next(
            (c for c in score_result.components if c.key == "acoustic_stability"), None
        )
        if acoustic_stability is not None:
            pitch_stability_pct = acoustic_stability.score

    range_summary = build_vocal_range_summary(db, user_id, recovery_status=score_result.status)
    range_span = (
        semitones_between(range_summary.current_low_note, range_summary.current_high_note)
        if range_summary.current_low_note and range_summary.current_high_note
        else None
    )

    todays_sustained = _sustained_rows(db, user_id, on_date=for_date)
    endurance_values = [
        m.longest_voiced_run_seconds for _r, m in todays_sustained if m.longest_voiced_run_seconds
    ]
    vocal_endurance = max(endurance_values) if endurance_values else None

    checkin = db.scalar(
        select(DailyCheckIn).where(
            DailyCheckIn.user_id == user_id, DailyCheckIn.checkin_date == for_date
        )
    )

    todays_session = db.scalar(
        select(ExerciseSession)
        .where(ExerciseSession.user_id == user_id)
        .order_by(ExerciseSession.started_at.desc())
    )
    training_completed_pct = None
    if todays_session is not None and todays_session.started_at.date() == for_date:
        results = db.scalars(
            select(ExerciseResult).where(ExerciseResult.exercise_session_id == todays_session.id)
        ).all()
        if results:
            training_completed_pct = round(
                100 * sum(1 for r in results if r.completed) / len(results), 1
            )

    return TodaySnapshot(
        for_date=for_date,
        score_value=score_result.score_value,
        score_delta=score_delta,
        measurement_confidence_label=score_result.confidence_label,
        low_measurement_confidence=low_confidence,
        comfortable_low_note=range_summary.current_low_note,
        comfortable_high_note=range_summary.current_high_note,
        range_span_semitones=range_span,
        pitch_stability_pct=pitch_stability_pct,
        vocal_endurance_seconds=vocal_endurance,
        reported_fatigue=checkin.fatigue if checkin else None,
        vocal_load=(
            _higher_load(checkin.speaking_load, checkin.singing_load) if checkin else None
        ),
        training_completed_pct=training_completed_pct,
    )


# --- My Progress ---


def _range_progress(db: Session, user_id: uuid.UUID, score_status: str) -> RangeProgress | None:
    summary = build_vocal_range_summary(db, user_id, recovery_status=score_status)
    if not summary.history:
        return None
    start_entry = summary.history[0]
    start_low = start_entry["comfortable_low_note"]
    start_high = start_entry["comfortable_high_note"]
    if start_high is None and start_low is None:
        return None
    delta = (
        semitones_between(start_high, summary.current_high_note)
        if start_high and summary.current_high_note
        else None
    )
    # VocalRange has no baseline/"established" concept of its own (see vocal_range.py) — the
    # comparison is always against the earliest recorded attempt.
    return RangeProgress(
        start_low_note=start_low,
        start_high_note=start_high,
        now_low_note=summary.current_low_note,
        now_high_note=summary.current_high_note,
        high_note_semitone_delta=delta,
        start_basis=START_BASIS_FIRST_SESSION,
    )


def _acoustic_metric_progress(
    db: Session, user_id: uuid.UUID, for_date: date
) -> NumericProgress | None:
    rows = _sustained_rows(db, user_id)
    if not rows:
        return None

    baselines = compute_all_voice_baselines(db, user_id)
    session_count = usable_voice_session_count(db, user_id)
    _pct, confidence_label = confidence_from_session_count(session_count)

    start_recording, start_measurement = rows[0]
    start_values = {
        metric: getattr(start_measurement, metric) for metric in ACOUSTIC_STABILITY_METRICS
    }
    start_score = _acoustic_stability_score(start_values, baselines)
    if start_score is None:
        return None

    now_result = compute_and_store_recovery_score(db, user_id, for_date)
    now_acoustic = next(
        (c for c in now_result.components if c.key == "acoustic_stability"), None
    )
    now_score = now_acoustic.score if now_acoustic else None
    if now_score is None:
        return None

    start_basis = (
        START_BASIS_ESTABLISHED if confidence_label == "established" else START_BASIS_FIRST_SESSION
    )
    return NumericProgress(
        start_value=round(start_score, 1),
        now_value=round(now_score, 1),
        delta=round(now_score - start_score, 1),
        start_basis=start_basis,
    )


def _endurance_progress(db: Session, user_id: uuid.UUID) -> NumericProgress | None:
    rows = _sustained_rows(db, user_id)
    values_in_order = [
        (r.created_at, m.longest_voiced_run_seconds)
        for r, m in rows
        if m.longest_voiced_run_seconds
    ]
    if len(values_in_order) < 2:
        return None
    start_value = values_in_order[0][1]
    now_value = max(v for _t, v in values_in_order)
    return NumericProgress(
        start_value=round(start_value, 1),
        now_value=round(now_value, 1),
        delta=round(now_value - start_value, 1),
        # longest_voiced_run_seconds is deliberately not part of app/baseline.py's VOICE_METRICS
        # (see that module's comment) — it never gets an "established baseline," only ever a
        # first-session comparison.
        start_basis=START_BASIS_FIRST_SESSION,
    )


def _fatigue_progress(db: Session, user_id: uuid.UUID) -> NumericProgress | None:
    stats = compute_fatigue_baseline(db, user_id)
    if stats.sample_count == 0:
        return None
    _pct, confidence_label = confidence_from_session_count(stats.sample_count)

    latest_checkin = db.scalar(
        select(DailyCheckIn)
        .where(DailyCheckIn.user_id == user_id, DailyCheckIn.fatigue.isnot(None))
        .order_by(DailyCheckIn.checkin_date.desc())
    )
    if latest_checkin is None:
        return None

    if confidence_label == "established":
        start_value = round(stats.median_value, 1)
        start_basis = START_BASIS_ESTABLISHED
    else:
        earliest_checkin = db.scalar(
            select(DailyCheckIn)
            .where(DailyCheckIn.user_id == user_id, DailyCheckIn.fatigue.isnot(None))
            .order_by(DailyCheckIn.checkin_date.asc())
        )
        start_value = float(earliest_checkin.fatigue)
        start_basis = START_BASIS_FIRST_SESSION

    return NumericProgress(
        start_value=start_value,
        now_value=float(latest_checkin.fatigue),
        delta=round(latest_checkin.fatigue - start_value, 1),
        start_basis=start_basis,
    )


def build_progress_snapshot(db: Session, user_id: uuid.UUID, for_date: date) -> ProgressSnapshot:
    score_result = compute_and_store_recovery_score(db, user_id, for_date)

    comfortable_range = _range_progress(db, user_id, score_result.status)
    pitch_stability = _acoustic_metric_progress(db, user_id, for_date)
    vocal_endurance = _endurance_progress(db, user_id)
    reported_fatigue = _fatigue_progress(db, user_id)

    valid_session_count = usable_voice_session_count(db, user_id)
    insufficient_data = (
        comfortable_range is None
        and pitch_stability is None
        and vocal_endurance is None
        and reported_fatigue is None
    )

    checkin_dates = db.scalars(
        select(DailyCheckIn.checkin_date).where(DailyCheckIn.user_id == user_id).distinct()
    ).all()
    completed_sessions = db.scalars(
        select(ExerciseSession).where(
            ExerciseSession.user_id == user_id, ExerciseSession.completed_at.isnot(None)
        )
    ).all()
    total_sessions = db.scalars(
        select(ExerciseSession).where(ExerciseSession.user_id == user_id)
    ).all()
    training_compliance_pct = (
        round(100 * len(completed_sessions) / len(total_sessions), 1) if total_sessions else None
    )

    return ProgressSnapshot(
        for_date=for_date,
        insufficient_data=insufficient_data,
        valid_session_count=valid_session_count,
        comfortable_range=comfortable_range,
        pitch_stability_pct=pitch_stability,
        vocal_endurance_seconds=vocal_endurance,
        reported_fatigue=reported_fatigue,
        days_tracked=len(checkin_dates),
        sessions_completed=len(completed_sessions),
        training_compliance_pct=training_compliance_pct,
    )
