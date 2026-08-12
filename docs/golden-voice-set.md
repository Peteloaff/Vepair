# Golden Voice Set

A permanent, synthetic, deterministic audio fixture set used to regression-test the acoustic
analysis engine (`packages/audio-engine`). Referenced from `TESTING.md`'s test pyramid.

**Location:** `data/fixtures/golden-voice-set/*.wav` (checked into the repo — small files,
deterministic generation, no reason to regenerate on every test run).

**Generator:** `packages/audio-engine/src/vepair_audio_engine/fixtures.py`. Regenerate with
`python packages/audio-engine/scripts/generate_golden_voice_set.py` if a generator changes.

**Why synthetic, not real recordings:** every fixture here is built from understood,
documented signal-processing operations (additive sine synthesis, frequency modulation,
filtered noise) — deterministic (seeded), reproducible on any machine, and with no licensing
question. Real human voice samples would need explicit consent/licensing per `PRIVACY.md` and
aren't needed to validate that the measurement code is *computing what it claims to compute*.

Every release should run the full measurement suite against this set; if output drifts beyond
the tolerances documented in `docs/acoustic-measurements.md` or `tests/unit/`, that's a
regression — investigate before shipping, per `TESTING.md`.

## The fixtures

| File | What it is | What it's for |
|---|---|---|
| `stable_vowel.wav` | Clean, steady 220Hz harmonic tone (fundamental + 3 decaying harmonics) | Baseline "everything should work" case — near-zero jitter/shimmer, high HNR |
| `unstable_vowel.wav` | 220Hz tone with injected per-cycle frequency (~1.5%) and amplitude (~6%) randomness | Jitter/shimmer should read clearly elevated vs. the stable baseline |
| `quiet_vowel.wav` | Same as stable_vowel at amplitude 0.05 | Recording-quality "too quiet" gate; voice measurements should be amplitude-independent |
| `loud_vowel.wav` | Same as stable_vowel at amplitude 0.9 (not clipping) | Confirms measurements are stable near full scale without clipping |
| `pitch_glide.wav` | 150Hz→500Hz sweep over 2s (constant rate in log-frequency) | F0 range/min/max should span the swept range; jitter/shimmer are N/A by design (not sustained phonation) |
| `low_note.wav` | Stable 82Hz tone (≈E2) | Low end of the pitch-floor range (F0_FLOOR_HZ=75Hz) |
| `high_note.wav` | Stable 440Hz tone (A4) | Mid-high end of typical vocal range |
| `vibrato.wav` | 220Hz tone with 5.5Hz-rate, ±50-cent sinusoidal vibrato | Realistic singer vibrato; jitter/shimmer read moderately elevated (expected — see limitations in acoustic-measurements.md) |
| `breathy.wav` | 220Hz tone mixed with high-passed noise | HNR should read clearly lower than stable_vowel — approximates breathiness, not a validated clinical model |
| `noisy_room.wav` | 220Hz tone with broadband background noise mixed throughout | HNR should read even lower than breathy; possible_background_noise (Stage 2) should flag |
| `clipping.wav` | 220Hz tone driven past full scale, hard-clamped | Stage 2's clipping detector must flag this. Notably, Praat's HNR does **not** drop much — clipping adds harmonic (correlated) distortion, not noise, which is exactly why recording-quality clipping detection is a separate check from voice-quality HNR, not redundant with it |
| `silence.wav` | True digital silence | Every measurement should come back `None` (unmeasurable), never a fabricated zero; voiced_ratio = 0.0 |
| `instrument_contamination.wav` | 220Hz "voice" + simultaneous 330Hz "instrument" tone | Demonstrates a real pitch-tracking failure mode — see below |

## A documented finding: `instrument_contamination`

220Hz and 330Hz are both integer multiples of 110Hz (220 = 110×2, 330 = 110×3). Mixed together,
they form the 2nd and 3rd harmonics of a **missing fundamental** at 110Hz, and Praat's pitch
tracker locks onto that missing fundamental rather than either real tone — reporting F0≈110Hz,
an octave below the actual "voice" signal.

This isn't a bug in the measurement code; it's a correct demonstration of a genuine, textbook
pitch-tracking failure mode, and exactly why this fixture exists: background music or a
simultaneous instrument can make F0 tracking silently report a plausible-looking but wrong
number. There is no current mitigation for this beyond the existing background-noise heuristic
(Stage 2), which this signal does not reliably trigger since the contaminating tone is
periodic, not noise-like. Documented here as a known limitation, not fixed.
