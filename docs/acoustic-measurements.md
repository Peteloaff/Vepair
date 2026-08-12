# Acoustic Measurements Reference

Every measurement VepAIr computes on a voice recording, documented per the Stage 3
requirement: definition, algorithm, library, units, valid input type, limitations, and
expected measurement variability. Implementation:
`packages/audio-engine/src/vepair_audio_engine/measurements.py`.

**Nothing here is a medical or diagnostic measurement.** These are standard acoustic/DSP
quantities used in voice science and speech research. See `MEDICAL_SAFETY.md` for the binding
rules on how (and how not) to present them to a user — in particular, never as a diagnosis.

## How to read this document

Each metric lists:
- **Definition** — what it means, in plain terms.
- **Algorithm** — how it's actually computed.
- **Library** — which library/function produces it (nothing here is hand-rolled DSP).
- **Units**.
- **Valid input** — which recording types (sustained phonation vs. running speech/singing vs.
  glide) it's scientifically meaningful for. Where a metric is computed on an input type it
  isn't valid for, VepAIr returns `null`, never a number.
- **Limitations** — known failure modes and caveats.
- **Expected variability** — how much a measurement can be expected to move between two
  otherwise-similar recordings from the same person, purely from normal measurement/technical
  variation (not vocal change). This is what a future personal baseline (Stage 4) needs to know
  before it can tell "normal noise" apart from a real trend.

## Which sample types support which metrics

| Metric group | sustained_ah / ee / oo / hum | glide | sentence / singing |
|---|---|---|---|
| F0 mean/median/min/max, pitch stability | ✅ | ✅ (describes the swept range, not a "resting" pitch) | ✅ (describes running-speech/song pitch, not sustained-phonation pitch) |
| Jitter, shimmer, HNR | ✅ | ❌ (`null`) | ❌ (`null`) |
| RMS loudness, spectral centroid/rolloff, ZCR, duration, voiced ratio | ✅ | ✅ | ✅ |

Jitter/shimmer/HNR are withheld (not computed) outside sustained phonation — see each metric's
Limitations section for why.

---

## Fundamental frequency (F0) — mean, median, "reliable" min/max

**Definition:** the rate of vocal fold vibration — perceived as pitch. VepAIr reports four
summary statistics over a recording's per-frame F0 track, not a single instantaneous number.

