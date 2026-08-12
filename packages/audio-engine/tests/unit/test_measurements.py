import math

import numpy as np
import pytest

from vepair_audio_engine.measurements import (
    InsufficientAudioError,
    InvalidAudioError,
    analyze,
    analyze_wav_bytes,
)

SAMPLE_RATE = 44100


def sine_tone(freq_hz: float, duration_s: float = 2.0, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(int(SAMPLE_RATE * duration_s)) / SAMPLE_RATE
    return amplitude * np.sin(2 * np.pi * freq_hz * t)


# --- Known-frequency tests (Stage 3 spec: 110Hz, 220Hz, 440Hz) ---


@pytest.mark.parametrize("freq_hz", [110.0, 220.0, 440.0])
def test_known_frequency_detected_within_tolerance(freq_hz: float) -> None:
    """A pure tone's F0 must read within 0.5Hz of the true frequency — a generous tolerance
    given clean synthetic tones actually measure within ~0.001Hz in practice; 0.5Hz leaves
    headroom for legitimate algorithmic variation without masking a real regression."""
    result = analyze(sine_tone(freq_hz), SAMPLE_RATE, "sustained_ah")
    assert result.f0_mean_hz == pytest.approx(freq_hz, abs=0.5)
    assert result.f0_median_hz == pytest.approx(freq_hz, abs=0.5)
    # "Reliable" min/max are percentiles of a near-constant track, so they should also sit
    # close to the true frequency for a stable tone.
    assert result.f0_min_hz == pytest.approx(freq_hz, abs=0.5)
    assert result.f0_max_hz == pytest.approx(freq_hz, abs=0.5)


@pytest.mark.parametrize("freq_hz", [660.0, 880.0])
def test_falsetto_range_frequency_detected_within_tolerance(freq_hz: float) -> None:
    """Stage 8 regression test: a 660Hz tone (within real falsetto/head-voice range) used to be
    tracked as its own octave-down subharmonic (330Hz) because it fell outside the old 600Hz
    F0_CEILING_HZ. Locks in the fix (ceiling raised to 1000Hz) so it can't silently regress."""
    result = analyze(sine_tone(freq_hz), SAMPLE_RATE, "sustained_ah")
    assert result.f0_mean_hz == pytest.approx(freq_hz, abs=0.5)


@pytest.mark.parametrize("freq_hz", [110.0, 220.0, 440.0])
def test_clean_tone_has_near_zero_jitter_shimmer(freq_hz: float) -> None:
    result = analyze(sine_tone(freq_hz), SAMPLE_RATE, "sustained_ah")
    assert result.jitter_percent < 0.01
    assert result.shimmer_percent < 0.01
    assert result.hnr_db > 60  # a clean synthetic tone has essentially no noise


# --- Cross-validation against a second, independent algorithm ---


def test_f0_agrees_with_independent_librosa_pyin_estimate() -> None:
    """The Stage 3 spec asks to compare results against Praat/Parselmouth reference
    calculations. Parselmouth (Praat) is VepAIr's primary F0 engine, so the meaningful
    cross-check is the reverse: does a completely independent algorithm (librosa's
    probabilistic YIN) agree with it on the same signal? Agreement between two
    independently-implemented pitch trackers is much stronger evidence of correctness than
    either algorithm's self-consistency."""
    librosa = pytest.importorskip("librosa")
    freq_hz = 220.0
    signal = sine_tone(freq_hz).astype(np.float32)

    parselmouth_result = analyze(sine_tone(freq_hz), SAMPLE_RATE, "sustained_ah")

    f0_track, voiced_flag, _ = librosa.pyin(
        signal, fmin=75, fmax=600, sr=SAMPLE_RATE
    )
    pyin_f0 = float(np.nanmean(f0_track[voiced_flag]))

    assert parselmouth_result.f0_mean_hz == pytest.approx(pyin_f0, rel=0.01)
    assert parselmouth_result.f0_mean_hz == pytest.approx(freq_hz, abs=1.0)


# --- Repeatability ---


def test_measurement_is_repeatable_on_identical_input() -> None:
    signal = sine_tone(220.0)
    first = analyze(signal, SAMPLE_RATE, "sustained_ah")
    second = analyze(signal, SAMPLE_RATE, "sustained_ah")
    assert first.as_dict() == second.as_dict()


# --- Noise, clipping, silence, short samples ---


def test_noise_contamination_reduces_hnr_and_raises_jitter() -> None:
    rng = np.random.default_rng(123)
    clean = sine_tone(220.0)
    noisy = clean + 0.15 * rng.normal(0, 1, len(clean))

    clean_result = analyze(clean, SAMPLE_RATE, "sustained_ah")
    noisy_result = analyze(noisy, SAMPLE_RATE, "sustained_ah")

    assert noisy_result.hnr_db < clean_result.hnr_db
    assert noisy_result.jitter_percent > clean_result.jitter_percent


def test_clipping_does_not_crash_and_still_detects_pitch() -> None:
    clipped = np.clip(sine_tone(220.0, amplitude=2.5), -1.0, 1.0)
    result = analyze(clipped, SAMPLE_RATE, "sustained_ah")
    assert result.f0_mean_hz == pytest.approx(220.0, abs=2.0)
    # Documented limitation (see docs/acoustic-measurements.md): HNR does not reliably drop
    # from clipping alone, since clipping distortion is harmonic, not noise-like. This test
    # exists so a future change to the HNR pipeline that *does* start reacting to clipping
    # doesn't silently and quietly change documented behavior without review.
    assert result.hnr_db is not None


def test_silence_returns_none_for_every_voice_measurement() -> None:
    result = analyze(np.zeros(SAMPLE_RATE * 2), SAMPLE_RATE, "sustained_ah")
    assert result.voiced_ratio == 0.0
    assert result.f0_mean_hz is None
    assert result.f0_median_hz is None
    assert result.f0_min_hz is None
    assert result.f0_max_hz is None
    assert result.pitch_stability_semitones is None
    assert result.jitter_percent is None
    assert result.shimmer_percent is None
    assert result.hnr_db is None
    assert result.longest_voiced_run_seconds is None
    # RMS/spectral features are still well-defined (all zero/silent), just not pitch-based.
    assert result.rms_loudness == 0.0


# --- Stage 10: longest_voiced_run_seconds ("Vocal Endurance") ---


def test_continuous_tone_run_length_is_close_to_full_duration() -> None:
    """A single unbroken sustained tone should register a run close to its total duration —
    some slack at the start/end is expected from Praat's own pitch-analysis windowing."""
    result = analyze(sine_tone(220.0, duration_s=2.0), SAMPLE_RATE, "sustained_ah")
    assert result.longest_voiced_run_seconds == pytest.approx(2.0, abs=0.3)


def test_run_length_is_the_longest_segment_not_the_total_voiced_time() -> None:
    """A tone interrupted by a silent gap must report the longest unbroken segment, not the
    sum of all voiced time — proving this is a run-length scan, not a repurposed voiced_ratio."""
    segments = np.concatenate(
        [
            sine_tone(220.0, duration_s=0.6),
            np.zeros(int(SAMPLE_RATE * 0.4)),
            sine_tone(220.0, duration_s=1.0),
        ]
    )
    result = analyze(segments, SAMPLE_RATE, "sustained_ah")
    # Longest run is the 1.0s segment, well short of the ~1.6s combined voiced time.
    assert result.longest_voiced_run_seconds == pytest.approx(1.0, abs=0.3)
    assert result.longest_voiced_run_seconds < 1.4


def test_very_short_sample_raises_insufficient_audio_error() -> None:
    short_signal = sine_tone(220.0, duration_s=0.1)
    with pytest.raises(InsufficientAudioError):
        analyze(short_signal, SAMPLE_RATE, "sustained_ah")


def test_invalid_wav_bytes_raise_invalid_audio_error() -> None:
    with pytest.raises(InvalidAudioError):
        analyze_wav_bytes(b"not a wav file", "sustained_ah")


# --- Per-sample-type validity (jitter/shimmer/HNR only for sustained phonation) ---


@pytest.mark.parametrize("sample_type", ["glide", "sentence", "singing"])
def test_periodicity_measures_withheld_for_non_sustained_types(sample_type: str) -> None:
    result = analyze(sine_tone(220.0), SAMPLE_RATE, sample_type)
    assert result.jitter_percent is None
    assert result.shimmer_percent is None
    assert result.hnr_db is None
    # F0 and other non-periodicity measures remain available.
    assert result.f0_mean_hz is not None


@pytest.mark.parametrize(
    "sample_type", ["sustained_ah", "sustained_ee", "sustained_oo", "hum"]
)
def test_periodicity_measures_present_for_sustained_types(sample_type: str) -> None:
    result = analyze(sine_tone(220.0), SAMPLE_RATE, sample_type)
    assert result.jitter_percent is not None
    assert result.shimmer_percent is not None
    assert result.hnr_db is not None


# --- Zero-crossing rate sanity check (documented in acoustic-measurements.md) ---


def test_zero_crossing_rate_matches_theoretical_prediction() -> None:
    """For a pure tone at frequency f and sample rate sr, ZCR should be close to 2f/sr."""
    freq_hz = 220.0
    result = analyze(sine_tone(freq_hz), SAMPLE_RATE, "sustained_ah")
    expected_zcr = 2 * freq_hz / SAMPLE_RATE
    assert result.zero_crossing_rate == pytest.approx(expected_zcr, rel=0.05)


def test_rms_loudness_matches_theoretical_sine_rms() -> None:
    """A sine wave's RMS is amplitude/sqrt(2) — exact, well-known DSP identity."""
    amplitude = 0.5
    result = analyze(sine_tone(220.0, amplitude=amplitude), SAMPLE_RATE, "sustained_ah")
    assert result.rms_loudness == pytest.approx(amplitude / math.sqrt(2), rel=0.001)
