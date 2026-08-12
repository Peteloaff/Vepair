"""Regression tests against the permanent Golden Voice Set (data/fixtures/golden-voice-set/,
see docs/golden-voice-set.md). These lock in *current, verified* measurement behavior so a
future change to the DSP pipeline (library upgrade, algorithm tweak) that shifts results
beyond the documented tolerance fails the build instead of shipping silently — per the
Stage 0 commitment in TESTING.md.

Tolerances here are deliberately looser than the tight synthetic-tone tests in
test_measurements.py — these fixtures are more complex signals (harmonics, injected
instability, noise), and the goal is "did something change unexpectedly," not
"reproduce a single sine to the machine epsilon."
"""

from pathlib import Path

import pytest

from vepair_audio_engine.measurements import analyze_wav_bytes

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "data" / "fixtures" / "golden-voice-set"


def _load(name: str) -> bytes:
    path = FIXTURES_DIR / f"{name}.wav"
    if not path.exists():
        pytest.skip(
            f"{path} not found — run "
            "packages/audio-engine/scripts/generate_golden_voice_set.py first"
        )
    return path.read_bytes()


def test_stable_vowel_is_clean_and_on_pitch() -> None:
    result = analyze_wav_bytes(_load("stable_vowel"), "sustained_ah")
    assert result.f0_mean_hz == pytest.approx(220.0, abs=1.0)
    assert result.jitter_percent < 0.01
    assert result.shimmer_percent < 0.01
    assert result.hnr_db > 60
    assert result.voiced_ratio == pytest.approx(1.0, abs=0.05)


def test_unstable_vowel_reads_clearly_worse_than_stable() -> None:
    stable = analyze_wav_bytes(_load("stable_vowel"), "sustained_ah")
    unstable = analyze_wav_bytes(_load("unstable_vowel"), "sustained_ah")

    assert unstable.jitter_percent > stable.jitter_percent * 10
    assert unstable.shimmer_percent > stable.shimmer_percent * 10
    assert unstable.hnr_db < stable.hnr_db
    assert unstable.pitch_stability_semitones > stable.pitch_stability_semitones


def test_quiet_and_loud_vowel_have_same_pitch_as_stable() -> None:
    """Amplitude shouldn't change what pitch is detected."""
    stable = analyze_wav_bytes(_load("stable_vowel"), "sustained_ah")
    quiet = analyze_wav_bytes(_load("quiet_vowel"), "sustained_ah")
    loud = analyze_wav_bytes(_load("loud_vowel"), "sustained_ah")

    assert quiet.f0_mean_hz == pytest.approx(stable.f0_mean_hz, abs=0.5)
    assert loud.f0_mean_hz == pytest.approx(stable.f0_mean_hz, abs=0.5)
    assert quiet.rms_loudness < stable.rms_loudness < loud.rms_loudness


def test_low_and_high_note_read_correct_pitch() -> None:
    low = analyze_wav_bytes(_load("low_note"), "sustained_ah")
    high = analyze_wav_bytes(_load("high_note"), "sustained_ah")

    assert low.f0_mean_hz == pytest.approx(82.0, abs=1.0)
    assert high.f0_mean_hz == pytest.approx(440.0, abs=1.0)


def test_pitch_glide_spans_the_swept_range() -> None:
    result = analyze_wav_bytes(_load("pitch_glide"), "glide")
    # 150Hz -> 500Hz sweep: the "reliable" (5th/95th percentile) range should be wide,
    # confirming the glide's pitch movement is actually being tracked, not flattened out.
    assert result.f0_min_hz < 200
    assert result.f0_max_hz > 400
    # Jitter/shimmer/HNR must be withheld for a glide regardless of what's in the file.
    assert result.jitter_percent is None
    assert result.shimmer_percent is None
    assert result.hnr_db is None


def test_vibrato_reads_clearly_nonzero_pitch_stability() -> None:
    """+/-50 cents vibrato should move pitch_stability well off the clean-tone baseline.

    Counterintuitively, vibrato's pitch_stability_semitones (0.349, matching the theoretical
    std dev of a 0.5-semitone-amplitude sine wave: amplitude/sqrt(2) ~= 0.35) reads *higher*
    than unstable_vowel's smaller, purely random per-cycle jitter (0.124) — a full, coherent
    vibrato sweep has more total pitch variance than mild random unsteadiness. This is
    correct, documented behavior (see docs/acoustic-measurements.md's Pitch stability
    Limitations): the metric doesn't distinguish intentional musical vibrato from noise-like
    instability, both show up as elevated standard deviation. Not asserting an ordering
    against unstable_vowel here — that ordering isn't guaranteed and depends on each
    fixture's specific parameters, not on which "sounds" more unstable.
    """
    stable = analyze_wav_bytes(_load("stable_vowel"), "sustained_ah")
    result = analyze_wav_bytes(_load("vibrato"), "sustained_ah")
    assert result.pitch_stability_semitones > 0.05
    assert result.pitch_stability_semitones > stable.pitch_stability_semitones


def test_breathy_and_noisy_room_have_lower_hnr_than_stable() -> None:
    stable = analyze_wav_bytes(_load("stable_vowel"), "sustained_ah")
    breathy = analyze_wav_bytes(_load("breathy"), "sustained_ah")
    noisy_room = analyze_wav_bytes(_load("noisy_room"), "sustained_ah")

    assert breathy.hnr_db < stable.hnr_db
    assert noisy_room.hnr_db < stable.hnr_db


def test_clipping_is_still_pitch_trackable_but_flagged_by_stage2_not_hnr() -> None:
    """Documents the known limitation from docs/acoustic-measurements.md: HNR alone does not
    reliably catch clipping. The recording-quality clipping check (Stage 2,
    apps/api/app/audio_quality.py) is what actually catches this — verified separately in
    apps/api's own test suite."""
    result = analyze_wav_bytes(_load("clipping"), "sustained_ah")
    assert result.f0_mean_hz == pytest.approx(220.0, abs=2.0)
    assert result.hnr_db > 40  # stays high despite being badly clipped — the documented gap


def test_silence_fixture_returns_no_voice_measurements() -> None:
    result = analyze_wav_bytes(_load("silence"), "sustained_ah")
    assert result.voiced_ratio == 0.0
    assert result.f0_mean_hz is None
    assert result.jitter_percent is None


def test_instrument_contamination_demonstrates_missing_fundamental() -> None:
    """Documents the known pitch-tracking failure mode from docs/golden-voice-set.md: 220Hz +
    330Hz (both multiples of 110Hz) gets tracked as F0=110Hz, the missing fundamental — not
    either real tone. This test exists to make sure that documented behavior stays visible
    and intentional, not to endorse it as correct."""
    result = analyze_wav_bytes(_load("instrument_contamination"), "sustained_ah")
    assert result.f0_mean_hz == pytest.approx(110.0, abs=2.0)