**Algorithm:** Praat's autocorrelation-based pitch-tracking algorithm (`Sound: To Pitch`),
computed per short analysis frame (Praat's default ~10ms time step) across the recording. Only
frames Praat marks as voiced contribute. Mean and median are taken over all voiced frames.
"Minimum reliable" and "maximum reliable" are the **5th and 95th percentile** of voiced-frame
F0 — not the absolute min/max. Absolute min/max are extremely sensitive to a single
octave-error frame (a well-known pitch-tracker failure mode — see `docs/golden-voice-set.md`'s
`instrument_contamination` case); percentiles give a robust range that one bad frame can't
distort. This is a deliberate, documented choice: **"reliable" means percentile-based, not
"the true extremes were measured."**

**Library:** Parselmouth (Python bindings to Praat), `Sound.to_pitch()`.

**Units:** Hz.

**Valid input:** any recording with voiced content. Meaningful for all sample types, but
interpreted differently — a sustained vowel's F0 describes one held pitch; a glide's F0
range describes the swept range; a sentence/song's F0 range describes normal pitch variation
in speech/singing, not a single "resting pitch."

**Limitations:**
- Pitch floor/ceiling are fixed at 75-1000Hz (`F0_FLOOR_HZ`/`F0_CEILING_HZ`) — covers low bass
  through most falsetto/head-voice and legit soprano singing, but a pitch outside that range
  won't be tracked at all. Genuine whistle register (roughly C6/~1050Hz and above) sits above
  the ceiling — a real, current limitation, not silently mishandled. (Originally 600Hz; raised
  in Stage 8 after a falsetto-range test tone at 660Hz was tracked as its own octave-down
  subharmonic because it fell outside the old ceiling entirely — see `CHANGELOG.md` Stage 8.)
- Octave errors (reporting exactly double or half the true pitch) are a known failure mode of
  every autocorrelation-based pitch tracker, worse with background noise or a concurrent
  pitched source (see the `instrument_contamination` fixture).
- Silence, very breathy phonation, or very short recordings can leave too few voiced frames
  for a meaningful statistic — in that case all four fields are `null`, not zero.

**Expected variability:** on a clean, steady synthetic tone, mean/median F0 reproduce a known
frequency to within ~0.001Hz (see `tests/unit/test_measurements.py`). On a **real human voice**
repeating "the same" sustained vowel on different days, expect natural mean-F0 variation on the
order of a few Hz to a few percent even with no underlying vocal change — normal physiological
and recording-condition variation, not measurement error. Stage 4's personal baseline exists
specifically to characterize this per-person, rather than assuming a fixed tolerance.

---

## Pitch stability

**Definition:** how much a sustained pitch wanders over the course of one recording, in a
musically meaningful unit.

**Algorithm:** the standard deviation of every voiced frame's F0, expressed in semitones
relative to the recording's own median F0: `12 * log2(frame_f0 / median_f0)`, then
`std()` of that array. Semitones (not Hz) because a given Hz-wobble means something very
different at 100Hz vs. 400Hz — semitones normalize for that.

**Library:** derived from Parselmouth's per-frame pitch track (numpy for the statistics).

**Units:** semitones (standard deviation).

**Valid input:** most meaningful for sustained phonation (a genuinely "held" pitch). Computed
for glide/sentence/singing too, but there it partly reflects intentional pitch movement, not
just instability — interpret with that in mind.

**Limitations:** needs at least 2 voiced frames; requires a non-zero median F0. Like the F0
percentiles above, sensitive to occasional octave-error frames pulling the distribution wide,
though the percentile-trimmed F0 range partially protects against the worst of this. **Does
not distinguish intentional musical vibrato from noise-like pitch instability** — both
increase F0 standard deviation the same way. Confirmed with the `vibrato` fixture: a full,
coherent ±50-cent vibrato sweep (std dev ≈ amplitude/√2 ≈ 0.35 semitones, matching theory)
measures *higher* pitch_stability than the `unstable_vowel` fixture's smaller random per-cycle
jitter (0.12 semitones) — a controlled, musical vibrato can read as "less stable" than mild
genuine unsteadiness. See `tests/unit/test_golden_voice_set.py`.

**Expected variability:** near 0 on a synthetic clean tone (see `stable_vowel` fixture, target
< 0.05 semitones). A real sustained "Ah" from an untrained voice commonly falls in the
0.1-0.5 semitone range; a trained singer holding a note steadily may be lower. No fixed
pass/fail threshold is implied — see `MEDICAL_SAFETY.md`.

---

## Jitter (local)

**Definition:** cycle-to-cycle variation in the *period* (duration) of consecutive glottal
vibration cycles — a classic measure of short-term pitch instability, used extensively in
voice science.

**Algorithm:** Praat's "local jitter": average absolute difference between consecutive
periods, divided by the average period. Requires first extracting a `PointProcess` (glottal
pulse timestamps) via Praat's cross-correlation periodicity detection
(`To PointProcess (periodic, cc)`), then `Get jitter (local)`.

**Library:** Parselmouth, calling Praat's `PointProcess` and jitter functions directly (not a
reimplementation).

