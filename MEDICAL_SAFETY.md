# VepAIr Medical Safety Policy

VepAIr is **not** a medical diagnostic device. This document is binding on all product copy,
UI strings, AI-generated text, and analysis output, at every stage.

## 1. What VepAIr must never say

VepAIr must never present a diagnosis or claim to observe anatomy it cannot observe. Prohibited
patterns include (non-exhaustive):

- "You have vocal nodules."
- "Your vocal folds are swollen."
- "Your left vocal fold is damaged."
- "You have muscle tension dysphonia."
- Any statement naming a specific pathology, structural condition, or diagnosis.

A consumer microphone (and, later, a front-facing camera) cannot directly observe the vocal
folds or larynx. No feature may claim otherwise, regardless of confidence.

## 2. What VepAIr may say instead

Observations must be phrased as measured deviations from the user's own history, not clinical
findings:

> "Several acoustic measurements have changed significantly from your established baseline."

> "Your voice appears less stable than your typical measurements today."

> "Consider reducing vocal load and consulting a qualified voice professional if this change
> persists, or if you have pain, sudden voice loss, breathing difficulty, coughing blood, or
> other concerning symptoms."

## 3. Escalation language

Any time a rule in this file would otherwise fire on symptoms suggesting urgent care (pain,
sudden voice loss, breathing difficulty, coughing blood), the copy must recommend consulting a
qualified professional — never instruct the user to "push through it," and never suppress the
recommendation because it might reduce engagement.

## 4. Baseline confidence language

Baseline confidence (Stage 4, a percentage) and recovery-score confidence (Stage 5, a plain
label — "Score 72 / Confidence: Moderate", per the product brief's own example) are both
**product indicators of data sufficiency**, not statistically validated clinical probabilities.
UI copy and any generated text must label them as such, e.g. "Baseline confidence: 42% (based
on 5 of the recommended 7–14 sessions)" rather than implying a scientific probability of health.

## 5. Inspectable-by-design architecture (not a clinical roadmap commitment)

**VepAIr has no clinical or regulatory ambitions, planned or hypothetical — see `ROADMAP.md`'s
Stage 12 note.** This section is an engineering-quality principle only, unrelated to any future
product plan: the data model (`ARCHITECTURE.md`) should stay traceable and inspectable — every
measurement traceable to its raw inputs, every recommendation's logic inspectable (see "Why did
I get this score?" in `ROADMAP.md` Stage 5) — because that is simply good practice for a
measurement product, the same reason Stage 5's score shows its own work. It is not there to
prepare for eventual clinical review, which is explicitly not planned.

## 6. Feature flags for unproven claims

Any experimental or clinical-sounding metric (e.g. the backlogged computer-vision posture
inference idea — see `ROADMAP.md`)
must ship behind a feature flag and be clearly labeled experimental. It must never be presented
with the same visual confidence as a validated acoustic measurement.

## 7. Exercise safety

- No exercise library entry (Stage 6) may include aggressive screaming/distortion techniques
  without an established, qualified methodology and explicit safeguards — none exist yet, so
  none are included. Confirmed: the Stage 6 library (`app/exercise_library.py`) is built
  entirely from standard SOVT/breathing/humming/trill/resonance techniques.
- If a user reports pain, the system must never recommend "pushing through" it. Recommendation
  logic (Stage 6) must treat reported pain as a hard stop toward rest/professional-care guidance,
  not a parameter to route around. Confirmed: `app/exercise_routine.py`'s discomfort rule is
  checked first and cannot be outvoted by any other signal — see `ARCHITECTURE.md` section 6f.

## 8. Real-time coaching feedback

- Live coaching (Stage 7) must never claim the microphone can reliably identify anatomical
  tension — a consumer microphone measures acoustic signal (pitch, volume, timing), not
  physiology. Feedback stays phrased around what was actually measured ("Reduce volume
  slightly," "Try a gentler onset") and never around a claimed physical cause ("your throat is
  tense," "your larynx is constricted").
- Live feedback must not overwhelm the user — a configurable minimum interval between messages
  (`apps/web/src/lib/feedbackEngine.ts`'s `minIntervalMs`) is mandatory, not optional polish.
- "Stay within your comfortable range" must be checked against the user's own personal baseline
  (Stage 4), never a population vocal-range norm — consistent with "personal baseline before
  population assumptions" (`ROADMAP.md`). If no personal baseline exists yet, that specific
  feedback rule simply doesn't fire — never a fabricated target range.

## 9. Track selection and plan graduation

- "Vocal Repair" and "Vocal Improvement" (Stage 9) are **self-selected programs, never
  diagnoses**. VepAIr has no way to know whether a user ever had a real vocal injury — the
  track is whatever the user picked, not an assessment of their condition.
- "Graduating" from Repair to Improvement (`app/vocal_plan.py`'s `assess_graduation_readiness`)
  must only ever be described as "your recent data has been consistently stable," **never**
  "you are healed," "your voice has recovered," or any other clinical-sounding claim.
  Graduation criteria and their pass/fail reasons must always be shown in full (never just the
  binding one), consistent with Section 5's inspectability requirement.
- A 90-day plan's targets (`VocalPlan.target_milestones`) must stay phrased as personal,
  optional goals ("gently extend," "if it feels comfortable") — never a required outcome or a
  guarantee, and never framed against a population range.
- Track choice may only ever change how readily Stage 8's adaptive challenge mode engages, or
  how large an optional range-stretch suggestion is — it must never be able to weaken or bypass
  any Stage 6 hard safety rule (discomfort, red recovery status, heavy-load-plus-fatigue). This
  is enforced identically regardless of track and is regression-tested.

## 10. Share My Progress (Stage 10)

- Exported images may only ever show real, already-measured numbers — never an estimate, a
  rounded-to-look-better value, or a fabricated metric. A metric with no real data behind it is
  omitted from the image, never invented or interpolated.
- **Progress must be reported honestly, including decline.** A metric that has gotten worse
  (e.g. rising fatigue, a shrinking comfortable range) must be displayed exactly as measured,
  with no reframing, hidden sign-flipping, or selective omission to make the result look more
  positive than the data supports.
- "Measurement Confidence" / "LOW MEASUREMENT CONFIDENCE" labeling is the same
  data-sufficiency concept as Section 4, not a claim about clinical validity — the same rule
  applies here as everywhere else in the app.
- No register classification, diagnosis, or population-comparison language may appear on either
  exported image — the same Section 1/2 rules apply, unmodified, to this feature.

## 11. Enforcement

- This file is reviewed at the end of every stage as part of the stage completion checklist.
- Any UI copy, AI-generated explanation, or analysis label that could be read as a diagnosis is a
  **critical bug** and blocks stage sign-off.
- Golden/example phrasings in this file may be reused verbatim; new copy should be checked
  against Sections 1–2 before shipping.
