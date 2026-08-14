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

## 12. VepAIr Coach professional notes (Stage 12, Phase II)

Coach-authored freeform notes are a genuinely new risk surface: everywhere else in the app,
clinical-sounding language is prevented by controlling VepAIr's own copy (Sections 1-2). A
coach's notes are the first place a human, not VepAIr, writes freeform text another user reads —
this section documents the real, concrete mitigations, not just the intent to have some.

- **Non-dismissible disclaimer**, shown above the note composer and above the singer's note
  list, every time: *"Notes are for coaching purposes only — not a medical or clinical record.
  Do not record diagnoses, medical history, or clinical assessments here. The singer can read
  every note you write."*
- **Server-side blocklist** (`apps/api/app/coach_notes.py`'s `BLOCKED_TERMS`), mirroring Section
  1's prohibited-pattern list (`nodule`, `dysphonia`, `vocal fold`, `vocal cord`, `diagnos`,
  `damaged`, `polyp`, `lesion`, `paralysis`, `paresis`). A match returns the flagged terms to the
  frontend as a warning **but the note still saves** — this is friction, not a hard block,
  because legitimate escalation language ("this sounds like something to have an ENT look at,"
  consistent with Section 3) must never be prevented by the same mechanism meant to discourage
  a coach writing a diagnosis.
- **2000-character server-enforced limit** (Pydantic `max_length`, 422 if exceeded) — keeps notes
  to short coaching observations by construction, not just by convention.
- **Immutable, soft-delete only**: a note is never edited in place; a mistake is deleted (never
  physically removed — the singer's read access to their own history is never revoked) rather
  than silently rewritten, so there is always an honest record of what was actually written and
  read.
- **Operational review, sized for pilot scale, not decorative**: `coach_notes WHERE
  flagged_terms IS NOT NULL` is a two-line SQL query the founder can run periodically during the
  pilot to see what triggered the blocklist. This is deliberately not a moderation UI or
  automated escalation — a small, unpaid pilot with a handful of real coaches does not need one
  yet; building one before real usage data exists would be guessing at a problem's actual shape.
  Revisit if Phase III (paid) scales this past what manual review can keep up with.

None of this makes coach notes a clinical record — Sections 1-2's prohibitions apply to this
surface exactly as they apply to VepAIr's own generated copy. The difference here is enforcement
mechanism: VepAIr's own copy is controlled by not writing prohibited language in the first place;
a coach's freeform text can't be pre-controlled the same way, so the mitigations above are the
next-best real defenses, not a weaker standard.

## 13. Rest day recommendations and coach-authored custom exercises (post-Stage-12 additions)

**Rest day recommendations** (`app/exercise_routine.py`'s `_should_recommend_rest_day`) are a
stricter tier above the existing "gentlest exercises only" cutoff (Section 7's discomfort
override), triggered by either severe reported discomfort (>= 9/10) or 3+ consecutive days of a
stored "red" recovery status. Same rules as everywhere else in this file apply:
- **Never a hard block** — the routine underneath still resolves to a real, safe (lowest-
  intensity) routine even when a rest day is recommended, so a user who chooses to exercise
  anyway is never stopped from doing so. Recommending rest is guidance, not gatekeeping.
- **Escalation language, not a diagnosis**: copy follows Section 2/3's pattern exactly — e.g.
  "Today looks like a good day to rest your voice completely. If this continues, consider
  checking in with a qualified voice professional." Never framed as a clinical order.

**Coach-authored custom exercises** (`POST /api/v1/coach/exercises`) are a real, deliberate
trade-off, not an oversight: unlike `SEED_EXERCISES` (Section 7 — hand-curated, explicitly
excludes any aggressive/unproven technique), a coach's custom exercise is immediately active and
immediately eligible for the *general* adaptive routine pool used by every user, not just that
coach's own singers. There is no founder review step before it goes live. The one mechanical
safeguard: `category` must be one of the existing, already-safety-tiered categories
(`CATEGORY_INTENSITY` in `app/exercise_library.py`) rather than free text, so a custom exercise
is still governed by the exact same intensity-cap gating as every seed exercise — a coach cannot
invent a new, unreviewed intensity tier, only place their exercise into an existing one. This
does shift real trust onto individual coaches; if pilot usage ever surfaces a problem here, the
fix is a review/approval step before `is_active=True`, not a change to this section's principles.

## 14. Enforcement

- This file is reviewed at the end of every stage as part of the stage completion checklist.
- Any UI copy, AI-generated explanation, or analysis label that could be read as a diagnosis is a
  **critical bug** and blocks stage sign-off.
- Golden/example phrasings in this file may be reused verbatim; new copy should be checked
  against Sections 1–2 before shipping.
