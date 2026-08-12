"""Personal vocal baseline computation (Stage 4).

Core idea from the product brief: compare a user against **their own voice over time**, not
population norms. Every statistic here is computed from one user's own historical
measurements — nothing here is a clinical reference range.

Robust statistics (median, median absolute deviation) are used deliberately instead of
mean/standard deviation, because they resist being dragged around by a handful of bad
recordings (a phone left near a fan for one session, one clipped take) — exactly the "bad
recordings do not corrupt baseline" and "single anomalies do not permanently shift baseline"
requirements from the Stage 4 test plan. A mean/stddev baseline would not have this property:
one wild outlier shifts the mean and inflates the stddev, silently degrading every future
comparison. See docs/baseline.md for the full methodology and worked examples.
"""

import statistics
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session
from vepair_audio_engine.measurements import SUSTAINED_PHONATION_SAMPLE_TYPES

from app.models import AcousticMeasurement, Baseline, DailyCheckIn, Recording, VoiceSession

# Modified z-score threshold from Iglewicz & Hoaglin's outlier-detection method (a standard,
# published robust-statistics technique — not invented here). |z| > 3.5 is their recommended
# cutoff for "probable outlier."
MODIFIED_Z_SCORE_ANOMALY_THRESHOLD = 3.5

# MAD is a consistent estimator of standard deviation only after this scale factor (assuming
# an approximately normal distribution) — the standard constant used to make modified z-scores
# comparable in scale to ordinary z-scores.
MAD_CONSISTENCY_CONSTANT = 0.6745

# Below this many prior usable sessions, there isn't enough data to trust a MAD-based anomaly
# comparison — a MAD computed from 1-2 points is not a meaningful spread estimate.
MIN_SAMPLES_FOR_ANOMALY_DETECTION = 5

# "Mature" baseline threshold from the product brief: 7-14 usable sessions.
ESTABLISHED_SESSION_COUNT = 14


@dataclass
class BaselineStats:
    metric_name: str
    median_value: float | None
    mad_value: float | None
    sample_count: int
    window_start: date | None
    window_end: date | None

    def as_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "median_value": self.median_value,
            "mad_value": self.mad_value,
            "sample_count": self.sample_count,
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
        }


@dataclass
class AnomalyResult:
    metric_name: str
    current_value: float
    baseline_median: float
    modified_z_score: float
    is_anomaly: bool


def median_absolute_deviation(values: list[float], center: float) -> float:
    """MAD: the median of the absolute deviations from the median. Zero for a perfectly
    uniform set of values (e.g. every recording landed on exactly the same F0) — callers must
    handle a zero MAD explicitly, since dividing by it is undefined."""
    deviations = [abs(v - center) for v in values]
    return statistics.median(deviations)


def confidence_from_session_count(usable_session_count: int) -> tuple[float, str]:
    """Confidence is a product indicator of *data sufficiency*, not a statistical probability
    of anything — see MEDICAL_SAFETY.md. Linear in session count up to the "established"
    threshold: simple and honest, rather than a more elaborate curve that would imply more
    rigor than actually exists here.
    """
    if usable_session_count <= 0:
        return 0.0, "insufficient"

    pct = min(100.0, round(100 * usable_session_count / ESTABLISHED_SESSION_COUNT, 1))

    if usable_session_count >= ESTABLISHED_SESSION_COUNT:
        label = "established"
    elif usable_session_count >= 7:
        label = "developing"
    elif usable_session_count >= 3:
        label = "building"
    else:
        label = "insufficient"

    return pct, label


def compute_baseline_stats(
    metric_name: str, values_with_dates: list[tuple[float, date]]
) -> BaselineStats:
    """Computes robust baseline statistics from a user's own historical values for one
    metric. `values_with_dates` should already be filtered to whatever exclusions the caller
    wants (e.g. excluding the recording currently being analyzed, for unbiased anomaly
    comparison — see `compute_and_store_baselines` in the recordings router)."""
    if not values_with_dates:
        return BaselineStats(
            metric_name=metric_name,
            median_value=None,
            mad_value=None,
            sample_count=0,
            window_start=None,
            window_end=None,
        )

    values = [v for v, _ in values_with_dates]
    dates = [d for _, d in values_with_dates]
    median_value = statistics.median(values)
    mad_value = median_absolute_deviation(values, median_value)

    return BaselineStats(
        metric_name=metric_name,
        median_value=median_value,
        mad_value=mad_value,
        sample_count=len(values),
        window_start=min(dates),
        window_end=max(dates),
    )


