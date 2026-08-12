"""Core acoustic measurement functions.

See `docs/acoustic-measurements.md` (repo root) for the full per-metric documentation —
definition, algorithm, library, units, valid input type, limitations, expected measurement
variability — required by the Stage 3 spec. This module intentionally keeps only short
implementation-level comments; that file is the authoritative reference.

F0/jitter/shimmer/HNR come from Parselmouth (Python bindings to Praat), the field-standard
tool for exactly these measurements in voice science — not a homebrew implementation.
Spectral features (centroid, rolloff, zero-crossing rate) come from librosa, the standard
Python audio-analysis library for those. Nothing here is fabricated: every field is either a
direct library output or a documented, simple derivation (e.g. percentile of per-frame F0),
and every field that can't be reliably computed for a given input is `None`, never a guess.
"""

import io
import math
from dataclasses import asdict, dataclass

import librosa
import numpy as np
import parselmouth
import soundfile as sf
from parselmouth.praat import call

# Praat pitch-tracking floor/ceiling in Hz. 75-1000 Hz covers low bass through most
# falsetto/head-voice and legit soprano singing, while staying tight enough to reject
# implausible octave-error detections. Genuine whistle register (roughly C6/~1050Hz and above)
# sits above this ceiling and won't be tracked — a real, documented remaining limitation, not a
# silent gap (see docs/acoustic-measurements.md). Originally set to 600Hz, which a Stage 8
# vocal-range falsetto test caught as too low: a 660Hz test tone was tracked as its own
# octave-down subharmonic (330Hz) because it fell outside the search range entirely.
F0_FLOOR_HZ = 75.0
F0_CEILING_HZ = 1000.0

# Below this, there usually aren't enough glottal cycles for any measurement to be
# meaningful — Praat's own jitter/shimmer algorithms need several consecutive periods.
MIN_ANALYZABLE_DURATION_SECONDS = 0.3

# Jitter/shimmer/HNR need enough voiced material to find reliable cycle-to-cycle periods.
# Below this frame count, Praat's point-process detection becomes unstable — a "measurement"
# from too little data would misrepresent the recording, so it's withheld (None) instead.
MIN_VOICED_FRAMES_FOR_PERIODICITY_MEASURES = 10

# Jitter, shimmer, and HNR are classically defined on *sustained, steady* phonation — Praat's
# algorithms assume a stable periodic signal to measure cycle-to-cycle variation against. A
# pitch glide (moving target) or spoken sentence/song (mixed voiced/unvoiced, consonants,
# pauses) breaks that assumption; computing these on non-sustained input would produce a
# number that looks precise but isn't scientifically meaningful. See
# docs/acoustic-measurements.md for the full reasoning.
SUSTAINED_PHONATION_SAMPLE_TYPES = frozenset(
    {"sustained_ah", "sustained_ee", "sustained_oo", "hum"}
)


class InvalidAudioError(ValueError):
    """The audio couldn't be decoded at all (corrupt/non-WAV bytes)."""


class InsufficientAudioError(ValueError):
    """The audio decoded fine but is too short/silent to measure anything meaningful from."""


@dataclass
class AcousticMeasurements:
    duration_seconds: float
    voiced_ratio: float | None
    f0_mean_hz: float | None
    f0_median_hz: float | None
    f0_min_hz: float | None
    f0_max_hz: float | None
    pitch_stability_semitones: float | None
    jitter_percent: float | None
    shimmer_percent: float | None
    hnr_db: float | None
    rms_loudness: float | None
    spectral_centroid_hz: float | None
    spectral_rolloff_hz: float | None
    zero_crossing_rate: float | None
    # Longest unbroken run of voiced frames, in seconds — "how long could this take sustain
    # phonation without a break," a byproduct of the same frame-level voicing decisions used
    # for voiced_ratio (Stage 10 "Vocal Endurance"), not a new signal-processing algorithm.
    longest_voiced_run_seconds: float | None

    def as_dict(self) -> dict:
        return asdict(self)


def _clean(value: float | None) -> float | None:
    """NaN/inf are not valid measurements — treat them as "couldn't measure", not zero."""
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return None
    return float(value)


def analyze_wav_bytes(wav_bytes: bytes, sample_type: str) -> AcousticMeasurements:
    """Decodes a WAV file and runs the full measurement suite. Raises InvalidAudioError if
    the bytes aren't valid audio, InsufficientAudioError if they decode but are too short."""
    try:
        samples, sample_rate = sf.read(io.BytesIO(wav_bytes), dtype="float64", always_2d=False)
    except Exception as exc:  # noqa: BLE001 — soundfile raises backend-specific errors
        raise InvalidAudioError(f"Could not decode audio: {exc}") from exc

    if samples.ndim > 1:
        samples = samples.mean(axis=1)  # downmix to mono for analysis

    return analyze(samples, sample_rate, sample_type)


