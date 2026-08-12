"""Synthetic audio generators for the Golden Voice Set (see data/fixtures/golden-voice-set/
and docs/golden-voice-set.md). Every generator returns (samples, sample_rate) — mono float64
in [-1, 1] — so they can be used directly by tests or written to disk as WAV files by
scripts/generate_golden_voice_set.py.

These are synthetic, not real human recordings — no licensing question, and deterministic
(seeded) so the same "recording" is reproducible across runs and machines. Each generator is
built from a small number of understood, documented signal-processing operations (additive
sine synthesis, linear/sinusoidal frequency modulation, filtered noise) — never randomness
dressed up as realism. Where a fixture approximates a real phenomenon (breathiness, room
noise), the docstring says what it approximates and how, so nobody mistakes it for validated
clinical audio.
"""

from collections.abc import Callable

import numpy as np

DEFAULT_SAMPLE_RATE = 44100


def _harmonic_tone(
    freq_hz: float | np.ndarray,
    duration_s: float,
    amplitude: float = 0.5,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    harmonic_amplitudes: tuple[float, ...] = (1.0, 0.4, 0.2, 0.1),
) -> np.ndarray:
    """A vowel-like tone: a fundamental plus a few decaying harmonics, instead of a bare
    sine — more representative of voiced speech (which is harmonically rich) while still
    being fully synthetic and analytically understood. `freq_hz` may be an array (for
    time-varying pitch, e.g. glide/vibrato) matching the sample count for `duration_s`."""
    n = int(sample_rate * duration_s)
    freq = np.full(n, freq_hz) if np.isscalar(freq_hz) else freq_hz
    phase = 2 * np.pi * np.cumsum(freq) / sample_rate

    signal = np.zeros(n)
    total_amp = sum(harmonic_amplitudes)
    for k, harmonic_amp in enumerate(harmonic_amplitudes, start=1):
        signal += (harmonic_amp / total_amp) * np.sin(k * phase)

    return amplitude * signal