**Units:** percent (Praat's raw output is a ratio; VepAIr multiplies by 100).

**Valid input:** **sustained phonation only** (`sustained_ah`/`ee`/`oo`/`hum`) — see
`SUSTAINED_PHONATION_SAMPLE_TYPES`. Jitter is only scientifically meaningful when measuring
variation around one intentionally-steady pitch target. On a glide (pitch is deliberately
changing) or running speech/song (voiced segments are short and interspersed with
consonants/pauses/pitch changes), "period-to-period variation" conflates real instability with
intentional pitch movement, producing a number that looks precise but isn't a valid jitter
measurement. VepAIr returns `null` for these sample types rather than compute a number that
would misrepresent what it is.

**Limitations:**
- Needs enough consecutive voiced frames to find reliable periods
  (`MIN_VOICED_FRAMES_FOR_PERIODICITY_MEASURES`); below that, `null`.
- Sensitive to background noise and low recording SNR, which corrupt period-boundary
  detection — a noisy *recording* can look like an unstable *voice* (see the `noisy_room`
  fixture, and Stage 2's separate recording-quality noise heuristic, which exists partly to
  flag this ambiguity rather than let it masquerade as a voice-quality finding).
- Vibrato (an intentional, musical pitch modulation) will read as somewhat elevated jitter —
  see the `vibrato` fixture — because Praat's local-jitter window is short enough that fast
  vibrato partially resembles cycle-to-cycle instability. This is a real limitation, not a bug.

**Expected variability:** near 0% on a synthetic clean tone (target < 0.001%, see
`tests/unit/test_measurements.py`). Commonly cited rough orientation figures in voice-science
literature put "typical"/healthy sustained-vowel jitter under roughly 1%, with elevated values
common in unsteady or pathological voices — but VepAIr does not apply any such threshold itself
(no "normal/abnormal" label is ever shown) and these figures vary considerably by study,
equipment, and vowel. This is provided as general orientation for engineers/clinicians reading
this document, not as a product-facing threshold.

---

## Shimmer (local)

**Definition:** cycle-to-cycle variation in *amplitude* (loudness) of consecutive glottal
vibration cycles — the amplitude counterpart to jitter.

**Algorithm:** Praat's "local shimmer": average absolute difference between consecutive
cycles' peak amplitude, divided by the average amplitude, computed from the same
`PointProcess` used for jitter (`Get shimmer (local)`).

**Library:** Parselmouth / Praat, as above.

**Units:** percent.

**Valid input:** sustained phonation only — same reasoning as jitter.

**Limitations:** same period-detection dependency as jitter; also sensitive to microphone
distance/handling changes during a recording (physical, not vocal, sources of amplitude
variation) — another reason recording-quality issues shouldn't be read as voice findings.

**Expected variability:** near 0% on a synthetic clean tone (target < 0.001%). Commonly cited
rough orientation figures put "typical" sustained-vowel shimmer under roughly 3-4%; same
caveats as jitter above apply — general orientation only, not a product threshold.

---

## Harmonics-to-noise ratio (HNR)

**Definition:** the ratio of the periodic (harmonic, voice) component of a signal to its
aperiodic (noise) component — a measure of voice "clarity" vs. breathiness/noise content, and
one of the more validated acoustic correlates of perceived voice quality in the literature.

**Algorithm:** Praat's harmonicity via autocorrelation (`Sound.to_harmonicity()`), averaged
over the recording (`Get mean`).

**Library:** Parselmouth / Praat.

**Units:** dB.

**Valid input:** sustained phonation only, same reasoning as jitter/shimmer — HNR's
autocorrelation method assumes a stable periodic signal.

**Limitations:** **HNR does not reliably detect clipping** — clipping adds harmonically
*correlated* distortion (extra energy at multiples of F0), which autocorrelation-based HNR
doesn't penalize the way it penalizes genuine noise. See the `clipping` fixture in
`docs/golden-voice-set.md`, where a badly clipped tone still measures ~70dB HNR. This is
exactly why Stage 2's recording-quality clipping check is a separate, independent gate — HNR is
not a substitute for it.

**Expected variability:** a clean synthetic tone measures extremely high (>100dB — there is
essentially zero real "noise" in a pure synthesized signal, which is higher than any real
voice will ever measure). Real human phonation commonly falls anywhere from single digits
(breathy/noisy) to the 20s (clear voice), highly dependent on recording conditions as well as
voice quality — which is precisely why a single HNR reading in isolation is not diagnostic;
see `MEDICAL_SAFETY.md`.

---

## RMS loudness

**Definition:** the root-mean-square amplitude of the waveform — a standard measure of a
signal's average energy/loudness (not a calibrated sound-pressure-level measurement, since
there's no reference calibration to a physical microphone's absolute sensitivity).

**Algorithm:** `sqrt(mean(sample^2))` over all samples.

**Library:** numpy.

**Units:** unitless, in normalized full-scale amplitude (0.0-1.0 range for non-clipped audio).

**Valid input:** any recording with audio content.

**Limitations:** **not calibrated sound pressure level (dB SPL)** — it reflects the gain
staging of whatever microphone/device/distance was used, not an absolute loudness a clinician
could compare across different recording setups. Comparable only within a consistent recording
setup (same device/distance/gain) — exactly why Stage 2 captures device metadata per session.

**Expected variability:** deterministic given fixed input; on repeated real recordings of "the
same" loudness, expect substantial variation from mic distance/gain/room differences —
dominated by recording-setup variance, not measurement noise.

---

## Spectral centroid

**Definition:** the "center of mass" of the frequency spectrum — informally, where most of the
signal's energy is concentrated. Correlates with perceived brightness/sharpness of a sound.

**Algorithm:** librosa's `spectral_centroid` (STFT-based, default frame/hop settings),
averaged over all analysis frames.

**Library:** librosa.

**Units:** Hz.

**Valid input:** any recording with audio content.

**Limitations:** a broadband, generic spectral-shape descriptor — not specific to voice in the
way F0/jitter/shimmer/HNR are. Affected by microphone frequency response, not just the voice
itself.