def analyze(samples: np.ndarray, sample_rate: int, sample_type: str) -> AcousticMeasurements:
    """Runs the full measurement suite on already-decoded mono float samples."""
    duration_seconds = len(samples) / sample_rate if sample_rate else 0.0
    if duration_seconds < MIN_ANALYZABLE_DURATION_SECONDS:
        raise InsufficientAudioError(
            f"Recording is only {duration_seconds:.2f}s; need at least "
            f"{MIN_ANALYZABLE_DURATION_SECONDS}s to analyze."
        )

    snd = parselmouth.Sound(samples.astype(np.float64), sampling_frequency=sample_rate)

    (
        f0_mean,
        f0_median,
        f0_min,
        f0_max,
        pitch_stability,
        voiced_ratio,
        voiced_frames,
        longest_voiced_run,
    ) = _analyze_pitch(snd)

    jitter_percent = shimmer_percent = hnr_db = None
    if (
        sample_type in SUSTAINED_PHONATION_SAMPLE_TYPES
        and len(voiced_frames) >= MIN_VOICED_FRAMES_FOR_PERIODICITY_MEASURES
    ):
        jitter_percent, shimmer_percent, hnr_db = _analyze_periodicity(snd)

    rms_loudness = _clean(float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))))

    y = samples.astype(np.float32)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sample_rate)
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sample_rate)
    zcr = librosa.feature.zero_crossing_rate(y)
    spectral_centroid = _clean(float(np.mean(centroid)))
    spectral_rolloff = _clean(float(np.mean(rolloff)))
    zero_crossing_rate = _clean(float(np.mean(zcr)))

    return AcousticMeasurements(
        duration_seconds=round(duration_seconds, 3),
        voiced_ratio=_clean(voiced_ratio),
        f0_mean_hz=_clean(f0_mean),
        f0_median_hz=_clean(f0_median),
        f0_min_hz=_clean(f0_min),
        f0_max_hz=_clean(f0_max),
        pitch_stability_semitones=_clean(pitch_stability),
        jitter_percent=_clean(jitter_percent),
        shimmer_percent=_clean(shimmer_percent),
        hnr_db=_clean(hnr_db),
        rms_loudness=rms_loudness,
        spectral_centroid_hz=spectral_centroid,
        spectral_rolloff_hz=spectral_rolloff,
        zero_crossing_rate=zero_crossing_rate,
        longest_voiced_run_seconds=_clean(longest_voiced_run),
    )


_OptFloat = float | None
_PitchResult = tuple[
    _OptFloat, _OptFloat, _OptFloat, _OptFloat, _OptFloat, _OptFloat, np.ndarray, _OptFloat
]


def _longest_voiced_run_seconds(voiced_mask: np.ndarray, time_step: float) -> float | None:
    """Longest unbroken run of voiced frames, in seconds — scans the same frame-level voicing
    decisions `voiced_ratio` already uses, just tracking run length instead of a total count."""
    longest = current = 0
    for is_voiced in voiced_mask:
        current = current + 1 if is_voiced else 0
        longest = max(longest, current)
    return float(longest * time_step) if longest > 0 else None


def _analyze_pitch(snd: parselmouth.Sound) -> _PitchResult:
    pitch = snd.to_pitch(pitch_floor=F0_FLOOR_HZ, pitch_ceiling=F0_CEILING_HZ)
    f0_frames = pitch.selected_array["frequency"]
    voiced_frames = f0_frames[f0_frames > 0]
    total_frames = len(f0_frames)

    voiced_ratio = len(voiced_frames) / total_frames if total_frames > 0 else None
    longest_voiced_run = _longest_voiced_run_seconds(f0_frames > 0, pitch.get_time_step())

    if len(voiced_frames) == 0:
        return None, None, None, None, None, voiced_ratio, voiced_frames, longest_voiced_run

    f0_mean = float(np.mean(voiced_frames))
    f0_median = float(np.median(voiced_frames))
    # "Reliable" min/max are the 5th/95th percentile of voiced-frame F0, not the absolute
    # min/max — a robust range that isn't thrown off by a single octave-error frame (a known
    # failure mode of pitch trackers). See docs/acoustic-measurements.md.
    f0_min = float(np.percentile(voiced_frames, 5))
    f0_max = float(np.percentile(voiced_frames, 95))

    pitch_stability = None
    if len(voiced_frames) >= 2 and f0_median > 0:
        # Standard deviation of each frame's pitch, expressed in semitones from the
        # recording's own median — a musically meaningful, F0-scale-independent unit (a 5Hz
        # wobble means very different things at 100Hz vs 400Hz; semitones normalize that).
        semitone_deviations = 12 * np.log2(voiced_frames / f0_median)
        pitch_stability = float(np.std(semitone_deviations))

    return (
        f0_mean,
        f0_median,
        f0_min,
        f0_max,
        pitch_stability,
        voiced_ratio,
        voiced_frames,
        longest_voiced_run,
    )


def _analyze_periodicity(
    snd: parselmouth.Sound,
) -> tuple[float | None, float | None, float | None]:
    """Jitter, shimmer, HNR — only called for sustained phonation with enough voiced frames.
    Praat's own algorithms can still fail to find enough periodic points on marginal audio;
    that's caught here and reported as unmeasurable (None) rather than a fabricated number."""
    try:
        point_process = call(snd, "To PointProcess (periodic, cc)", F0_FLOOR_HZ, F0_CEILING_HZ)
        jitter_local = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer_local = call(
            [snd, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6
        )
        hnr_mean = call(snd.to_harmonicity(), "Get mean", 0, 0)
    except Exception:  # noqa: BLE001 — Praat raises its own error types on bad input
        return None, None, None

    jitter_percent = jitter_local * 100 if jitter_local is not None else None
    shimmer_percent = shimmer_local * 100 if shimmer_local is not None else None
    return jitter_percent, shimmer_percent, hnr_mean
