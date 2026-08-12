# VepAIr Features

A feature-by-feature reference for what VepAIr does today and why each piece exists. For a
step-by-step "how do I actually use this" walkthrough, see [`USER_GUIDE.md`](USER_GUIDE.md)
instead — this document is organized by feature, not by user journey, and is meant as a
catalog you can hand to a tester, investor, or use as source material for the marketing site.

VepAIr is **not** a medical diagnostic device and never claims to be. See
[`MEDICAL_SAFETY.md`](MEDICAL_SAFETY.md) for the binding rules behind every feature below —
every measurement is compared only to the user's own history, never to a population norm, and
nothing in the app ever says "you're healed" or names a medical condition.

## Core idea

VepAIr learns *your* voice specifically — your own baseline, your own normal range, your own
patterns of fatigue and recovery — and uses that personal history (not a generic model of
"voices in general") to guide daily training and flag when something looks meaningfully
different from your usual. Everything below is in service of that one idea.

## Live features

### Account & onboarding
Email/password signup, login, and password reset. Onboarding immediately offers a track choice
(**Vocal Repair** or **Vocal Improvement**) plus a short, entirely optional background
questionnaire (voice use, singer status, style, practice frequency, goals, prior coaching
history). No question here is required to use the app.

### Daily Vocal Check-In
A 30-second daily journal: perceived voice quality, fatigue, throat discomfort, sleep, vocal
load, hydration/alcohol/smoke exposure, and optional free-text notes on illness or reflux
symptoms. Every field is individually skippable. This is the subjective half of the data VepAIr
uses to build your daily score and adapt your exercises.

### Guided Voice Recording
A structured ~3–5 minute recording session: sustained "Ah"/"Ee"/"Oo," a comfortable hum, a
gentle pitch glide, a standardized reading passage, and an optional singing sample. Every
recording is automatically analyzed — pitch (F0), jitter, shimmer, harmonics-to-noise ratio
(HNR), and more — plus a 0–100 recording quality score that catches bad takes (too quiet,
clipped, too short) independent of the voice measurements themselves. This is the objective half
of the data.

### Acoustic Analysis Engine
The DSP layer underneath every recording (`packages/audio-engine`), built on Praat/Parselmouth
and librosa — the field-standard tools for exactly these measurements, not a custom or invented
algorithm. Every metric is documented individually in
[`docs/acoustic-measurements.md`](docs/acoustic-measurements.md): what it measures, the exact
algorithm, units, and known limitations. Validated against a permanent synthetic "Golden Voice
Set" regression suite so measurements can't silently drift as the code changes.

### Personal Vocal Baseline
Once enough sustained-vowel recordings exist, VepAIr computes a personal baseline per metric
(robust median + MAD statistics — resistant to outlier bad takes) with a confidence label
(insufficient → low → moderate → high/established) and flags recordings that look like anomalies
against your own recent normal. This baseline is the yardstick everything else measures against
— never a population average.

### VepAIr Score
A daily 0–100 training/recovery indicator with a GREEN/YELLOW/RED status, fully explainable via
a "why did I get this score?" breakdown showing exactly which measurements contributed and how
much. Explicitly not a medical score — a transparent readiness signal, not a black box.

### Adaptive Voice Exercises
A 23-exercise library across 12 categories (breathing, humming, lip/tongue trills, resonant
voice, SOVT/straw phonation, sirens/glides, range exploration, cooldown, and more), assembled
into a 5/10/15/20-minute routine that adapts daily to your recovery status, fatigue, recent
vocal load, sleep, and baseline deviations. Reported discomfort always caps the routine to the
gentlest exercises available — the system never suggests "pushing through" anything, no matter
what the data says.

### Live AI Vocal Coach
Real-time coaching feedback (pitch, volume, onset, glide smoothness) during exercises that have
a vocal signal, computed entirely client-side via the Web Audio API — nothing is uploaded for
this part. If the microphone is denied or unavailable, the exercise still works fine without
live feedback.

### Vocal Range Mapping
A quick, comfortable range test capturing your low, high, and optional falsetto/head-voice
notes, visualized on a piano-style keyboard with your historical best and 30/90-day change
tracked in semitones. Framed explicitly as "your own range over time," never a classification of
voice type.

### Exercise Trends & Adaptive Challenge
Exercises with a measurable target (e.g. range-extension exercises) are tracked for
improving/declining trends over time, and the system gently increases challenge as your data
supports it — always subordinate to safety rules, reported discomfort, and recovery status. It
never overrides those to chase progress.

### Personalized Vocal Track & 90-Day Plan
Once you've picked a track and have both a recent recording and a vocal range test, VepAIr
generates a 90-day plan specific to your own measured data — a stability goal on Repair, a
range-extension goal on Improvement, each with a real target date. Repair-track users are
automatically moved up to Improvement once their recent data looks consistently stable — always
phrased as "consistently stable," never "healed."

### Share My Progress
Generates two ready-to-post, vertical (1080×1920) images — today's snapshot and a start-vs-now
comparison — built entirely from real, already-measured data. Any metric you don't have data for
is simply omitted, never invented or estimated. Exports via native share sheet or direct
download.

### Progress Dashboard
The long-range view: your VepAIr Score charted over any range up to all-time, your daily
training streak and consistency (with a calendar-style activity grid), and every tracked
exercise's current trend in one place.

## Planned / not yet built

| Feature | Status |
|---|---|
| VepAIr Coach — professional portal for vocal coaches/studios to assign training and view a consented user's progress | Scoped (Stage 12), not started — see [`ROADMAP.md`](ROADMAP.md) |
| Mobile app packaging (Android/Play Store) | Planned as part of the post-Stage-11 deployment milestone, not started |
| Recording deletion | Not yet built — recordings currently persist indefinitely once uploaded |
| Real email delivery for password reset | Currently dev-mode only (token printed to server logs) — no email provider configured yet |
| Computer Vision Coach, Wearables + Vocal Load | Backlog — deprioritized, revisited only if they become a priority |

**Explicitly and permanently out of scope**: anything clinical or regulatory ("VepAIr Clinical").
VepAIr is an information/training tool, for consumers and (eventually) vocal coaches/studios —
not a credentialed clinical product, now or in any planned future phase.