def stable_vowel(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A clean, steady 220Hz vowel-like tone. The baseline "everything should work" case."""
    return _harmonic_tone(220.0, 2.0, amplitude=0.5, sample_rate=sample_rate), sample_rate


def unstable_vowel(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A 220Hz tone with real cycle-to-cycle jitter and shimmer injected — simulates an
    unsteady voice. Jitter: each cycle's frequency perturbed by a small random amount.
    Shimmer: each cycle's amplitude perturbed by a small random amount."""
    rng = np.random.default_rng(seed=42)
    sample_rate_ = sample_rate
    duration_s = 2.0
    base_freq = 220.0

    n = int(sample_rate_ * duration_s)
    # Build cycle-by-cycle with per-cycle random freq/amp perturbation (~1.5% jitter,
    # ~6% shimmer — clearly audible instability, well above a clean voice's typical <1%/<3%).
    signal = np.zeros(n)
    idx = 0
    while idx < n:
        freq = base_freq * (1 + rng.normal(0, 0.015))
        amp = 0.5 * (1 + rng.normal(0, 0.06))
        cycle_len = max(int(sample_rate_ / freq), 1)
        cycle_len = min(cycle_len, n - idx)
        t = np.arange(cycle_len) / sample_rate_
        signal[idx : idx + cycle_len] = amp * np.sin(2 * np.pi * freq * t)
        idx += cycle_len

    return signal, sample_rate_


def quiet_vowel(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A stable 220Hz tone at low amplitude — below or near the too-quiet floor."""
    return _harmonic_tone(220.0, 2.0, amplitude=0.05, sample_rate=sample_rate), sample_rate


def loud_vowel(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A stable 220Hz tone at high amplitude, but staying just under clipping."""
    return _harmonic_tone(220.0, 2.0, amplitude=0.9, sample_rate=sample_rate), sample_rate


def pitch_glide(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A gentle siren-like glide from 150Hz to 500Hz over 2 seconds (linear in log-frequency,
    i.e. constant perceived rate of pitch change)."""
    duration_s = 2.0
    n = int(sample_rate * duration_s)
    freq = np.geomspace(150.0, 500.0, n)
    return _harmonic_tone(freq, duration_s, amplitude=0.5, sample_rate=sample_rate), sample_rate


def low_note(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A stable low note (E2, ~82Hz) — near the low end of typical bass range."""
    return _harmonic_tone(82.0, 2.0, amplitude=0.5, sample_rate=sample_rate), sample_rate


def high_note(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A stable high note (A4, 440Hz) — within typical soprano/high-tenor range."""
    return _harmonic_tone(440.0, 2.0, amplitude=0.5, sample_rate=sample_rate), sample_rate


def vibrato(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A 220Hz tone with sinusoidal vibrato: 5.5Hz rate, +/-50 cents extent — typical of a
    trained singer's vibrato (rate 4-7Hz, extent roughly +/-30-100 cents)."""
    duration_s = 2.0
    n = int(sample_rate * duration_s)
    t = np.arange(n) / sample_rate
    vibrato_rate_hz = 5.5
    vibrato_extent_semitones = 0.5  # +/-50 cents
    freq = 220.0 * 2 ** (
        (vibrato_extent_semitones / 12) * np.sin(2 * np.pi * vibrato_rate_hz * t)
    )
    return _harmonic_tone(freq, duration_s, amplitude=0.5, sample_rate=sample_rate), sample_rate


def breathy(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """Approximates breathiness by mixing a clean 220Hz tone with substantial high-passed
    noise (turbulent airflow reduces harmonic-to-noise ratio in real breathy phonation).
    This is a crude approximation, not a validated breathy-voice model — good for testing
    that HNR responds to added noise, not for anything clinical."""
    rng = np.random.default_rng(seed=7)
    duration_s = 2.0
    n = int(sample_rate * duration_s)
    tone = _harmonic_tone(220.0, duration_s, amplitude=0.35, sample_rate=sample_rate)
    noise = rng.normal(0, 1, n)
    # Crude high-pass: difference noise (emphasizes high frequencies, like breath turbulence).
    noise = np.diff(noise, prepend=0)
    noise = 0.15 * noise / (np.max(np.abs(noise)) + 1e-9)
    return tone + noise, sample_rate


def noisy_room(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A clean 220Hz tone with moderate broadband background noise mixed in throughout —
    simulates recording in a room with constant ambient noise (fan, traffic, HVAC)."""
    rng = np.random.default_rng(seed=99)
    duration_s = 2.0
    n = int(sample_rate * duration_s)
    tone = _harmonic_tone(220.0, duration_s, amplitude=0.5, sample_rate=sample_rate)
    noise = 0.12 * rng.normal(0, 1, n)
    return tone + noise, sample_rate


def clipping(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A 220Hz tone driven well past full scale and hard-clamped to [-1, 1] — what happens
    when input gain is set too high."""
    signal = _harmonic_tone(220.0, 2.0, amplitude=2.5, sample_rate=sample_rate)
    return np.clip(signal, -1.0, 1.0), sample_rate


def silence(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """True digital silence — the floor case for every "too quiet" / "no voice" check."""
    return np.zeros(int(sample_rate * 2.0)), sample_rate


def instrument_contamination(sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """A 220Hz "voice" tone mixed with a simultaneous, unrelated 330Hz "instrument" tone
    (e.g. someone practicing with background music or an accompanying instrument) — tests
    whether pitch tracking gets confused by a second concurrent pitched source."""
    duration_s = 2.0
    voice = _harmonic_tone(220.0, duration_s, amplitude=0.4, sample_rate=sample_rate)
    instrument = _harmonic_tone(
        330.0,
        duration_s,
        amplitude=0.3,
        sample_rate=sample_rate,
        harmonic_amplitudes=(1.0, 0.6, 0.3),
    )
    return voice + instrument, sample_rate


GOLDEN_VOICE_SET: dict[str, Callable[[int], tuple[np.ndarray, int]]] = {
    "stable_vowel": stable_vowel,
    "unstable_vowel": unstable_vowel,
    "quiet_vowel": quiet_vowel,
    "loud_vowel": loud_vowel,
    "pitch_glide": pitch_glide,
    "low_note": low_note,
    "high_note": high_note,
    "vibrato": vibrato,
    "breathy": breathy,
    "noisy_room": noisy_room,
    "clipping": clipping,
    "silence": silence,
    "instrument_contamination": instrument_contamination,
}
