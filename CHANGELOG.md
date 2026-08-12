# Changelog

All notable changes to VepAIr are documented here, stage by stage.

## Fixed — track selection required a saved profile first, and plan-pending copy implied only one input was needed (2026-08-12)

**Found live**, right after the onboarding redirect went in: a brand-new signup has no
`UserProfile` row yet, so `PATCH /api/v1/profile/track` 404'd with "complete onboarding first"
— forcing a user to fill out the whole profile form before they could even pick Repair or
Improvement, even though onboarding already lands them straight on the track picker.

- `app/routers/vocal_plan.py`'s `set_track` now creates a bare `UserProfile` row on first
  choice if one doesn't exist yet, the same create-on-first-write pattern `PUT /profile`
  already used — track selection works the instant a user lands on onboarding, no separate
  profile save required first.
- `TrackSelector.tsx`: removed the blocking "save the form below first" early return that
  depended on the now-obsolete 404.
- Separately, `PLAN_PENDING_REASON` said "head over to Record voice sample, **or** Vocal
  Range," misleadingly implying either alone is enough — a real plan needs both a recording
  and a vocal-range test. Reworded to say so plainly. (Confirmed via a direct query against a
  real tester's production data: recordings and a track were present, but zero `vocal_ranges`
  rows — correct by-design "pending" behavior, not a bug, just misleading copy.)
- `login/page.tsx`: a different real tester (`sjkepner@gmail.com`) reported "can't sign in" —
  turned out they simply hadn't signed up yet (confirmed via direct DB query: no account row).
  The login error message stays intentionally generic for anti-enumeration reasons and was not
  changed; instead, "Create an account" is now a prominent full-width button instead of a
  small text link, so it's harder to miss on the way in.

## Added — Supabase Storage backend for recordings (2026-08-12)

**Why now:** deploying to Cloud Run for real phone testing exposed a real gap —
`STORAGE_BACKEND=local` writes recordings to the container's local disk, which Cloud Run wipes
on every restart/redeploy. Fine for clicking through the UI, not fine for actually testing with
a real voice.

- `app/storage.py`: new `SupabaseStorage`, implementing the exact same `save`/`read`/`exists`/
  `delete` interface `LocalStorage` already had (now formalized as an `ObjectStorage` protocol)
  — a true drop-in behind `STORAGE_BACKEND=supabase`, no caller changes needed anywhere.
  Recordings are **never** made directly fetchable from Supabase: `SupabaseStorage` always
  authenticates with the service role key (bypassing RLS) and only the backend's own existing
  authenticated, ownership-checked endpoint (`GET /api/v1/recordings/{id}/audio`) re-serves the
  bytes — the exact same security model `PRIVACY.md`'s "no public-by-guessable-URL storage"
  principle already required, unchanged by this swap. New `STORAGE_BUCKET` setting (default
  `"recordings"`) names which private bucket to use.
- New `supabase` (official Python SDK) dependency.
- 14 new unit tests: `LocalStorage` (previously untested directly) and `SupabaseStorage`
  (mocked SDK client, no network calls) covering save/read/exists/delete, plus `get_storage()`
  backend dispatch including the unknown-backend error case.

## Fixed — apps/api's Docker image never actually included its own dependency (2026-08-12)

**Found deploying to Cloud Run, not by any test — Docker was never exercised before this**:
`app/baseline.py` (and others) import `vepair_audio_engine` from the sibling
`packages/audio-engine` package, but `apps/api/Dockerfile` only ever copied `apps/api` itself
into the image and never installed `packages/audio-engine` at all — a `ModuleNotFoundError` on
every startup. This was latent since Stage 0: local dev always ran directly in the shared
`.venv` (both packages installed together via `scripts/setup.ps1`), and `docker-compose.yml`'s
`build: ./apps/api` scoped the Docker build context to `apps/api` alone, so the sibling package
was never even reachable to copy in the first place.

Fixed by widening the build context to the **repo root** and moving the Dockerfile there too
(`apps/api/Dockerfile` → `Dockerfile` at the repo root) — it installs `packages/audio-engine`
first (COPY + `pip install`, ahead of the app itself, so the Docker layer cache stays useful
across ordinary app-code changes), then `apps/api`. The move to root wasn't optional: it turns
out `gcloud run deploy --source .` only auto-detects a Dockerfile-based build when it finds a
file literally named `Dockerfile` at the root of `--source` — otherwise it silently falls back
to Buildpacks, which can't make sense of a monorepo with both a Python backend and a Next.js
frontend present and fails outright. `docker-compose.yml`'s `api` service now builds with
`context: .`, `dockerfile: Dockerfile`. A new root-level `.dockerignore` keeps the wider
context's upload small. Cloud Run source deploys must now use `--source .` (repo root) instead
of `--source apps/api` to match.

## Fixed — Alembic crashed against a password containing a URL-encoded character (2026-08-12)

**Found while migrating the first real Supabase database, not by any test** — local dev's
`vepair:vepair` password has no special characters, so this was latent since Stage 0.
`migrations/env.py` passed `DATABASE_URL` straight into Alembic's `Config.set_main_option`,
which is backed by Python's `configparser` — and `configparser` treats a bare `%` as the start
of interpolation syntax (`%(name)s`), not a literal character. A Supabase pooler connection
string with a URL-encoded special character in the password (e.g. `%40` for `@`) crashed with
`ValueError: invalid interpolation syntax` before a single migration could run. Fixed by
doubling every `%` (`%%`) before storing it, which `configparser` correctly un-escapes back to
a single `%` when Alembic reads it back out — the same fix applies to any future
`DATABASE_URL` with a percent-encoded character, not just this one.

## Stage 11 — Progress Dashboard (2026-08-12)

### Added