def detect_anomaly(
    metric_name: str, current_value: float, stats: BaselineStats
) -> AnomalyResult | None:
    """Returns None if there isn't enough prior data to make a meaningful comparison at all
    (not "no anomaly" — genuinely "can't tell yet"). A zero MAD (every prior value identical)
    means *any* deviation is technically infinite in z-score terms; treated as a max-severity
    anomaly only if the new value actually differs, never a division error.
    """
    if stats.sample_count < MIN_SAMPLES_FOR_ANOMALY_DETECTION or stats.median_value is None:
        return None

    if stats.mad_value is None or stats.mad_value == 0:
        is_different = current_value != stats.median_value
        return AnomalyResult(
            metric_name=metric_name,
            current_value=current_value,
            baseline_median=stats.median_value,
            modified_z_score=float("inf") if is_different else 0.0,
            is_anomaly=is_different,
        )

    modified_z = (
        MAD_CONSISTENCY_CONSTANT * (current_value - stats.median_value) / stats.mad_value
    )
    return AnomalyResult(
        metric_name=metric_name,
        current_value=current_value,
        baseline_median=stats.median_value,
        modified_z_score=modified_z,
        is_anomaly=abs(modified_z) > MODIFIED_Z_SCORE_ANOMALY_THRESHOLD,
    )


# --- Data access & orchestration (talks to the DB; pure functions above don't) ---

# Every voice metric below comes from the same set of "usable sessions" (sustained-phonation
# recordings with a stored AcousticMeasurement), so they share one confidence/session-count
# basis. `duration_seconds` comes from Recording itself, not AcousticMeasurement.
#
# `AcousticMeasurement.longest_voiced_run_seconds` ("Vocal Endurance", Stage 10) is
# deliberately NOT included here: `app/recovery_score.py` asserts every VOICE_METRICS entry is
# claimed by exactly one recovery-score component (ACOUSTIC_STABILITY_METRICS or
# CONSISTENCY_METRICS), so adding it here would silently start feeding it into the daily
# VepAIr Score — Share My Progress is a read-only presentation feature and must never change
# score computation. Its own baseline comparison (Share My Progress "Progress" page) is
# computed directly from AcousticMeasurement history in app/share_progress.py instead.
VOICE_METRICS: tuple[str, ...] = (
    "f0_mean_hz",
    "f0_min_hz",
    "f0_max_hz",
    "pitch_stability_semitones",
    "jitter_percent",
    "shimmer_percent",
    "hnr_db",
    "rms_loudness",
    "duration_seconds",
)

# DailyCheckIn-sourced metrics use check-in count as their own, separate confidence basis --
# journaling consistency isn't the same data stream as recording consistency.
CHECKIN_METRICS: tuple[str, ...] = ("fatigue",)

METRIC_FRIENDLY_NAMES: dict[str, str] = {
    "f0_mean_hz": "average pitch",
    "f0_min_hz": "lowest comfortable pitch",
    "f0_max_hz": "highest comfortable pitch",
    "pitch_stability_semitones": "pitch stability",
    "jitter_percent": "pitch steadiness (jitter)",
    "shimmer_percent": "loudness steadiness (shimmer)",
    "hnr_db": "vocal clarity (harmonics-to-noise ratio)",
    "rms_loudness": "loudness",
    "duration_seconds": "sustained phonation duration",
    "fatigue": "reported fatigue",
}


def anomaly_message(result: AnomalyResult) -> str:
    """Deliberately vague/descriptive, never diagnostic — see MEDICAL_SAFETY.md. Matches the
    product brief's own example phrasing almost verbatim."""
    friendly = METRIC_FRIENDLY_NAMES.get(result.metric_name, result.metric_name)
    return f"Your {friendly} is noticeably different from your recent baseline."