**Expected variability:** for a pure tone, centers very close to the fundamental (see
`stable_vowel` — measures ~222Hz for a 220Hz tone, since the harmonic content pulls it
slightly above the fundamental). Real voice recordings vary with vowel, mic, and room
acoustics.

---

## Spectral rolloff

**Definition:** the frequency below which a specified percentage (librosa default: 85%) of the
signal's total spectral energy is contained — another standard brightness/timbre descriptor.

**Algorithm:** librosa's `spectral_rolloff`, averaged over all analysis frames.

**Library:** librosa.

**Units:** Hz.

**Valid input:** any recording with audio content.

**Limitations:** same generic, non-voice-specific caveats as spectral centroid.

**Expected variability:** for a pure/near-pure tone, sits somewhat above the centroid (see
`stable_vowel` — ~238Hz for a 220Hz tone, reflecting the higher harmonics). Varies with vowel
and recording conditions on real voice.

---

## Zero-crossing rate (ZCR)

**Definition:** how often the waveform crosses zero amplitude per unit time — a crude but
cheap proxy for signal frequency content/noisiness (voiced speech tends to have a lower ZCR
than unvoiced/fricative speech or noise).

**Algorithm:** librosa's `zero_crossing_rate`, averaged over all analysis frames.

**Library:** librosa.

**Units:** unitless (crossings per sample, i.e. fraction of samples where a sign change
occurs).

**Valid input:** any recording with audio content.

**Limitations:** a very simple, generic time-domain feature — easily disturbed by DC offset or
low-frequency noise. Not specific to voice.

**Expected variability:** for a pure tone at frequency f and sample rate sr, ZCR ≈ 2f/sr
deterministically (verified in `tests/unit/test_measurements.py`: a 220Hz tone at 44.1kHz
measures ZCR ≈ 0.00989, matching the predicted 2×220/44100 ≈ 0.00998 to within FFT
frame-boundary effects). Real voice varies by vowel and noise content.

---

## Duration

**Definition:** the length of the recording.

**Algorithm:** `sample_count / sample_rate`.

**Library:** direct arithmetic (numpy/soundfile provide the sample count and rate).

**Units:** seconds.

**Valid input:** any recording.

**Limitations:** none beyond WAV decoding correctness — this is exact arithmetic, not an
estimate. (Note: this is a separate field from Stage 2's own duration check in
`apps/api/app/audio_quality.py`, which exists purely as a fast quality gate before any DSP
runs; the two are computed independently and should agree.)

**Expected variability:** none (deterministic).

---

## Voiced/unvoiced ratio

**Definition:** the fraction of analysis frames Praat classified as voiced (i.e. exhibiting
detectable periodic vocal-fold vibration) out of all frames in the recording.

**Algorithm:** `count(frames where F0 > 0) / count(all frames)`, from the same Praat pitch
track used for F0.

**Library:** Parselmouth / Praat.

**Units:** unitless ratio, 0.0-1.0.

**Valid input:** any recording. Interpretation differs by type — a clean sustained vowel
should read near 1.0; a spoken sentence naturally has unvoiced consonants and pauses and
should read well below 1.0; total silence reads 0.0.

**Limitations:** depends on the same pitch-tracking algorithm as F0, with the same octave-error
and noise-sensitivity caveats. A very noisy recording can read a falsely low voiced ratio if
noise prevents periodicity detection even where the person was actually voicing.

**Expected variability:** near 1.0 (deterministically, ±a few frames at the recording's start/
end where the analysis window doesn't fully overlap signal) for any clean sustained-phonation
fixture. 0.0 for silence. No general "expected" value for running speech — depends entirely on
content.

---

## A note on additional measurements

The Stage 3 brief asks to "research whether additional measurements are scientifically and
technically valid before adding them." No additional measurements were added beyond the
required list for this stage — the fourteen fields above (F0 mean/median/min/max, pitch
stability, jitter, shimmer, HNR, RMS loudness, spectral centroid, spectral rolloff, ZCR,
duration, voiced ratio) match the spec exactly. Candidates considered and deliberately
**not** added yet:

- **Formants (F1/F2/etc.)** — scientifically well-established and Parselmouth supports formant
  tracking, but formant analysis is highly vowel-and-speaker-dependent and would need real
  validation work (and likely per-vowel reference data) to be meaningful here; deferred rather
  than added speculatively.
- **Cepstral Peak Prominence (CPP)** — increasingly considered a more robust dysphonia
  correlate than jitter/shimmer/HNR in recent voice-science literature, and a strong future
  candidate, but not in the Stage 3 spec's required list and not implemented here to keep this
  stage's scope to exactly what was asked for.