- **New `/progress` page** consolidating the three genuine long-range gaps confirmed by a
  codebase survey before building — everything else (check-in trends, vocal plan, per-exercise
  badges) already had its own home and wasn't duplicated here:
  - **VepAIr Score history**: a real line chart of the daily score over a selectable range
    (7/30/90/180 days, 1 year, all-time). New `app/recovery_score.py` function
    `fetch_score_history` and `GET /api/v1/recovery-score/history` — strictly **read-only** over
    whatever `RecoveryScore` rows already exist; it never backfills or recomputes a day that
    wasn't already scored, since doing so would score old raw measurements against *today's*
    baseline and silently produce a different number than whatever's already shown elsewhere for
    that date. Gaps in the chart are real gaps, not something to paper over.
  - **Training consistency**: current streak, longest streak, and a day-by-day completed-session
    grid. New `app/training_consistency.py` (`compute_streaks` — pure, unit-tested for every
    streak edge case: today counts, "yesterday still counts before today is over," a gap in the
    middle, current never exceeding longest) and `GET /api/v1/training-consistency`. Streaks are
    always computed over the user's *entire* history, never clipped to the requested display
    range — a streak that started outside the visible window still reports its real length.
  - **Consolidated exercise trend list**: every exercise's current improving/declining/stable
    classification in one place (previously only ever surfaced as badges on the single
    just-completed session's screen). Needed zero backend changes — `GET /api/v1/exercise-trends`
    already computed the full list, just wasn't fully displayed anywhere.
- Reused `TrendChart` (already built for the homepage's check-in charts) unmodified for the
  0-100 VepAIr Score history — it was already fully generic on `yMin`/`yMax`/`yTicks`.

### Notes

- Scoped through a short survey-then-confirm pass rather than guessing: an Explore-agent survey
  of what progress/trend UI already existed found the three real gaps above; the founder then
  picked "new standalone page" over "fold into homepage," and selected Score history + training
  consistency + exercise trend list from the surveyed options (a vocal-range history chart was
  surveyed but not selected, so it's not part of this stage).
- "All-time" is approximated as everything since 2020-01-01 rather than the account's actual
  creation date — a deliberately simple stand-in, not a precision requirement for this feature.

## Roadmap restructuring — VepAIr Coach added, clinical/regulatory work excluded (2026-08-12)

**Founder decision, informed by a monetization strategy doc ("VepAIr Coach — The Next Step in
VepAIr Monetization"):** insert a new B2B SaaS stage — **VepAIr Coach**, a professional
dashboard for vocal coaches/teachers/studios/programs — as **Stage 12**, sequenced after Stage
11 (Progress Dashboard) and a non-numbered deployment milestone (moving to Supabase dev/prod,
setting up a GitHub deploy workflow, and Google Play readiness). The founder's own doc phases
this out (Phase I already underway through Phase V University/Enterprise); recorded in
`ROADMAP.md` now so later detailed scoping (like Stages 9/10 got) starts from that phase order
rather than re-deriving it. Computer Vision Coach and Wearables + Vocal Load moved to an
unscheduled Backlog — deprioritized, not deleted.

**Explicitly, not tentatively, out of scope: anything clinical or regulatory.** The source doc
sketched a hypothetical future "VepAIr Clinical" layer; the founder rejected it outright —
VepAIr Coach is information-purposes-only, same posture as the consumer product, never
diagnostic, never a clinical or regulated tool, now or later. This replaces the "Clinician
Portal" stage that was previously on the roadmap; `MEDICAL_SAFETY.md` section 5 (previously
framed as "designed for eventual clinician review") was rewritten to drop that framing entirely,
and `PRIVACY.md`'s "Clinician sharing consent" category was renamed to "Vocal professional
sharing consent," scoped to coaches/teachers/studios only.

## Scope removal — Song Analyzer (2026-08-12)

**Founder decision: VepAIr is a voice repair and training product, not a song-specific analysis
tool — cut, not deferred.** Removed the never-built `Song`/`SongAnalysis` models and their
(always-empty) `songs`/`song_analyses` tables (migration `65b7e96919a2`), and dropped the "Song
Analyzer" stage from `ROADMAP.md` entirely rather than renumbering it further down the list.
Every later stage shifted down by one (old Stage 13 Computer Vision Coach → 12, old 14 Wearables
→ 13, old 15 Clinician Portal → 14); `MEDICAL_SAFETY.md`/`PRIVACY.md`/`ARCHITECTURE.md` stage
references updated to match. Unrelated to this: the existing optional "sing a short phrase"
sample type in the Stage 2 guided recording flow, which stays exactly as it was.

## Stage 10 — Share My Progress (2026-08-12)

### Added

- **User-requested Beta feature — two read-only, exportable 9:16 summary images built entirely
  from real VepAIr data:** "Today's Voice" (a snapshot) and "My Progress" (a start-vs-now
  comparison). Every displayed number is either a direct read of existing stored data or a
  read-only recomputation using the app's own existing scoring functions — never a new,
  divergent calculation, and never a fabricated or estimated value. A field with nothing real
  behind it is omitted, never invented; the founder's own explicit "do not manufacture
  improvement" and "negative progress must be displayed honestly" requirements are enforced by
  construction (every delta is a plain subtraction of two real values).
- **New "Vocal Endurance" measurement** (`longest_voiced_run_seconds`): the longest unbroken run
  of voiced frames in a sustained-phonation recording, in seconds — reuses the exact frame-level
  voicing array `packages/audio-engine` already computes for `voiced_ratio`, so no new
  signal-processing algorithm was introduced, only a run-length scan over data already being
  produced. Deliberately **excluded** from `app/baseline.py`'s `VOICE_METRICS` (and therefore
  from the daily VepAIr Score) — see that module's own comment — because Share My Progress must
  never change score computation; its own historical comparison is computed directly from
  `AcousticMeasurement` history in `app/share_progress.py` instead.
- `apps/api/app/share_progress.py`: `build_today_snapshot` and `build_progress_snapshot`.
  Notably, "Pitch Stability %" reuses the recovery score's existing `acoustic_stability`
  component (jitter/shimmer/HNR/pitch-stability vs. personal baseline, already a 0-100 score) —
  for the historical "START" side of the Progress page, this is recomputed read-only against
  the *current* baseline using the same `detect_anomaly`/`score_from_anomaly_results` functions
  the daily score already uses, without ever recomputing or overwriting a past day's stored
  `RecoveryScore` row. "My Progress" prioritizes an established personal baseline as the
  comparison point, falling back to the user's first valid recorded session, and reports which
  basis was used per metric; with no comparable data at all it returns a real valid-session
  count instead of a comparison.
- New endpoints: `GET /api/v1/share-progress/today`, `GET /api/v1/share-progress/progress`
  (both `?date=` required, client-supplied — same convention as `/api/v1/recovery-score`).
  Confirmed by an explicit test that neither response ever includes email, account ID,
  location, or raw journal text.
- Frontend: `/share` page with `TodayCard`/`ProgressCard` components rendered at the real
  1080×1920 target size (previewed via a CSS-scaled wrapper, so the exported image is always
  captured at true resolution, not a scaled-down approximation). Export uses the new
  `html-to-image` dependency (`toBlob`) with `navigator.share` used when the browser supports
  file sharing, falling back to a plain download otherwise; "Save Both" exports both images
  sequentially. A "Share My Progress" button was added to the exercise-session completion
  screen (`/exercises`).

### Notes

- **Two deliberate deviations from the founder's original spec, both toward stricter accuracy:**
  (1) "Recovery Day X/90" appeared in the founder's initial informal pitch but not in the
  follow-up detailed spec's field list — omitted, matching the more authoritative, more recent
  message. (2) The comparison basis ("established baseline" vs. "first valid session") is
  reported **per metric**, not once for the whole page, since different metrics can legitimately
  have different real bases available at the same time (e.g. Vocal Endurance, which has no
  baseline-table concept at all, can never be "established," even when other metrics are).
- Manual live-browser testing could not fully verify the Save/Share image-export path pixel by
  pixel: this sandboxed environment's Browser pane does not composite frames unless actively
  displayed to a human, which stalls the canvas-decode step `html-to-image` depends on (`Image`
  `onload` never fires without active compositing). The DOM-to-SVG serialization step — the
  most failure-prone part of the library — was confirmed working (a real `data:image/svg+xml`
  request completed successfully over the network log). Real-browser verification by the
  founder is recommended before considering this fully proven, the same caveat already
  documented for `getUserMedia` in every prior stage.

## Stage 9 — Personalized Vocal Track & 90-Day Plan (2026-08-12)

### Added

- **User-requested feature — self-selected Repair/Improvement track with an auto-generated
  90-day plan:** `UserProfile.track` (`"repair" | "improvement" | null`, self-selected, never
  inferred — see `MEDICAL_SAFETY.md`) and a new `VocalPlan` table (`apps/api/app/models.py`,
  migration `cdea6917203b`). One row per plan; past plans are superseded, not deleted, so a
  user's plan history stays traceable.
- `apps/api/app/vocal_plan.py`: pure, rule-based, fully-inspectable logic (no black-box model,
  matching the recovery score and routine generator's own "show your work" pattern) —
  - `build_assessment_snapshot` reuses the most recent existing sustained-phonation recording
    (Stage 2/3) and the most recent `VocalRange` entry (Stage 8) rather than a new, separate
    "assessment" recording flow. Returns `None` — never a fabricated plan — if either is
    missing.
  - `create_plan` supersedes any current active plan and builds a new one from that snapshot;
    `build_target_milestones` sets a stability goal for Repair or a range-extension goal (from
    the user's own just-measured high note) for Improvement.
  - `assess_graduation_readiness` checks three independent criteria (14+ days of ≥70%
    non-red recovery status, personal baseline confidence at "developing"/"established", zero
    declining exercise trends) and always returns every criterion's pass/fail reason, not just
    the binding one.
  - `get_active_plan` auto-graduates a Repair plan to Improvement once every readiness
    criterion passes — "graduating" means "your recent data has been consistently stable,"
    never "you are healed."
  - `sync_plan_to_track` regenerates the plan immediately when the user manually switches
    track (a deliberate switch is a strong enough signal to restart the 90-day clock);
    `ensure_plan_exists` is the separate, more conservative path used after unrelated data
    submissions — a no-op once any active plan exists, so it can never accidentally restart
    the clock on an ordinary vocal-range or recording upload.
- New endpoints: `PATCH /api/v1/profile/track` (choose/change track; attempts immediate plan
  creation, or reports why a plan isn't ready yet) and `GET /api/v1/vocal-plan` (active plan,
  readiness for a Repair plan, and whether this request just triggered a graduation).
- `apps/api/app/exercise_routine.py`: `RoutineSignals.track` adjusts how *readily* Stage 8's
  adaptive challenge mode engages — Repair never enters it; Improvement engages it by default
  whenever the day is already uncapped (choosing that track is itself the signal); no track
  keeps Stage 8's original trend-gated behavior unchanged. Never touches `intensity_cap` or
  any hard safety rule, which apply identically regardless of track.
- `apps/api/app/vocal_range.py`: `suggest_stretch_target` gains the same `track` parameter —
  Repair always suppresses the suggestion outright; Improvement allows a bigger (+2 semitone,
  vs. the standard +1) stretch, but only when the recent range trend is genuinely improving,
  not just non-declining. Every existing safety check (discomfort, red status, declining trend)
  still applies unchanged.
- Frontend: a `TrackSelector` component on `/onboarding` ("What brings you to VepAIr?") and a
  new `/vocal-plan` page showing the active plan's goal, target date, days remaining, and (for
  a Repair plan) the transparent graduation-readiness reasons. A "Vocal plan" link was added to
  the dashboard nav.

### Fixed

- **Manually switching track through the selector silently kept the old, now-mismatched plan
  active** — found live in-browser during manual testing: selecting Improvement after an
  active Repair plan left `profile.track = "improvement"` but the plan the API returned (and
  `/vocal-plan` displayed) was still the old Repair plan. `ensure_plan_exists` was a no-op
  whenever *any* active plan existed, regardless of whether its track matched. Fixed by adding
  a separate `sync_plan_to_track`, used only by the track-set endpoint, that replaces a
  mismatched plan while still leaving `ensure_plan_exists`'s conservative no-op behavior
  unchanged for the unrelated-submission case.

### Notes

- A plan never becomes a second, competing scheduling engine — day-to-day exercise selection
  and range-stretch suggestions still run entirely through the existing Stage 6/8 adaptive
  systems; a `VocalPlan` only supplies the track those systems read, plus a long-term target
  captured once from real, already-measured data.

## Stage 8 — Vocal Range Mapping (2026-08-12)

### Added

- `apps/api/app/vocal_range.py`: Hz-to-note-name conversion, quality/duration gating, and
  historical range tracking. Three new recording sample types (`range_low`, `range_high`,
  `range_falsetto`) reuse the existing Stage 2/3 upload/analysis pipeline rather than a new one,
  deliberately excluded from Stage 4's baseline (a tested extreme isn't "normal" variation).
  `VocalRange` is a growing historical ledger (not upserted in place), so 30/90-day change can
  look back at real points in time.
- New endpoints: `POST /api/v1/vocal-range` (submit a low/high/falsetto attempt),
  `GET /api/v1/vocal-range/summary` (current range, historical best, 30/90-day change, full
  history, optional stretch-target suggestion).
- **No register-classification logic anywhere** — the brief's "do not pretend microphone
  analysis alone can definitively classify vocal registers" taken literally: only low, high, and
  falsetto notes are tracked, independently, never combined into a claimed voice "type."
- Frontend: a `/vocal-range` guided flow (low → high → optional falsetto) and a piano-style
  visualization (`PianoRange`) showing current range, historical best marker, and an optional
  stretch-target marker.
- **User-requested addition — "listen to your exercises and track improvement":**
  `apps/api/app/exercise_audio.py` analyzes exercise-attempt audio with the same Stage 3
  DSP pipeline (not a new algorithm), in-memory only — never written to storage, per
  `PRIVACY.md`'s minimal-collection principle. Only exercises with a `target_measurement` are
  analyzed. `apps/api/app/exercise_trends.py` classifies improving/declining/stable per exercise
  by comparing a recent window of real measurements against an earlier window (the same
  median-based approach as Stage 4's baseline, one level up). New
  `GET /api/v1/exercise-trends` endpoint; the exercise-session results endpoint now accepts
  multipart audio alongside the existing live-coaching telemetry.
- **User-requested addition — "challenge your voice as you get better":** `RoutineSignals.
  trending_positive` biases exercise *selection* toward more demanding (but still fully-allowed)
  exercises when a user's own trends are net-positive — reversing the category fill order and
  preferring harder difficulty within a category. This can only ever apply on a day already
  uncapped (`intensity_cap == "high"`); every existing Stage 6 safety rule (discomfort, red
  recovery status, heavy-load-plus-fatigue, rest days) still applies exactly as before and is
  regression-tested to confirm a positive trend never changes the outcome when a safety rule is
  also active.
- Vitest set up further: `apps/web/src/lib/notes.ts` (note/MIDI conversion mirroring the
  backend) with its own unit tests.

### Fixed

- **Stage 3's F0 pitch ceiling (600Hz) was too low for genuine falsetto/head voice, and the
  code comment overclaimed it "covers the full human vocal range."** A 660Hz falsetto test tone
  was tracked as its own octave-down subharmonic (330Hz) because it fell entirely outside the
  search range — found via this stage's own falsetto testing, the first thing to actually
  exercise that range. Fixed by raising `F0_CEILING_HZ` to 1000Hz in `packages/audio-engine`,
  correcting the doc comment, and adding a permanent regression test. Whistle register above
  ~1000Hz remains a documented, real limitation, not silently mishandled.
- **`/vocal-range` had no way to view existing data without starting a brand-new recording
  flow** — every visit jumped straight into "record your low note," even for a returning user
  who just wanted to check progress. Found live in-browser during manual testing. Fixed by
  fetching the summary on mount and showing it directly when data exists.

### Notes

- Exercise-attempt audio is the most privacy-conservative audio handling in the app: analyzed
  in a single request, never persisted, only the derived numbers survive. Vocal range test
  recordings, by contrast, go through the ordinary Stage 2 storage path (needed for
  `source_recording_id` and general consistency with how every other recording works).
- A larger feature was proposed after this stage's work was underway — onboarding goal
  selection ("vocal repair" vs. "vocal improvement"), auto-progression between them, and
  generated 90-day plans. Deliberately not folded into Stage 8: it's a new planning/curriculum
  layer on top of everything built so far, not a vocal-range-mapping feature, and deserves its
  own scoping conversation rather than a last-minute addition to an already-tested stage.

## Stage 7 — Live AI Vocal Coach (2026-08-11)

### Added

- `apps/web/src/lib/pitchDetector.ts`: a pure, dependency-free normalized-autocorrelation pitch
  detector for real-time use — deliberately simple (not ML-based), since live coaching only
  needs "roughly what note is this," not Stage 3's archival-precision F0. Returns `null` for
  silence/noise/low-confidence input, never a fabricated pitch.
- `apps/web/src/lib/feedbackEngine.ts`: pure, deterministic real-time coaching rules —
  comfortable-range (checked against the user's own Stage 4 baseline, never a population norm),
  gentle-onset, volume-spike, pitch-drift-near-end, and positive reinforcement for a steady
  tone. A configurable minimum interval between messages satisfies both "avoid overwhelming the
  user" and "create configurable feedback frequency" from the product brief in one setting.
- `apps/web/src/lib/liveCoach.ts`: the Web Audio integration layer, reusing Stage 2's
  `AudioRecorder` for microphone permission/setup rather than duplicating it. Analysis is 100%
  client-side — no audio ever leaves the browser for live coaching, and the recording itself is
  discarded, not stored or uploaded.
- Live coaching wired into the `/exercises` flow: exercises with a vocal signal (everything
  except Breathing) get real-time feedback with a Frequent/Normal/Minimal frequency control;
  microphone denial degrades gracefully (the exercise flow works exactly as it did in Stage 6,
  with a small notice instead of live feedback, and permission is only requested once per
  session).
- Backend: `ExerciseResult.measured_result` (already reserved by the Stage 0 schema) now
  optionally stores per-exercise live-coaching telemetry (voiced ratio, frame count, average
  analysis latency) when a coached exercise completes.
- **Vitest set up for frontend unit tests** — the framework `TESTING.md` had already named as
  the plan since Stage 1, but never actually needed until Stage 7's algorithms warranted real
  unit tests. 44 new tests covering known-frequency pitch accuracy, silence/noise handling, and
  every feedback rule (including an explicit "false feedback frequency" check: a clean, steady
  tone never produces a single corrective message).

### Fixed

- **Octave-down error in the pitch detector.** The first implementation picked the single
  highest-correlation lag across the whole search range; a pure tone correlates strongly not
  just at its true period but at every integer multiple of it, so the naive "global max" locked
  onto a subharmonic almost every time (220Hz and 440Hz test tones both read ~110Hz).
  Root-caused via the known-frequency unit tests before they were ever reported as passing.
  Fixed by walking from the shortest lag upward and taking the first strong local peak instead
  of the global max — the standard fix for this well-known autocorrelation failure mode.

### Notes

- **This environment has no real microphone hardware**, same limitation documented in Stage 2.
  What's verified: the algorithms themselves (pitch accuracy, feedback rules) against synthetic
  Web Audio signals, with real measured timing (not assumed); analysis latency benchmarked at
  ~2.4ms/frame (~2.6% of the ~93ms budget between audio chunks); and the full exercise flow live
  in-browser, including the microphone-denied graceful-degradation path (this environment's
  Browser pane blocks real `getUserMedia`, so that path is exactly what got exercised).
  **Not verified here**: live pitch-tracking against a real voice, battery impact, true
  CPU/memory profiling, or real headset/laptop/phone microphone comparison — see `TESTING.md`
  Stage 7 for the full, honest breakdown of what could and couldn't be measured.
- "Backend analysis where appropriate" (per the product brief) is Stage 3's existing
  Parselmouth/librosa pipeline on the finished recording — Stage 7 doesn't add a second backend
  analysis path, since real-time feedback has to happen client-side to feel responsive at all.

## Stage 6 — Personalized Daily Exercises (2026-08-11)

### Added

- `apps/api/app/exercise_library.py`: a 23-exercise library as plain Python data, covering all
  12 categories from the product brief (Breathing, Gentle humming, Lip trill, Tongue trill,
  Resonant voice exercises, SOVT, Straw phonation, Pitch glides, Gentle sirens, Range
  exploration, Vocal cooldown, Speaking voice recovery). No aggressive screaming/distortion
  techniques — the brief requires "a qualified methodology and appropriate safeguards" that
  don't exist yet, so none are included. `scripts/seed_exercises.py` idempotently upserts the
  library into the DB; wired into `scripts/setup.ps1`.
- `apps/api/app/exercise_routine.py`: the adaptive routine generator. Produces 5/10/15/20-minute
  routines adapted to today's recovery status, fatigue, recent vocal load, sleep, baseline
  deviation (reusing Stage 5's recovery-score components directly), and a keyword-based "user
  goal" tie-breaker — always opening with a breathing exercise and closing with a cooldown when
  the time budget allows.
- **The one rule that can never be overridden, per the brief verbatim**: reported discomfort
  (`throat_discomfort >= 7`) forces the lowest intensity tier and a fixed safety message,
  checked first and unaffected by every other signal — never a "push through it" routine.
- **Dangerous combinations are explicitly prevented**: heavy vocal load yesterday stacked with
  high fatigue caps the routine more strictly than either signal alone, matching the product
  brief's own test-plan scenario.
- Every proposed caution level is surfaced with a plain-language reason (not just the binding
  one) — the same transparency pattern as Stage 5's "why did I get this score?"
- New endpoints: `GET /api/v1/exercises` (library listing), `GET /api/v1/routine` (generate
  today's adaptive routine), `POST /api/v1/exercise-sessions` + `.../results` +
  `.../complete` + `GET` (session tracking, mirroring Stage 2's voice-session pattern).
- Frontend: a "Voice exercises" flow (`/exercises`) — pick a routine length, see a safety notice
  first when discomfort is high, walk through each exercise with instructions/contraindications/
  a countdown timer, mark done or skip, and a completion summary.
- 24 new unit tests + 15 new integration tests covering the product brief's explicit Stage 6
  test plan (188 total backend tests).

### Fixed

- **A reserved "closing cooldown" slot could get eaten by an earlier exercise during routine
  bin-packing**, so some routines silently dropped the intended cooldown even though it should
  have fit. Found during manual smoke-testing before writing the test suite. Fixed by checking
  the reserve *before* adding each middle exercise rather than breaking the fill loop early —
  see `app/exercise_routine.py`'s `try_add`.

### Notes

- "User goal" adaptation is a small, explicit keyword tie-breaker over `UserProfile.goals` free
  text (e.g. "range" → try range exercises earlier) — not NLP, and it can only reorder within
  the already safety-filtered exercise pool, never add back an excluded category.

## Stage 5 — VepAIr Daily Recovery Score (2026-08-11)

### Added

- `apps/api/app/recovery_score.py`: a transparent, explainable 0-100 daily score — "NOT a
  medical score... an individualized training/recovery indicator," per the product brief.
  Combines six components: consistency vs. personal baseline and acoustic stability (both
  reusing Stage 4's modified-z-score machinery directly), subjective fatigue, sleep, recent
  vocal load, and hydration self-report. *Vocal Range* and *Vocal Endurance* (also listed as
  possible components in the brief) are deliberately deferred — no data source exists for
  either yet — documented, not fabricated.
- New `GET /api/v1/recovery-score?date=YYYY-MM-DD` endpoint: computed fresh from current data on
  every call (fully deterministic — same underlying rows always produce the same score),
  upserted into the existing `RecoveryScore` table for a persisted history.
- **Confidence** (insufficient/low/moderate/high) is reported separately from the score itself
  — "Score 72 / Confidence: Moderate," matching the product brief's own example — rather than
  folded into the weighted average, since "how much data do we have" and "how good is today"
  are different questions.
- **GREEN / YELLOW / RED daily status**, in careful non-clinical language ("Normal training" /
  "Reduced vocal load recommended" / "Recovery-focused day"), always paired with a "not medical
  clearance" disclaimer.
- **High discomfort is a hard safety override**, not a weighted factor: `throat_discomfort >= 7`
  forces a "Recovery-focused day" status and a fixed safety-guidance message regardless of every
  other component, so a good acoustic day can never outvote it.
- **"Why did I get this score?"** — an expandable factor list on the dashboard, built directly
  from the same per-component data the score is computed from (not a separate narrative path),
  so the explanation can't drift out of sync with the number.
- Frontend: a "VepAIr Score" card at the top of the dashboard (score, status, confidence, safety
  banner when applicable, tappable explanation), updating live after a check-in is saved.
- 27 new unit tests + 7 new integration tests covering the product brief's explicit Stage 5 test
  plan (149 total backend tests).

### Fixed

- **A single bad self-report component could crater the whole score.** Discovered during manual
  testing before any automated test existed for it: the first implementation excluded missing
  components and renormalized over whatever was left, so on a day with only one component
  available, that component *was* the entire score — reporting only 3 hours of sleep alone
  produced a false "red / recovery-focused day," directly violating the brief's own requirement
  that poor sleep alone must not falsely indicate injury. Fixed by having missing components
  regress toward a neutral midpoint (50) rather than being dropped; since no component exceeds
  weight 0.20, one bad self-report answer can now move the score at most 10 points from neutral.
  See `TESTING.md` Stage 5 and `ARCHITECTURE.md` section 6e for the full writeup.

### Notes

- `GET /api/v1/recovery-score` recomputes on every call rather than being write-triggered like
  `Baseline` — a deliberate difference, since a day's score depends on two independent write
  paths (check-ins and recordings) and recomputing on read is simpler and always current.
- `MEDICAL_SAFETY.md` section 4 updated to reflect that recovery-score confidence ships as a
  plain label (matching the brief's own example), not a percentage like baseline confidence.

## Stage 4 — Personal Vocal Baseline (2026-08-11)

### Added

- `apps/api/app/baseline.py`: robust-statistics baseline engine. Uses **median and median
  absolute deviation (MAD)** instead of mean/standard deviation, specifically so a handful of
  bad recordings can't drag the baseline around the way an outlier drags a mean. Anomaly
  detection uses the modified z-score (Iglewicz & Hoaglin, `|z| > 3.5`) — a published
  robust-statistics method, not invented here.
- Anomaly detection always compares a new recording against the baseline computed from **prior**
  sessions only, then updates the stored baseline afterward — a new data point is judged before
  it gets to join the history it's judged against.
- **Confidence** (`insufficient` / `building` / `developing` / `established`, 0-100%, linear up
  to 14 usable sessions): an explicit "how much data is this based on" indicator, never
  presented as a statistical probability — see `MEDICAL_SAFETY.md`.
- `POST /api/v1/voice-sessions/{id}/recordings` now runs baseline analysis for sustained-vowel
  recordings and returns any detected anomalies once, in that upload's response
  (`RecordingOut.anomalies`) — not stored or re-served, a one-time signal.
- New `GET /api/v1/baseline` endpoint: per-metric median/MAD/confidence for all 9 voice metrics
  plus the separately-tracked fatigue baseline (from `DailyCheckIn`, its own confidence basis).
- New `Baseline` unique constraint (`user_id`, `metric_name`) + migration — one row per metric,
  updated in place, matching the "not a growing history table" design from Stage 0's schema.
- Frontend: a "Your vocal baseline" card on the dashboard (confidence, session count, per-metric
  medians, empty state for zero sessions) and anomaly callouts on the recording-session
  completion screen, both with the required non-diagnostic framing.
- 7 new integration tests covering the product brief's explicit simulated-user test plan
  (stable, slow improvement, slow decline, one-day anomaly, bad microphone data, missing days)
  plus 20 unit tests for the pure statistics functions (27 new backend tests, 104 total).

### Notes

- **Zero-MAD is a real, documented edge case, not a bug.** If every prior value is identical,
  MAD = 0 and the z-score formula is undefined; the fallback treats any deviation as maximally
  anomalous. Shows up readily with perfectly uniform synthetic test audio — see `TESTING.md`
  Stage 4 for how the test suite accounts for this.
- `GET /api/v1/baseline` returns a **materialized snapshot** (the stored `Baseline` table,
  upserted on each qualifying upload) rather than a live recomputation — it only reflects new
  data once another upload triggers a refresh.
- Baseline analysis only runs for `SUSTAINED_PHONATION_SAMPLE_TYPES`, and only when a recording
  actually produced an `AcousticMeasurement` — a too-short/unanalyzable recording can never
  corrupt the baseline, by construction rather than by a special-case check.

## Stage 3 — Acoustic Analysis Engine (2026-08-10)

### Added

- `packages/audio-engine` (`vepair-audio-engine`): a standalone Python DSP package computing
  F0 mean/median/percentile-based min-max, pitch stability, jitter, shimmer, HNR (via
  Parselmouth/Praat), RMS loudness, spectral centroid, spectral rolloff, zero-crossing rate,
  duration, and voiced ratio (via librosa/numpy) — every metric documented in the new
  `docs/acoustic-measurements.md` (definition, algorithm, library, units, valid input,
  limitations, expected variability), per the Stage 3 spec's explicit requirement.
- Jitter/shimmer/HNR are only computed for sustained phonation (`sustained_ah/ee/oo/hum`) —
  `null` for glide/sentence/singing, never a scientifically-invalid fabricated number.
- Recording upload now automatically runs acoustic analysis and stores an
  `AcousticMeasurement` row (new `pitch_stability_semitones` column + migration); best-effort —
  a too-short/unanalyzable recording just gets no measurement, never a blocked upload.
- **Recording Quality Score**: a 0-100 explainable score, extended from Stage 2's recording-technical
  checks (clipping/loudness/duration/background-noise), deliberately never factoring in voice
  measurements (jitter/shimmer/HNR/F0) — guarded by a dedicated unit test that inspects the
  scoring function's source for forbidden terms.
- **Golden Voice Set** (`data/fixtures/golden-voice-set/`, 13 synthetic WAV fixtures + generator
  script): permanent regression fixtures with documented expected behavior in
  `docs/golden-voice-set.md`, including a real documented pitch-tracking failure mode (a
  "missing fundamental" illusion from the `instrument_contamination` fixture).
- Recording session completion screen now shows each recording's quality score and (where
  applicable) F0/jitter/shimmer/HNR, with a note that these are measurements, not a diagnosis.
- 45 new tests (109 total across `apps/api` + `packages/audio-engine`): known-frequency
  accuracy (110/220/440Hz), cross-validation against an independent second pitch-tracking
  algorithm (librosa's pyin), repeatability, noise/clipping/silence/short-sample handling,
  per-sample-type validity, Golden Voice Set regression tests, and full API integration tests.

### Fixed

- **A pitch_stability test assumption was wrong, not the code.** Expected the `vibrato` fixture
  to read "more stable" than `unstable_vowel`; it measured the opposite. Investigated and
  confirmed correct: a full ±50-cent vibrato sweep has more total pitch variance (std dev
  ≈ amplitude/√2, matching theory) than `unstable_vowel`'s smaller random jitter. Not a bug —
  fixed the test's expectation and documented the real limitation (pitch_stability doesn't
  distinguish intentional vibrato from noise-like instability) in `docs/acoustic-measurements.md`.

### Incident: accidental data loss and recovery

Mid-stage, most of the repository (`.git`, `packages/`, `data/`, `docs/`, `scripts/`, `tests/`,
root docs, most of `apps/api` and `apps/web`'s source, `.venv`, `node_modules`) was deleted —
confirmed by the user to be an accidental manual deletion, not anything automated. Recovered in
full: the 7 root markdown docs were reconstructed exactly from session history (Recycle Bin
lookup missed them due to a display quirk); ~40 real source files were restored from the
Recycle Bin using original-path metadata to avoid pulling in unrelated deleted items; `.venv`
and `node_modules` were rebuilt fresh since they're fully regenerable. Verified with the full
test suite (109/109 passing) and a live browser smoke test after recovery. The database was
never affected (separate system from the filesystem).

### Notes

- No additional measurements beyond the Stage 3 spec's required list were added — formants and
  Cepstral Peak Prominence (CPP) were considered and deliberately deferred; see
  `docs/acoustic-measurements.md`'s closing section for the reasoning.
- **HNR does not reliably detect clipping** — clipping adds harmonically correlated distortion,
  which autocorrelation-based HNR doesn't penalize the way it penalizes genuine noise. Verified
  with the `clipping` Golden Voice Set fixture (HNR stays >60dB despite being badly clipped).
  This is exactly why the separate Stage 2 recording-quality clipping check exists — HNR is not
  a substitute for it.
- `AcousticMeasurement` computation happens synchronously in the upload request — fine at this
  scale, but worth revisiting (background job) if upload latency becomes noticeable.

## Stage 2 — Voice Recording Lab (2026-08-10)

### Added

- Guided 7-step voice recording flow (`/record`): sustained "Ah"/"Ee"/"Oo", comfortable hum,
  gentle pitch glide, a standardized reading sentence (opening line of the Fairbanks Rainbow
  Passage), and an optional singing sample — with pre-recording instructions (quiet room,
  consistent distance, don't touch the mic), a live timer, a live waveform, and per-step
  record/review/retake before upload.
- In-browser raw-PCM audio capture and real WAV encoding (`apps/web/src/lib/recorder.ts`) via
  the Web Audio API — not compressed webm/opus — so Stage 3's DSP work gets precise,
  uncompressed samples without a re-encode step.
- Backend: `/api/v1/voice-sessions` (create/list/get/complete) and
  `/api/v1/voice-sessions/{id}/recordings` (upload) and `/api/v1/recordings/{id}/audio`
  (playback), all ownership-scoped. Device metadata (device type, mic name, OS, app version)
  captured and reused across sessions.
- Server-side recording-quality gating (`apps/api/app/audio_quality.py`, stdlib-only):
  clipping, too-quiet, too-short, and a coarse background-noise heuristic. Every upload is
  re-validated server-side, never trusting the client-side check alone. Flags are advisory —
  a flagged recording can still be used, with a prominent Retake option.
- Local filesystem object storage (`apps/api/app/storage.py`) behind a narrow interface meant
  to make a future S3-compatible backend a drop-in swap.
- 26 new backend tests (64 total): WAV quality heuristics against synthetic audio fixtures,
  upload/playback/authorization for the full recording flow.

### Fixed

- **Background-noise heuristic false-positived on every clean sustained-vowel recording** — the
  most common recording type in this app. See `TESTING.md` Stage 2 for the full story; fixed
  with a coefficient-of-variation gate in `audio_quality.py`.
- **Recording timer froze if the browser tab lost focus/visibility mid-recording** (found via
  this environment's backgrounded test tab, which incidentally exercised a real alt-tab edge
  case). Switched from `requestAnimationFrame` to `setInterval` for the on-screen timer; actual
  audio capture was never affected since it runs on the Web Audio graph, not the render loop.
- **Timer didn't reset between recording steps**, showing the previous step's leftover elapsed
  time until a new recording started.

### Notes

- **Recording deletion is not implemented.** Deleting a user cascades the database rows but
  does not delete the underlying audio file from storage, and there's no per-recording delete
  endpoint at all yet. Flagged in `PRIVACY.md` as an open gap, not silently dropped.
- **No real microphone hardware was available to test with in this environment.** The full
  capture → encode → upload → store → playback pipeline was verified against a real,
  continuously-generated Web Audio signal (not a canned file) exercising the exact same code
  path a physical microphone would use, plus an independent Node.js re-implementation of the
  WAV encoder cross-checked against the Python parser. Bluetooth/USB-specific microphone
  behavior and genuine ambient background noise were not testable here — see `TESTING.md`.
- `ScriptProcessorNode` (used for audio capture) is deprecated but fully functional in current
  browsers. Migrating to `AudioWorkletNode` is tracked as technical debt.

## Stage 1 — User Account + Daily Vocal Journal (2026-08-09)

### Added

- Self-hosted email/password authentication (bcrypt + JWT access tokens + rotating opaque
  refresh tokens + single-use password reset tokens), deliberately designed to swap to Supabase
  Auth later with minimal change — see `ARCHITECTURE.md` section 6a.
- Backend: `/api/v1/auth/*` (signup, login, logout, refresh, password-reset request/confirm,
  me), `/api/v1/profile` (onboarding, GET/PUT), `/api/v1/checkins` (create, edit, list with
  date-range filtering, get one) — all ownership-scoped to the authenticated user.
- Frontend: signup, login, forgot-password, reset-password pages; an onboarding form (voice use,
  singer/non-singer, style, practice frequency, perceived range, goals, coaching history,
  professional care — all skippable, no medical-diagnosis fields); the real "VepAIr / Today's
  Vocal Check-In" dashboard with a skippable daily check-in form and four trend charts (voice
  quality, fatigue, throat discomfort, sleep) with a 7/30/90-day range control, hover tooltips,
  and an accessible table view per chart.
- Client-side auth session handling (`apps/web/src/lib/auth-context.tsx`) with automatic silent
  token refresh and graceful forced logout on a fully expired session.
- 33 new backend tests (38 total) covering the full auth lifecycle, authorization (cross-user
  isolation), and validation. All passing against a real Postgres instance, not mocks.
- Moved the Stage 0 system-status page to `/status`; `/` is now the real product dashboard.

### Fixed

- **Signup redirected new users to the dashboard instead of onboarding.** A race between two
  `router.replace()` calls in the signup page (see `TESTING.md` Stage 1 bugs) sent every new
  signup straight past onboarding. Fixed and re-verified live in-browser.
- **Chart tooltips could get stuck on screen** after certain hover-exit paths (notably anything
  without a reliable `pointerleave`, including touch). Fixed with redundant leave handlers plus a
  window-level pointer-position safety net in `TrendChart.tsx`.

### Notes

- Auth tokens are stored in `localStorage` rather than an httpOnly cookie for Stage 1 — a
  deliberate simplification documented in `ARCHITECTURE.md` section 6a, with the cookie-based
  upgrade flagged as a recommended change before wider rollout.
- No email provider is wired up yet; password-reset tokens are logged server-side
  (`apps/api/app/email.py`) rather than emailed. Fine for local testing, not for real users.
- "Slow connection" from the Stage 1 manual test plan was reasoned about (loading states exist)
  but not observed under actual network throttling — no throttling tool was available in this
  environment.

## Stage 0 — Foundation and Architecture (2026-08-08)

### Added

- Monorepo structure: `apps/web` (Next.js), `apps/api` (FastAPI), `packages/*`, `docs/`,
  `tests/`, `scripts/`, `data/fixtures/`.
- Top-level docs: `README.md`, `ARCHITECTURE.md`, `TESTING.md`, `ROADMAP.md`,
  `MEDICAL_SAFETY.md`, `PRIVACY.md`, `CHANGELOG.md`.
- Full Stage 0 database schema (19 tables) covering every entity in the product brief, as
  SQLAlchemy models + an Alembic migration.
- FastAPI backend with `GET /api/v1/health`, structured JSON logging, request-id middleware,
  a global exception handler, and CORS configuration.
- Next.js (App Router, TypeScript strict, Tailwind v4) frontend with a Stage 0 status page that
  live-checks API and database connectivity, plus a global error boundary.
- Local development PostgreSQL setup (`scripts/setup.ps1`, `scripts/dev-db-start.ps1`,
  `scripts/dev-db-stop.ps1`) that works without administrator rights.
- `docker-compose.yml` and per-app `Dockerfile`s for containerized deployment.
- Backend test suite (pytest): config validation, live health-check integration test, DB
  connect-timeout regression test.
- Git repository initialized.

### Fixed

- Health check hung indefinitely (well beyond a two-minute observed wait) when PostgreSQL was
  unreachable, because the SQLAlchemy engine had no connection timeout. Added
  `connect_args={"connect_timeout": 3}` in `apps/api/app/database.py` so the health endpoint now
  fails fast (~3s) and reports `"database": "unreachable"` instead of hanging. Covered by
  `apps/api/tests/unit/test_database.py`.

### Notes

- Node.js, Python, and PostgreSQL were not present on the target machine and were installed via
  `winget` as part of Stage 0 setup.
- The dev database initially ran as a user-owned PostgreSQL cluster on port 5433 to avoid
  needing admin rights. Once admin rights became available, this was retired in favor of the
  standard `postgresql-x64-17` Windows service on port 5432, with a `vepair` role/database
  created via a UAC-elevated one-time setup step (`scripts/_admin_setup_pg.ps1`, invoked
  automatically by `scripts/setup.ps1`). See `ARCHITECTURE.md` section 10.