def _fetch_voice_measurement_rows(
    db: Session, user_id: uuid.UUID, exclude_recording_id: uuid.UUID | None = None
) -> list[tuple[Recording, AcousticMeasurement]]:
    stmt = (
        select(Recording, AcousticMeasurement)
        .join(AcousticMeasurement, AcousticMeasurement.recording_id == Recording.id)
        .join(VoiceSession, VoiceSession.id == Recording.voice_session_id)
        .where(
            VoiceSession.user_id == user_id,
            Recording.sample_type.in_(SUSTAINED_PHONATION_SAMPLE_TYPES),
        )
    )
    if exclude_recording_id is not None:
        stmt = stmt.where(Recording.id != exclude_recording_id)
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def _extract_metric_series(
    rows: list[tuple[Recording, AcousticMeasurement]], metric_name: str
) -> list[tuple[float, date]]:
    series = []
    for recording, measurement in rows:
        value = (
            recording.duration_seconds
            if metric_name == "duration_seconds"
            else getattr(measurement, metric_name)
        )
        if value is not None:
            series.append((value, recording.created_at.date()))
    return series


def compute_all_voice_baselines(
    db: Session, user_id: uuid.UUID, exclude_recording_id: uuid.UUID | None = None
) -> dict[str, BaselineStats]:
    rows = _fetch_voice_measurement_rows(db, user_id, exclude_recording_id)
    return {
        metric: compute_baseline_stats(metric, _extract_metric_series(rows, metric))
        for metric in VOICE_METRICS
    }


def usable_voice_session_count(
    db: Session, user_id: uuid.UUID, exclude_recording_id: uuid.UUID | None = None
) -> int:
    rows = _fetch_voice_measurement_rows(db, user_id, exclude_recording_id)
    return len({recording.voice_session_id for recording, _measurement in rows})


def compute_fatigue_baseline(db: Session, user_id: uuid.UUID) -> BaselineStats:
    stmt = select(DailyCheckIn.fatigue, DailyCheckIn.checkin_date).where(
        DailyCheckIn.user_id == user_id, DailyCheckIn.fatigue.isnot(None)
    )
    series = [(fatigue, checkin_date) for fatigue, checkin_date in db.execute(stmt).all()]
    return compute_baseline_stats("fatigue", series)


def upsert_baseline_row(
    db: Session,
    user_id: uuid.UUID,
    stats: BaselineStats,
    confidence_pct: float,
    confidence_label: str,
) -> Baseline:
    existing = db.scalar(
        select(Baseline).where(
            Baseline.user_id == user_id, Baseline.metric_name == stats.metric_name
        )
    )
    today = date.today()
    if existing is None:
        existing = Baseline(
            user_id=user_id,
            metric_name=stats.metric_name,
            window_start=stats.window_start or today,
            window_end=stats.window_end or today,
        )
        db.add(existing)

    existing.median_value = stats.median_value
    existing.mad_value = stats.mad_value
    existing.sample_count = stats.sample_count
    if stats.window_start is not None:
        existing.window_start = stats.window_start
    if stats.window_end is not None:
        existing.window_end = stats.window_end
    existing.confidence_pct = confidence_pct
    existing.confidence_label = confidence_label
    return existing


def analyze_and_update_baselines(
    db: Session,
    user_id: uuid.UUID,
    recording_id: uuid.UUID,
    new_values: dict[str, float | None],
) -> list[AnomalyResult]:
    """Called right after a sustained-phonation recording's AcousticMeasurement is stored.

    Order matters: anomaly detection compares the new recording against the baseline computed
    from *prior* sessions only (excluding this one), so the new data point never biases the
    baseline it's being judged against. Only after that comparison does the stored baseline
    get updated to include this recording, for the next comparison.
    """
    prior_baselines = compute_all_voice_baselines(db, user_id, exclude_recording_id=recording_id)

    anomalies = []
    for metric, value in new_values.items():
        if value is None or metric not in prior_baselines:
            continue
        result = detect_anomaly(metric, value, prior_baselines[metric])
        if result is not None and result.is_anomaly:
            anomalies.append(result)

    updated_session_count = usable_voice_session_count(db, user_id)
    confidence_pct, confidence_label = confidence_from_session_count(updated_session_count)
    updated_baselines = compute_all_voice_baselines(db, user_id)
    for stats in updated_baselines.values():
        upsert_baseline_row(db, user_id, stats, confidence_pct, confidence_label)

    return anomalies
