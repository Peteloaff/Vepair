import array
import io
import math
import wave

import pytest

from app.audio_quality import (
    InvalidWavError,
    QualityReport,
    analyze_wav,
    compute_recording_quality_score,
)

SAMPLE_RATE = 16000


def make_wav(samples: list[float], sample_rate: int = SAMPLE_RATE, channels: int = 1) -> bytes:
    """Builds a 16-bit PCM WAV from normalized (-1..1) float samples."""
    clamped = [max(-1.0, min(1.0, s)) for s in samples]
    ints = array.array("h", [int(s * 32767) for s in clamped])
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(ints.tobytes())
    return buf.getvalue()


def sine_tone(freq_hz: float, duration_s: float, amplitude: float = 0.5) -> list[float]:
    n = int(SAMPLE_RATE * duration_s)
    return [amplitude * math.sin(2 * math.pi * freq_hz * i / SAMPLE_RATE) for i in range(n)]


def silence(duration_s: float) -> list[float]:
    return [0.0] * int(SAMPLE_RATE * duration_s)


def test_clean_tone_is_usable_and_not_flagged() -> None:
    wav = make_wav(sine_tone(220, 2.0, amplitude=0.5))
    report = analyze_wav(wav)

    assert report.is_usable
    assert not report.clipping
    assert not report.too_quiet
    assert not report.too_short
    assert 1.9 < report.duration_seconds < 2.1
    assert report.sample_rate == SAMPLE_RATE


def test_clipped_signal_is_flagged() -> None:
    # A sine pushed well past full scale gets hard-clamped at +/-1.0 for a large fraction
    # of samples, which is what real clipping looks like.
    wav = make_wav(sine_tone(220, 2.0, amplitude=3.0))
    report = analyze_wav(wav)

    assert report.clipping
    assert not report.is_usable


def test_silence_is_flagged_too_quiet() -> None:
    wav = make_wav(silence(2.0))
    report = analyze_wav(wav)

    assert report.too_quiet
    assert not report.is_usable
    assert report.rms == pytest.approx(0.0, abs=1e-6)


def test_short_recording_is_flagged_too_short() -> None:
    wav = make_wav(sine_tone(220, 0.1, amplitude=0.5))
    report = analyze_wav(wav)

    assert report.too_short
    assert not report.is_usable


def test_quiet_tone_under_noise_floor_is_flagged_too_quiet() -> None:
    wav = make_wav(sine_tone(220, 2.0, amplitude=0.005))
    report = analyze_wav(wav)

    assert report.too_quiet


def test_clean_tone_with_quiet_pauses_is_not_flagged_noisy() -> None:
    samples = sine_tone(220, 1.0, amplitude=0.5) + silence(0.5) + sine_tone(220, 1.0, amplitude=0.5)
    wav = make_wav(samples)
    report = analyze_wav(wav)

    assert not report.possible_background_noise


def test_continuous_sustained_tone_is_not_flagged_noisy() -> None:
    """Regression test: a sustained vowel/hum/glide is continuous phonation with no natural
    pauses at all. Comparing "quiet windows" to "loud windows" within a uniform-level
    recording used to always find a ~1.0 floor/peak ratio and flag it as noisy — a false
    positive on exactly the most common recording type in this app. See CHANGELOG.md."""
    wav = make_wav(sine_tone(220, 2.0, amplitude=0.5))
    report = analyze_wav(wav)

    assert not report.possible_background_noise


def test_sentence_with_noisy_pauses_is_flagged_possibly_noisy() -> None:
    # A spoken sentence has real pauses (breaths, word gaps). Simulate a noisy room: those
    # pauses carry a low hiss instead of true silence, unlike the clean fixture above where
    # the pauses are actual silence — a much smaller peak-to-floor gap than clean audio.
    noisy_pause = sine_tone(60, 0.3, amplitude=0.3)
    voice = sine_tone(220, 0.6, amplitude=0.5)
    samples = voice + noisy_pause + voice + noisy_pause + voice
    wav = make_wav(samples)
    report = analyze_wav(wav)

    assert report.possible_background_noise


def test_invalid_wav_bytes_raise_invalid_wav_error() -> None:
    with pytest.raises(InvalidWavError):
        analyze_wav(b"not a real wav file")


def test_as_dict_is_json_serializable_shape() -> None:
    wav = make_wav(sine_tone(220, 1.0))
    report = analyze_wav(wav).as_dict()

    assert set(report.keys()) == {
        "duration_seconds",
        "sample_rate",
        "channels",
        "peak_amplitude",
        "rms",
        "clipping",
        "too_quiet",
        "too_short",
        "possible_background_noise",
    }


def _report(**overrides) -> QualityReport:
    defaults = dict(
        duration_seconds=2.0,
        sample_rate=44100,
        channels=1,
        peak_amplitude=0.5,
        rms=0.35,
        clipping=False,
        too_quiet=False,
        too_short=False,
        possible_background_noise=False,
    )
    defaults.update(overrides)
    return QualityReport(**defaults)


def test_clean_recording_scores_100() -> None:
    result = compute_recording_quality_score(_report())
    assert result.score == 100
    assert result.label == "excellent"
    assert all(v == "no issues" for v in result.components.values())


def test_clipping_costs_50_points() -> None:
    result = compute_recording_quality_score(_report(clipping=True))
    assert result.score == 50
    assert "clipping" in result.components["clipping"]


def test_too_quiet_costs_50_points() -> None:
    result = compute_recording_quality_score(_report(too_quiet=True, rms=0.001))
    assert result.score == 50


def test_marginal_loudness_costs_15_points_not_50() -> None:
    # Above the too_quiet threshold but still within the "quieter than ideal" margin.
    result = compute_recording_quality_score(_report(too_quiet=False, rms=0.02))
    assert result.score == 85


def test_too_short_costs_50_points() -> None:
    result = compute_recording_quality_score(_report(too_short=True, duration_seconds=0.1))
    assert result.score == 50


def test_background_noise_costs_20_points() -> None:
    result = compute_recording_quality_score(_report(possible_background_noise=True))
    assert result.score == 80


def test_multiple_issues_stack_and_floor_at_zero() -> None:
    result = compute_recording_quality_score(
        _report(clipping=True, too_quiet=True, too_short=True, possible_background_noise=True)
    )
    assert result.score == 0
    assert result.label == "poor"


def test_score_never_factors_in_voice_measurements() -> None:
    """Guards the recording-quality-vs-voice-quality boundary from MEDICAL_SAFETY.md /
    ARCHITECTURE.md — this score must only ever depend on QualityReport fields."""
    import inspect

    from app.audio_quality import compute_recording_quality_score as fn

    source = inspect.getsource(fn)
    for forbidden in ("jitter", "shimmer", "hnr", "f0", "pitch"):
        assert forbidden not in source.lower()
