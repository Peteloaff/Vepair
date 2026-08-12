"""WAV recording-quality gating for Stage 2.

Deliberately stdlib-only (`wave` + `array`) — the real acoustic-analysis stack (numpy, scipy,
librosa, Parselmouth) is introduced in Stage 3 for actual voice measurements. Everything here
is *recording* quality (is the audio usable at all), never *voice* quality — see
MEDICAL_SAFETY.md's distinction between recording quality and voice quality, and
ARCHITECTURE.md's Recording Quality Score note.

The background-noise check in particular is a coarse heuristic (a floor-vs-peak energy ratio),
not a validated SNR measurement. It's good enough to catch "recorded next to a TV," not
precise enough to report as a number to a user. Treat it as a gate, not a metric.
"""

import array
import io
import wave
from dataclasses import dataclass

MIN_DURATION_SECONDS = 0.4
CLIPPING_SAMPLE_THRESHOLD = 0.99
CLIPPING_FRACTION_THRESHOLD = 0.001
TOO_QUIET_RMS_THRESHOLD = 0.01
NOISE_FLOOR_RATIO_THRESHOLD = 0.5
MIN_LEVEL_VARIATION_FOR_NOISE_CHECK = 0.15
WINDOW_MS = 50


@dataclass
class QualityReport:
    duration_seconds: float
    sample_rate: int
    channels: int
    peak_amplitude: float
    rms: float
    clipping: bool
    too_quiet: bool
    too_short: bool
    possible_background_noise: bool

    def as_dict(self) -> dict:
        return {
            "duration_seconds": round(self.duration_seconds, 3),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "peak_amplitude": round(self.peak_amplitude, 4),
            "rms": round(self.rms, 4),
            "clipping": self.clipping,
            "too_quiet": self.too_quiet,
            "too_short": self.too_short,
            "possible_background_noise": self.possible_background_noise,
        }

    @property
    def is_usable(self) -> bool:
        return not (self.clipping or self.too_quiet or self.too_short)


class InvalidWavError(ValueError):
    pass


def _read_normalized_samples(wav_bytes: bytes) -> tuple[list[float], int, int]:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
            sample_width = wav_file.getsampwidth()
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            raw = wav_file.readframes(n_frames)
    except (wave.Error, EOFError) as exc:
        raise InvalidWavError(f"Could not parse WAV file: {exc}") from exc

    if sample_width == 2:
        samples = array.array("h", raw)
        max_value = 32768.0
    elif sample_width == 1:
        # 8-bit WAV PCM is unsigned, centered at 128.
        samples = array.array("B", raw)
        samples = array.array("h", [s - 128 for s in samples])
        max_value = 128.0
    elif sample_width == 4:
        samples = array.array("i", raw)
        max_value = 2147483648.0
    else:
        raise InvalidWavError(f"Unsupported sample width: {sample_width} bytes")

    normalized = [s / max_value for s in samples]
    return normalized, sample_rate, channels


def analyze_wav(wav_bytes: bytes) -> QualityReport:
    samples, sample_rate, channels = _read_normalized_samples(wav_bytes)

    if not samples:
        return QualityReport(
            duration_seconds=0.0,
            sample_rate=sample_rate,
            channels=channels,
            peak_amplitude=0.0,
            rms=0.0,
            clipping=False,
            too_quiet=True,
            too_short=True,
            possible_background_noise=False,
        )

    frames_per_channel = len(samples) // channels
    duration_seconds = frames_per_channel / sample_rate if sample_rate else 0.0

    # Use one channel's worth of samples for level analysis (mono assumption is fine for
    # voice recordings; a stereo file just gets analyzed on its interleaved samples, which
    # slightly overcounts window count but doesn't change peak/RMS/clipping conclusions).
    abs_samples = [abs(s) for s in samples]
    peak_amplitude = max(abs_samples)
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5

    clipped_count = sum(1 for s in abs_samples if s >= CLIPPING_SAMPLE_THRESHOLD)
    clipping = (clipped_count / len(samples)) > CLIPPING_FRACTION_THRESHOLD

    too_quiet = rms < TOO_QUIET_RMS_THRESHOLD
    too_short = duration_seconds < MIN_DURATION_SECONDS

    possible_background_noise = _has_poor_dynamic_range(samples, sample_rate, channels)

    return QualityReport(
        duration_seconds=duration_seconds,
        sample_rate=sample_rate,
        channels=channels,
        peak_amplitude=peak_amplitude,
        rms=rms,
        clipping=clipping,
        too_quiet=too_quiet,
        too_short=too_short,
        possible_background_noise=possible_background_noise,
    )


def _has_poor_dynamic_range(samples: list[float], sample_rate: int, channels: int) -> bool:
    """Coarse noise-floor heuristic: split into short windows, compare the quietest 10th
    percentile of window RMS to the loudest 10th percentile. A recording with natural pauses
    (a spoken sentence, breath gaps) has quiet stretches well below its voiced segments; a
    noisy room compresses that gap.

    This only means anything for recordings that *have* quiet stretches to measure. A
    sustained vowel/hum/glide is continuous phonation by design — no pauses at all — so its
    window levels are naturally uniform even when clean. Flagging that as "no dynamic range
    therefore noisy" would false-positive on exactly the most common recording type in this
    app. Guard against that by first checking whether the recording has *any* meaningful
    loud/quiet contrast (coefficient of variation across windows) before treating a low
    floor/peak ratio as evidence of noise rather than of continuous phonation.
    """
    window_size = max(int(sample_rate * (WINDOW_MS / 1000) * channels), 1)
    if len(samples) < window_size * 4:
        return False  # too short to make a reliable call either way

    window_rms = []
    for i in range(0, len(samples) - window_size, window_size):
        window = samples[i : i + window_size]
        window_rms.append((sum(s * s for s in window) / len(window)) ** 0.5)

    if len(window_rms) < 4:
        return False

    mean_rms = sum(window_rms) / len(window_rms)
    if mean_rms < TOO_QUIET_RMS_THRESHOLD:
        return False  # already flagged too_quiet; don't double-report as noisy

    variance = sum((w - mean_rms) ** 2 for w in window_rms) / len(window_rms)
    coefficient_of_variation = (variance**0.5) / mean_rms
    if coefficient_of_variation < MIN_LEVEL_VARIATION_FOR_NOISE_CHECK:
        # Uniform level throughout — a continuous phonation task, not evidence either way
        # about background noise. Nothing reliable to compare against.
        return False

    window_rms.sort()
    floor = window_rms[max(len(window_rms) // 10, 0)]
    peak = window_rms[min(len(window_rms) - 1, (len(window_rms) * 9) // 10)]

    return (floor / peak) > NOISE_FLOOR_RATIO_THRESHOLD


# --- Recording Quality Score (Stage 3) ---
#
# A single 0-100 number summarizing whether *this recording is technically usable*, with an
# explainable breakdown — same "why did I get this score" transparency principle the future
# VepAIr Score (Stage 5) will use for voice health, applied here to the recording itself.
#
# This score is built ONLY from recording-technical signals already computed above: clipping,
# gain staging (RMS relative to the noise floor), duration, and the background-noise heuristic.
# It deliberately never factors in anything from packages/audio-engine's voice measurements
# (jitter, shimmer, HNR, F0) — those describe the *voice*, and folding them in here would blur
# exactly the line MEDICAL_SAFETY.md and ARCHITECTURE.md §6b warn against: a low score must
# always mean "re-record this, something about the capture was off," never "something may be
# wrong with your voice." That second kind of signal is a future, clearly-separated feature.

QUIET_MARGIN_MULTIPLIER = 3.0  # within 3x the "too quiet" floor still costs points
SHORT_MARGIN_MULTIPLIER = 2.0  # within 2x the minimum duration still costs points

CLIPPING_PENALTY = 50
TOO_QUIET_PENALTY = 50
MARGINAL_QUIET_PENALTY = 15
TOO_SHORT_PENALTY = 50
MARGINAL_SHORT_PENALTY = 10
BACKGROUND_NOISE_PENALTY = 20


@dataclass
class RecordingQualityScore:
    score: int
    label: str
    components: dict[str, str]

    def as_dict(self) -> dict:
        return {"score": self.score, "label": self.label, "components": self.components}


def _label_for(score: int) -> str:
    if score >= 85:
        return "excellent"
    if score >= 65:
        return "good"
    if score >= 40:
        return "fair"
    return "poor"


def compute_recording_quality_score(report: QualityReport) -> RecordingQualityScore:
    score = 100
    components: dict[str, str] = {}

    if report.clipping:
        score -= CLIPPING_PENALTY
        components["clipping"] = f"-{CLIPPING_PENALTY}: clipping detected"
    else:
        components["clipping"] = "no issues"

    if report.too_quiet:
        score -= TOO_QUIET_PENALTY
        components["loudness"] = f"-{TOO_QUIET_PENALTY}: below the usable loudness floor"
    elif report.rms < TOO_QUIET_RMS_THRESHOLD * QUIET_MARGIN_MULTIPLIER:
        score -= MARGINAL_QUIET_PENALTY
        components["loudness"] = f"-{MARGINAL_QUIET_PENALTY}: quieter than ideal"
    else:
        components["loudness"] = "no issues"

    if report.too_short:
        score -= TOO_SHORT_PENALTY
        components["duration"] = f"-{TOO_SHORT_PENALTY}: below the minimum usable duration"
    elif report.duration_seconds < MIN_DURATION_SECONDS * SHORT_MARGIN_MULTIPLIER:
        score -= MARGINAL_SHORT_PENALTY
        components["duration"] = f"-{MARGINAL_SHORT_PENALTY}: shorter than ideal"
    else:
        components["duration"] = "no issues"

    if report.possible_background_noise:
        score -= BACKGROUND_NOISE_PENALTY
        components["background_noise"] = f"-{BACKGROUND_NOISE_PENALTY}: possible background noise"
    else:
        components["background_noise"] = "no issues"

    score = max(0, min(100, score))
    return RecordingQualityScore(score=score, label=_label_for(score), components=components)
