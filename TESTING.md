# VepAIr Testing

## 1. Test pyramid

Every stage adds to all of these as relevant:

- **Unit tests** — individual functions (`apps/api/tests/unit`, `apps/web/__tests__`,
  `tests/unit`).
- **Integration tests** — API + database + processing engine (`tests/integration`).
- **End-to-end tests** — real user workflows (`tests/e2e`).
- **DSP validation** (from Stage 3 on) — known audio in, known expected measurement out.
- **Regression tests** — previously-working audio must keep producing results within documented
  tolerance as DSP libraries change.

## 2. Golden Voice Set (from Stage 3 on)

A permanent fixture set (`data/fixtures/golden-voice-set/`) covering: stable vowel, unstable
vowel, quiet vowel, loud vowel, pitch glide, low note, high note, vibrato, breathy sample, noisy
room, clipping, silence, instrument contamination. Every release runs these; if DSP output drifts
beyond established tolerance, the build fails and requires review. Not populated until Stage 3.

## 3. Frameworks

| Layer | Framework |
|---|---|
| Backend unit/integration | `pytest` |
| Frontend unit | `vitest` / React Testing Library |
| E2E | Playwright (added when there is a real user flow to test, Stage 1+) |
| Lint | `ruff` (Python), `eslint` (TypeScript) |
| Type check | `mypy` or Pydantic-native typing (Python), `tsc --noEmit` (TypeScript) |

## 4. Stage 0 test plan

**Automated:**

- [ ] Backend unit test suite runs and passes (`pytest`)
- [ ] Backend health endpoint integration test passes
- [ ] Linting passes (`ruff`, `eslint`)

**Manual / operational:**

- [ ] Frontend launches (`npm run dev` in `apps/web`)
- [ ] Backend launches (`uvicorn` in `apps/api`)
- [ ] Database connects (Postgres reachable with configured credentials)
- [ ] Migration succeeds (`alembic upgrade head`)
- [ ] Health API responds (`GET /api/v1/health` returns 200 with DB status)
- [ ] Environment variables load correctly from `.env` (not committed)
- [ ] Frontend can call backend (health page shows live status, not a hard-coded value)
- [ ] Errors are logged correctly (structured log line with request id on a forced error)

**PASS criteria:** every checkbox above is checked, with no critical bugs open.

**Actual results:** recorded in the "VEPAIR STAGE 0 REPORT" appended to this file / delivered in
chat at the end of Stage 0, per the required report format.

---

## Stage 0 actual results

Run 2026-08-08 against a real local PostgreSQL 17 instance (no mocks).

**Automated:**

- [x] Backend unit/integration suite: **7 passed, 0 failed** (`pytest`)
- [x] Backend health endpoint integration test passes (live DB round-trip)
- [x] Linting passes: `ruff check .` (backend) clean, `eslint` (frontend) clean, `tsc --noEmit`
      clean

**Manual / operational:**

- [x] Frontend launches (`next dev`, Next.js 16.3.0 / Turbopack, ready in ~3.4s)
- [x] Backend launches (`uvicorn app.main:app`)
- [x] Database connects (PostgreSQL 17, standard Windows service, port 5432, `scram-sha-256` auth)
- [x] Migration succeeds (`alembic upgrade head` — 19 tables created; `alembic check` confirms no
      model/schema drift)
- [x] Health API responds (`GET /api/v1/health` → `{"status":"ok","database":"connected",...}`)
- [x] Environment variables load correctly from `.env` / `.env.local` (not committed)
- [x] Frontend can call backend — verified visually in-browser: status page shows live
      "Reachable" / "connected" state, and correctly flips to "Unreachable" / "Unknown" with a
      visible error message when the backend is stopped (no crash, no blank page)
- [x] Errors are logged correctly — structured JSON log line with full traceback confirmed on a
      forced DB-outage error (see `apps/api/app/logging_config.py`)
- [x] Production frontend build succeeds (`next build`); `/` correctly marked dynamic (ƒ) since
      it performs a live, uncached fetch on every request

**Bug found and fixed during testing:** the health check had no database connection timeout, so
a DB outage caused the request to hang instead of failing fast. Reproduced (request took over two
minutes with no response), fixed by adding `connect_timeout=3` to the SQLAlchemy engine, and
covered by a regression test (`tests/unit/test_database.py`). Re-verified: DB-down health check
now returns `"database": "unreachable"` in ~3 seconds.

**Result: PASS.** No user-facing critical bugs remain open. See the Stage 0 completion report
delivered alongside this update for the full write-up.

---

## 5. Stage 1 test plan

**Automated:**

- [ ] Account creation (signup)
- [ ] Login
- [ ] Logout (revokes the session)
- [ ] Password reset (request + confirm, old sessions revoked)
- [ ] Create check-in
- [ ] Edit check-in
- [ ] Retrieve history
- [ ] Authorization tests (a user can never read/write another user's data)
- [ ] Validation tests (bad email, short password, out-of-range scores, duplicate check-in date)

**Manual:**

- [ ] Create an account through the real UI
- [ ] Complete seven simulated days of check-in entries
- [ ] Confirm charts correctly update and match the underlying data exactly
- [ ] Mobile browser (375px viewport, no horizontal overflow)
- [ ] Desktop browser
- [ ] Invalid data (duplicate email, wrong password) surfaces a clear, non-crashing error
- [ ] Empty fields (every check-in/profile field skippable)
- [ ] Slow connection
- [ ] Session expiration (both the silent-refresh and fully-expired-session paths)

**PASS criteria:**

- No user can access another user's data.
- No submitted check-in is lost.
- Charts accurately represent stored values.

**Actual results:** recorded below, run 2026-08-09 against a real local PostgreSQL 17 instance
and the real running frontend/backend (no mocks).

### Automated

- [x] Signup, login, logout, refresh (with rotation), password reset (request + confirm +
      session revocation on reset): **all covered**, `apps/api/tests/integration/test_auth.py`
- [x] Create/edit check-in, retrieve history (incl. date-range filter): **all covered**,
      `apps/api/tests/integration/test_checkins.py`
- [x] Authorization: a second user gets 404 (not the first user's data) reading/editing another
      user's check-in, and an empty history list, never the other user's rows
- [x] Validation: short password, invalid email, duplicate signup email, missing check-in date,
      out-of-range scores (`voice_quality=11`), negative `sleep_hours` — all rejected with 422/409
- [x] Onboarding profile: missing-before-onboarding (404), full-replace PUT semantics, all fields
      skippable, no medical-diagnosis-shaped field names (guards MEDICAL_SAFETY.md)
- [x] **38/38 backend tests pass** (`pytest`), `ruff check .` clean, `alembic check` shows no
      schema drift
- [x] Frontend: `tsc --noEmit` clean, `eslint` clean, `next build` succeeds

### Manual (performed live in-browser, not simulated)

- [x] Created a real account through the signup UI, completed onboarding (all fields, including
      both tri-state Yes/No questions), verified the saved row in Postgres matches exactly what
      was entered
- [x] Seeded 6 additional days via the API (7 total) and created/edited today's check-in through
      the real dashboard UI
- [x] Opened "View as table" on every chart and confirmed all 7 dates/values match the seeded
      data exactly, character for character
- [x] Switched the 7/30/90-day range control — the same 7 known points reappear correctly in
      each wider window, with no data invented for the empty days
- [x] Mobile viewport (375×812): dashboard, login, onboarding all render with zero horizontal
      overflow
- [x] Invalid data: duplicate-email signup and wrong-password login both show a clear inline
      error and leave the form usable — no crash, no stuck loading state
- [x] Empty fields: submitted a check-in with every optional field left blank; all skipped
      fields stored as `null`, correctly rendered as "Skipped"/blank rather than a false zero
- [x] Session expiration, silent-refresh path: corrupted only the access token, reloaded — the
      app silently refreshed and stayed logged in
- [x] Session expiration, fully-expired path: corrupted both tokens, reloaded — cleanly logged
      out and redirected to `/login`, storage cleared, no hang, no crash
- [x] Cross-user isolation, verified in the real UI (not just backend tests): a second real
      account sees a completely empty dashboard — none of the first account's check-ins, profile
      answers, or history
- [ ] **Slow connection** — not explicitly tested (no network-throttling tool available in this
      environment). The loading states (`RequireAuth`'s "Loading...", per-section loading text)
      are already in place for this case, but the behavior is reasoned about, not observed.
      Recommend a manual pass with browser dev-tools throttling before wider rollout.

### Bugs found and fixed during Stage 1 testing

1. **Signup redirected to the wrong page.** `apps/web/src/app/signup/page.tsx` had two competing
   redirects: an effect that bounces an already-authenticated visitor to `/`, and the post-signup
   handler that sends a brand-new user to `/onboarding`. Signing up flipped auth state to
   "authenticated" *before* the explicit redirect ran, so the generic effect's `router.replace("/")`
   fired too and won the race — new users landed on the dashboard, skipping onboarding entirely.
   Fixed with a ref flag that the effect checks before redirecting; regression-verified live in
   browser (signup → `/onboarding`, confirmed by `location.pathname`).
2. **Chart tooltip could get stuck on screen.** The crosshair/tooltip in `TrendChart.tsx` only
   cleared on `onPointerLeave`, which isn't guaranteed to fire on every input path (e.g. no
   native "leave" event exists for touch at all). Reproduced: a hover that ended without a clean
   `pointerleave` left a stale date/value tooltip on screen indefinitely. Fixed by moving the hit
   area to the full `<svg>`, adding `onMouseLeave`/`onPointerUp`/`onPointerCancel` as redundant
   triggers, and adding a window-level pointermove listener that force-clears the tooltip the
   instant the pointer is outside the chart's bounding box — verified the stuck state is no
   longer reproducible after the fix.

### Result: PASS

No user-facing critical bugs remain open. Both bugs found during testing were fixed and
re-verified live, not just patched and assumed correct. See the Stage 1 completion report
delivered in chat for the full write-up.

---

## 6. Stage 2 test plan

**Test (from the product brief):**

- [ ] Microphone permission accepted
- [ ] Microphone permission denied
- [ ] No microphone present
- [ ] Clipping
- [ ] Silence
- [ ] Background noise
- [ ] Short recording
- [ ] Interrupted recording
- [ ] Mobile recording
- [ ] Desktop recording
- [ ] Bluetooth microphone
- [ ] USB microphone

**Confirm:**

- [ ] WAV/audio data remains playable after upload
- [ ] Metadata matches the recording
- [ ] Recordings belong only to the authenticated user

### A note on what this environment can and can't test

This environment's browser tooling has no fake/virtual microphone input, so genuine
hardware-microphone capture could not be exercised end-to-end here. What *was* possible, and is
arguably a stronger test of the actual recording pipeline than a quick manual mic check: feeding
`getUserMedia` a real, live-generated audio signal (a Web Audio `OscillatorNode` piped through
`createMediaStreamDestination()`) so the exact same capture code path — `AudioContext`,
`ScriptProcessorNode`, WAV encoding, upload, storage, playback — runs on genuine, continuously
flowing audio samples, just not from a physical microphone. Bluetooth/USB-specific mic behavior
and real ambient background noise were not testable here at all.

### Automated (backend)

- [x] WAV quality heuristics unit-tested against synthetic fixtures: clean tone, clipped tone,
      silence, short clip, quiet-tone-under-noise-floor, sentence-with-true-silence-pauses,
      **continuous sustained tone** (regression test for the false-positive bug below),
      sentence-with-noisy-pauses, invalid/corrupt WAV bytes — `tests/unit/test_audio_quality.py`
- [x] Voice session create (with/without device metadata), device metadata reuse across
      sessions, list, get-with-recordings, complete
- [x] Recording upload: valid WAV accepted with correct duration/sample_rate/quality_flags;
      invalid `sample_type` rejected (422); non-WAV bytes rejected (400); clipped/silent/short
      audio correctly flagged
- [x] Playback: uploaded and re-downloaded bytes are **byte-identical**
- [x] Authorization: a second user gets 404 reading another user's session, uploading into it,
      or playing back its recordings — never another user's data
- [x] **64/64 backend tests pass** (`pytest`), `ruff check .` clean, `alembic check` shows no
      schema drift
- [x] Frontend: `tsc --noEmit` clean, `eslint` clean, `next build` succeeds

### Manual (performed live — real browser, real backend, real Postgres)

- [x] Permission **denied**: mocked `getUserMedia` to reject with `NotAllowedError` — app shows
      a clear "Microphone access needed" screen with a working retry, no crash
- [x] **No microphone**: mocked rejection with `NotFoundError` — app shows a clear "No
      microphone found" screen with a working retry
- [x] Full 7-step guided sequence completed end-to-end against a **live, continuously-generated
      audio signal** (not a canned file) via a real `AudioContext`/`ScriptProcessorNode`/WAV
      pipeline: session created with device metadata captured correctly, all 6 required steps
      recorded/reviewed/uploaded, the optional 7th (singing) step's **Skip** path exercised,
      session marked complete, summary screen listed all 6 recordings as "clean"
- [x] Server-side re-verification: queried Postgres directly and confirmed the session was
      marked complete with exactly 6 recordings in the correct order and correct sample types
- [x] Downloaded a real browser-recorded WAV back through the playback endpoint and re-analyzed
      it with the (independently tested) Python WAV parser — sample rate, duration, peak
      amplitude, and all quality flags matched expectations exactly, confirming the encode →
      upload → store → retrieve round trip preserves the audio correctly
- [x] Mobile viewport (375×812): intro screen and active-recording screen (including the
      waveform canvas) both render with zero horizontal overflow
- [x] Cross-validated the in-browser WAV encoder independently of the browser: ran the exact
      same encoding algorithm under plain Node, fed the output to the Python WAV parser, and
      confirmed correct duration/sample rate/peak/RMS — two independent implementations
      agreeing is stronger evidence than either alone
- [ ] **Bluetooth microphone** — not testable in this environment (no Bluetooth audio hardware
      available to it)
- [ ] **USB microphone** — not testable in this environment (no USB audio hardware available to
      it)
- [ ] **Real ambient background noise** — the synthetic test signal has no way to simulate an
      actually noisy room; the background-noise heuristic was validated with synthetic clean and
      noisy waveforms in the unit tests instead (see bug below)

### Bug found and fixed during Stage 2 testing

1. **Background-noise heuristic false-positived on every clean sustained-vowel recording.** The
   original heuristic compared the quietest 10% of short time windows to the loudest 10%,
   flagging a recording as possibly noisy when that ratio was high. A sustained "Ah" (or any
   continuous phonation — hum, glide) has *no natural pauses at all by design*, so its windows
   are all close to the same level even when perfectly clean — the heuristic read that as "no
   dynamic range, therefore noisy" and flagged essentially every clean sustained-vowel recording,
   the single most common recording type in this app. Reproduced live (uploaded a clean synthetic
   220Hz tone through the real API, got `possible_background_noise: true`), fixed by adding a
   coefficient-of-variation gate that skips the noise check entirely when a recording has no
   meaningful loud/quiet contrast to measure in the first place, and re-verified both against the
   original synthetic tone (now correctly `false`) and against a new realistic fixture (a spoken
   sentence with genuinely noisy pauses, which still correctly flags `true`). See
   `apps/api/app/audio_quality.py` and `tests/unit/test_audio_quality.py`.

### Two minor UX bugs found and fixed during manual browser testing

2. **Recording timer froze if the tab lost visibility mid-recording.**
   The on-screen timer used `requestAnimationFrame`, which browsers fully pause in a
   backgrounded tab — the displayed timer would freeze at whatever it last showed even though
   the actual audio capture (on the Web Audio graph, unaffected by tab visibility) correctly
   kept recording. Switched to `setInterval`, which degrades to roughly once per second in the
   background instead of stopping outright. Discovered because this environment's browser tab
   reports `document.visibilityState: "hidden"`, which incidentally exercised a real edge case
   (a user alt-tabbing mid-recording) that a normal foregrounded manual test would not have
   caught. Confirmed fixed by re-running the sequence and observing the timer advance correctly.
3. **Timer didn't reset between steps.** After uploading one step's recording and advancing to
   the next, the timer displayed the *previous* step's elapsed time until the user started a new
   recording, rather than resetting to 0.0s. Fixed by resetting the timer state alongside the
   step-index advance.

### Result: PASS

No user-facing critical bugs remain open. Three bugs found during testing (one measurement
correctness bug, two timer UX bugs) were fixed and re-verified live against a real recording
pipeline, not just patched and assumed correct. Recording deletion and cloud storage remain
unimplemented — tracked in `ARCHITECTURE.md` §6b and `PRIVACY.md` §6 as recommended changes
before Stage 3, not silently dropped. See the Stage 2 completion report delivered in chat for the
full write-up.

---

## 7. Stage 3 test plan

**From the product brief:**

- [ ] Unit-test each metric
- [ ] Test against known synthetic frequencies: 110Hz, 220Hz, 440Hz
- [ ] Test measurement repeatability
- [ ] Test noise contamination
- [ ] Test clipping
- [ ] Test silence
- [ ] Test very short samples
- [ ] Compare applicable results against Praat/Parselmouth reference calculations
- [ ] Document tolerances

**PASS criteria:** core calculations must demonstrate known and reproducible behavior.

**Actual results:** recorded below, run 2026-08-10 against the real running backend, real
Postgres, and `packages/audio-engine`'s real Parselmouth/librosa pipeline (no mocks).

### Automated

- [x] 110/220/440Hz pure tones: F0 mean/median/percentile-min/max all read within 0.5Hz of the
      true frequency (measured accuracy in practice: within ~0.001Hz) —
      `test_known_frequency_detected_within_tolerance`
- [x] Clean tones at all three frequencies: jitter < 0.01%, shimmer < 0.01%, HNR > 60dB
- [x] **Cross-validated against an independent second algorithm**: librosa's `pyin` pitch
      tracker agrees with Parselmouth/Praat's F0 estimate to within 1% on the same signal —
      two independently-implemented pitch trackers agreeing is stronger evidence of correctness
      than either algorithm's internal self-consistency alone (the spec's "compare against
      Praat/Parselmouth reference" requirement, applied as a genuine cross-check since
      Parselmouth *is* VepAIr's Praat integration)
- [x] Repeatability: identical input produces byte-for-byte-identical measurement output
- [x] Noise contamination: added noise measurably lowers HNR and raises jitter vs. the same
      clean signal
- [x] Clipping: doesn't crash, F0 still tracks correctly; **documented finding** — HNR does not
      reliably drop from clipping alone (clipping is harmonic distortion, not noise-like), which
      is exactly why the separate Stage 2 clipping check exists
- [x] Silence: every voice measurement returns `null` (never a fabricated zero); RMS/spectral
      fields correctly read as genuinely zero/silent
- [x] Very short samples (<0.3s): raises `InsufficientAudioError`, caught by the API layer so
      the recording still uploads successfully with `measurement: null`
- [x] Per-sample-type validity: jitter/shimmer/HNR present for sustained_ah/ee/oo/hum, `null`
      for glide/sentence/singing — verified both at the `packages/audio-engine` unit level and
      through the real upload API
- [x] Golden Voice Set regression suite (13 fixtures): stable/unstable/quiet/loud vowel, pitch
      glide, low/high note, vibrato, breathy, noisy room, clipping, silence, instrument
      contamination — each fixture's behavior asserted and documented in
      `docs/golden-voice-set.md`
- [x] Recording Quality Score: clean recording scores 100/"excellent"; each issue
      (clipping/quiet/short/noise) costs its documented, correct point value; multiple issues
      stack and floor at 0; a dedicated test guards that the score never depends on voice
      measurements (jitter/shimmer/HNR/F0), inspecting the scoring function's own source code
- [x] Full upload → analyze → store → retrieve API integration tests, including authorization
      (a second user can never see another user's measurements)
- [x] **109/109 tests pass** (`apps/api`: 77, `packages/audio-engine`: 32), `ruff check .` clean
      in both packages, `alembic check` shows no schema drift

### Manual (live, real backend + real Postgres, browser-driven)

- [x] Full 7-step guided recording session run against a live, continuously-generated Web Audio
      signal (same code path a real microphone uses): all 6 required recordings scored
      "excellent (100)"; sustained types (Ah/Ee/Oo/hum) correctly showed F0/Jitter/Shimmer/HNR;
      glide and sentence correctly showed F0 only, no jitter/shimmer/HNR — confirming the
      per-sample-type withholding logic works end-to-end, not just in unit tests
- [x] Verified directly in Postgres that measurements persisted correctly and match what the
      API returned
- [x] Confirmed the medical-safety disclaimer ("measurements, not a diagnosis") renders on the
      completion screen alongside the numbers

### Documented findings (not bugs — correct, worth recording)

1. **`instrument_contamination` fixture demonstrates a real pitch-tracking failure mode.**
   220Hz + 330Hz (both multiples of 110Hz) gets tracked as F0≈110Hz — the "missing
   fundamental" both tones are harmonics of, not either real tone. See
   `docs/golden-voice-set.md`.
2. **`vibrato` reads higher pitch_stability than `unstable_vowel`.** Counterintuitive at first,
   confirmed correct: a full ±50-cent vibrato sweep has more total pitch variance than
   `unstable_vowel`'s smaller random per-cycle jitter (std dev ≈ amplitude/√2 ≈ 0.35 semitones,
   matching the theoretical prediction exactly). The metric doesn't distinguish intentional
   musical vibrato from noise-like instability — documented in `docs/acoustic-measurements.md`.
3. **HNR does not reliably detect clipping.** Clipping adds harmonically-correlated distortion,
   not noise — autocorrelation-based HNR stays high (>60dB in the `clipping` fixture) despite
   severe clipping. This is why recording-quality clipping detection (Stage 2) is a genuinely
   separate, necessary check, not redundant with any voice measurement.

### Result: PASS

Core calculations demonstrate known and reproducible behavior, cross-validated against an
independent second algorithm, and verified end-to-end live (not just in unit tests). No
user-facing critical bugs found. One test-expectation error was caught, investigated, and
corrected (see `CHANGELOG.md`) rather than silently "fixed" by changing the underlying code to
match a wrong assumption. See the Stage 3 completion report delivered in chat for the full
write-up, including an incident report on mid-stage accidental data loss and full recovery.

## 8. Stage 4 test plan

**From the product brief — simulated users:**

- [ ] Stable measurements
- [ ] Slow improvement
- [ ] Slow decline
- [ ] One-day anomaly
- [ ] Bad microphone data
- [ ] Missing days

**Confirm:**

- [ ] Bad recordings do not corrupt baseline
- [ ] Single anomalies do not permanently shift baseline
- [ ] Progressive changes are detectable
- [ ] Baseline confidence increases appropriately

**PASS criteria:** every simulated-user scenario behaves as specified above, verified against
the real upload → baseline endpoints (not just the pure statistics functions in isolation).

**Actual results:** recorded below, run 2026-08-10/11 against the real running backend, real
Postgres, and `app/baseline.py`'s real robust-statistics pipeline (no mocks).

### Automated

- [x] **Stable measurements**: 8 uploads clustered around 220Hz produce no anomalies and a
      baseline median within 1Hz of the true value —
      `test_stable_user_no_anomalies_and_confidence_increases`
- [x] **Confidence increases appropriately**: confidence percentage is monotonically
      non-decreasing as usable sessions accumulate (6 sequential uploads, each checked against
      the last) — `test_confidence_increases_monotonically_as_sessions_accumulate`; confidence
      labels verified at every threshold boundary (0→insufficient, 3→building, 7→developing,
      14→established) in the unit suite
- [x] **Slow improvement / slow decline are not flagged as anomalies**: 12 uploads drifting
      +0.8Hz or -0.8Hz per step (a ~9Hz total move) never trip the pitch anomaly detector —
      `test_slow_improvement_is_not_flagged_as_anomaly`,
      `test_slow_decline_is_not_flagged_as_anomaly`. (Pure synthetic sine tones have near-zero
      jitter/shimmer noise, which can trip the documented zero-MAD fallback on meaningless
      floating-point differences — these tests deliberately scope their assertion to the pitch
      metrics being varied, not the full anomaly list; see
      `test_zero_mad_baseline_flags_any_deviation` for that documented edge case.)
- [x] **One-day anomaly is flagged but does not permanently shift the baseline**: after 8 stable
      220Hz sessions, a single 320Hz upload correctly flags `f0_mean_hz` (and related pitch
      metrics) as anomalous; the baseline median moves by less than 5Hz from that one point; the
      very next normal 220Hz upload is *not* flagged, and the baseline settles back within 2Hz
      of 220 — `test_one_day_anomaly_does_not_permanently_shift_baseline`
- [x] **Bad microphone data does not corrupt the baseline**: a too-short (0.1s) recording
      uploads successfully (per Stage 2/3 behavior) but produces no `AcousticMeasurement` row and
      no anomaly; the baseline's usable session count and every metric are byte-identical before
      and after — `test_bad_microphone_data_does_not_corrupt_baseline`
- [x] **Missing days between sessions still accumulate into the baseline**: 6 sessions backdated
      to span roughly two months of once-a-week recording (not consecutive days) still all count
      as usable sessions once the next upload refreshes the stored snapshot, with
      `window_start < window_end` correctly spanning the gap —
      `test_missing_days_between_sessions_still_accumulate_into_baseline`
- [x] Pure-function unit tests (20, `tests/unit/test_baseline.py`): median resists a single wild
      outlier while mean would shift >20 units on the same data; MAD-based confidence label
      thresholds; insufficient-sample case returns `None` (genuinely "can't tell yet"), never a
      false `False`; zero-MAD edge case
- [x] **104/104 backend tests pass** (`apps/api`), `ruff check .` clean, `tsc --noEmit` clean,
      `eslint` clean (frontend)

### Manual (live, real backend + real Postgres, browser-driven)

- [x] Signed up a fresh test account, uploaded 6 stable ~220Hz sustained-vowel recordings via
      direct HTTP calls exercising the exact same upload endpoint the browser uses, confirmed
      `GET /api/v1/baseline` returns `usable_session_count: 6`, `voice_confidence: 42.9%
      (building)`, and `f0_mean_hz` baseline median ≈220Hz
- [x] Uploaded one 320Hz outlier: response correctly listed `f0_mean_hz`/`f0_min_hz`/
      `f0_max_hz`/`pitch_stability_semitones` anomalies with non-diagnostic messages (e.g. "Your
      average pitch is noticeably different from your recent baseline"); baseline median after
      the anomaly stayed at 220.30 (sample_count 7) — not dragged toward 320
- [x] Logged into the dashboard in-browser (fresh tab, cleared storage) as that same test
      account: "Your vocal baseline" card correctly rendered "Developing (50%)", "7 usable
      sessions", and per-metric medians (average pitch 220Hz, HNR 90.7dB, etc.), with the
      required non-diagnostic disclaimer
- [x] Signed up a second, brand-new account with zero recordings: dashboard correctly rendered
      the empty-baseline state ("Record a few sustained-vowel samples to start building your
      personal vocal baseline...") instead of crashing or showing blank/undefined data
- [x] No console errors on either dashboard state beyond an expected, pre-existing 404 on
      `/api/v1/profile` for accounts that skipped onboarding

### Documented findings (not bugs — correct, worth recording)

1. **Zero-MAD baseline flags any deviation.** Perfectly uniform synthetic test data (e.g. every
   jitter/shimmer reading numerically identical) makes MAD = 0, so the modified z-score formula
   is undefined; the documented fallback treats *any* different value as maximally anomalous.
   Confirmed correct and intentional — this is why the improvement/decline tests scope their
   anomaly assertion to the metric actually being varied rather than asserting an empty anomaly
   list outright.
2. **`GET /api/v1/baseline` serves a materialized snapshot, not a live recomputation.** The
   stored `Baseline` row only updates on the next qualifying upload — backdating existing
   recordings' timestamps (as the missing-days test does) doesn't retroactively change the
   already-stored snapshot until a new upload triggers a refresh. This matches the deliberate
   "one row per (user, metric), updated in place" design in `models.py`, not a bug, but worth
   knowing before assuming baseline data is always current relative to the underlying rows.

### Result: PASS

All six simulated-user scenarios from the product brief behave as specified, confirmed against
the real upload and baseline endpoints (not mocks), plus live in-browser verification of both
the populated and empty dashboard states. No user-facing critical bugs found.

## 9. Stage 5 test plan

**From the product brief:**

- [ ] Create controlled test users
- [ ] Good data raises appropriate components
- [ ] Poor sleep alone doesn't falsely indicate vocal injury
- [ ] Bad microphone recordings don't tank recovery score
- [ ] High discomfort triggers appropriate safety guidance
- [ ] Score explanation mathematically matches score
- [ ] Same input always produces same score

**PASS criteria:** every scenario above behaves as specified, verified against the real
check-in/upload/recovery-score endpoints (not just the pure aggregation function in isolation).

**Actual results:** recorded below, run 2026-08-11 against the real running backend, real
Postgres, and `app/recovery_score.py`'s real scoring pipeline (no mocks).

### Automated

- [x] **Good data raises appropriate components**: a user with 6 stable ~220Hz recordings (a
      real baseline) and a fully-filled, good check-in scores ≥80, status green, all six
      components included with score ≥75, and every surfaced factor positive —
      `test_good_data_raises_appropriate_components`
- [x] **Poor sleep alone doesn't falsely indicate vocal injury**: a check-in reporting only
      `sleep_hours: 2.0` (everything else skipped, no recordings at all) never produces a "red"
      status — `test_poor_sleep_alone_does_not_falsely_indicate_injury`
- [x] **Bad microphone recordings don't tank recovery score**: a too-short (0.1s) recording that
      produces no `AcousticMeasurement` yields a score byte-identical to an independent second
      user with the same check-in and *no recording at all*, and both acoustic components stay
      explicitly excluded (`included: false`), never scored low —
      `test_bad_microphone_recording_does_not_tank_score`
- [x] **High discomfort triggers appropriate safety guidance**: `throat_discomfort: 9` forces
      `status: "red"` and a non-empty safety message recommending professional consultation,
      even with a full baseline and an otherwise-perfect check-in —
      `test_high_discomfort_triggers_safety_guidance`
- [x] **Score explanation mathematically matches score**: the weighted total recomputed purely
      from the API response's own `components` (`score`/`weight`/`included`, with excluded
      components substituted at the documented neutral value) reproduces `score_value` exactly —
      `test_score_explanation_mathematically_matches_score`
- [x] **Same input always produces same score**: two consecutive `GET` calls with no data change
      in between return byte-identical responses — `test_same_input_always_produces_same_score`
- [x] No-data day returns `score_value: null` / `confidence_label: "insufficient"` /
      `status: "unknown"` — a genuine "can't tell yet," never a fabricated number
      (`test_no_data_returns_null_score_not_a_fabricated_number`), matching the same principle
      established in Stage 4's `detect_anomaly`/`compute_baseline_stats`
- [x] 27 pure-function unit tests (`tests/unit/test_recovery_score.py`): every component scoring
      function's boundaries (fatigue 1↔100/10↔0, sleep peak at 8h, load none↔100/high↔20 with
      the more-demanding-of-two-loads rule, hydration mapping), confidence-label thresholds,
      status thresholds, the discomfort override at exactly the threshold and just below it,
      and determinism
- [x] **149/149 backend tests pass** (`apps/api`), `ruff check .` clean, `tsc --noEmit` clean,
      `eslint` clean (frontend)

### Manual (live, real backend + real Postgres, browser-driven)

- [x] Logged into the dashboard as an existing test account with a real baseline but no
      check-in yet for today: "VepAIr Score" card showed 64, "Reduced vocal load recommended,"
      "Based on limited data today" — correctly reflecting partial (acoustic-only) data
- [x] Expanded "Why did I get this score?" — showed exactly the two acoustic-derived positive
      factors, nothing fabricated for the missing self-report components
- [x] Filled out and saved today's check-in (low fatigue, 8h sleep, low load, high hydration)
      through the real form: the score card updated **live, without a page reload**, from 64 to
      89, status changed to "Normal training," confidence changed to "Based on a full picture of
      today's data," and all six factors flipped to positive
- [x] Edited the same check-in to set `throat_discomfort: 9`: the card immediately updated to
      "Recovery-focused day" with the safety-guidance banner visible, despite every other
      component still being scored well — confirming the override is visually correct, not just
      correct in the API response
- [x] No new console errors beyond the same pre-existing, expected 401/404 noise already
      documented in Stage 4 testing (token-bootstrap 401s, `/api/v1/profile` 404 for an account
      that skipped onboarding)

### Bug found and fixed during development

1. **A single bad self-report component could crater the whole score.** The first
   implementation excluded missing components and renormalized the weighted average over
   whatever was left — so on a day with only one component available (e.g. just a bad
   `sleep_hours` value), that one component *was* the entire score: reporting 3 hours of sleep
   alone produced a score of 17 and a false "red / recovery-focused day," directly violating the
   product brief's own test requirement. Root-caused during manual pure-function testing before
   any test was even written against it. Fixed by having missing components regress toward a
   neutral midpoint (50) instead of being dropped — see `app/recovery_score.py` and
   `ARCHITECTURE.md` section 6e for the full reasoning. Re-verified: the same poor-sleep-only
   input now produces 45 ("Reduced vocal load recommended"), not 17 ("Recovery-focused day").
   Regression-tested at both the unit level (`test_poor_sleep_alone_does_not_falsely_indicate_injury`
   in `tests/unit/test_recovery_score.py`) and the integration level (same-named test in
   `tests/integration/test_recovery_score.py`).

### Result: PASS

All seven scenarios from the product brief's Stage 5 test plan behave as specified, confirmed
against the real check-in/upload/recovery-score endpoints (not mocks), plus live in-browser
verification including a real-time score update after saving a check-in and a visually-verified
safety override. One real bug was found, root-caused, fixed, and regression-tested before this
report was written — not discovered afterward. No user-facing critical bugs remain open.

## 10. Stage 6 test plan

**From the product brief:**

- [ ] Test recommendation engine with: healthy baseline, fatigued user, range reduction, high
      discomfort, poor sleep, heavy rehearsal yesterday, several rest days
- [ ] Verify dangerous combinations are prevented

**PASS criteria:** every scenario above produces the specified routine behavior, verified
against the real check-in/routine/exercise-session endpoints (not just the pure routine
generator in isolation), and no scenario ever recommends "pushing through" reported pain.

**Actual results:** recorded below, run 2026-08-11 against the real running backend, real
Postgres, and `app/exercise_routine.py`'s real rule engine (no mocks).

### Automated

- [x] **Healthy baseline**: a good check-in with no other risk signals gets the full-intensity
      routine, no safety message — `test_healthy_baseline_gets_full_intensity_routine`
- [x] **Fatigued user**: `fatigue: 9` alone caps the routine at low/moderate, excluding every
      high-intensity exercise — `test_fatigued_user_gets_moderate_routine`
- [x] **Range reduction**: 6 stable baseline recordings followed by a 320Hz outlier (Stage 4's
      anomaly detection firing, read through Stage 5's recovery-score components) keeps Range
      exploration and Pitch glides out of the routine —
      `test_range_reduction_baseline_deviation_avoids_high_intensity`
- [x] **High discomfort**: `throat_discomfort: 9` forces the low-intensity cap, a non-null
      safety message, and every single selected exercise verified to be low-intensity — never a
      "push through it" routine —
      `test_high_discomfort_triggers_safety_guidance_never_push_through`
- [x] **Poor sleep**: `sleep_hours: 2.5` alone keeps the routine below full intensity —
      `test_poor_sleep_avoids_high_intensity`
- [x] **Heavy rehearsal yesterday (dangerous combination)**: heavy singing load yesterday
      stacked with high fatigue caps at low — stricter than either signal alone would produce —
      `test_heavy_rehearsal_yesterday_dangerous_combination_prevented`, confirmed at the unit
      level too (`test_heavy_rehearsal_plus_high_fatigue_caps_at_low` vs.
      `test_rehearsal_alone_without_fatigue_does_not_cap` in `tests/unit/test_exercise_routine.py`)
- [x] **Several rest days**: backdating the last completed exercise session by 9 days eases the
      next routine back to moderate even though every other signal looks fine —
      `test_several_rest_days_eases_back_in`
- [x] **Dangerous combinations prevented, more generally**: a red recovery status alone (from
      any cause) never yields a single high-intensity exercise
      (`test_red_status_never_yields_a_high_intensity_exercise`), and a "user goal" keyword
      never overrides an active safety cap even when it would otherwise prioritize exactly the
      excluded category (`test_goal_never_overrides_a_safety_cap`)
- [x] Full exercise-session lifecycle (start → log a result per exercise → complete → fetch with
      results) works end-to-end, and a session belonging to another user correctly 404s —
      `test_full_session_lifecycle`, `test_user_cannot_log_results_on_another_users_session`
- [x] All 4 routine lengths (5/10/15/20 min) produce a non-empty routine that never exceeds its
      time budget — `test_all_valid_routine_lengths_work` (integration),
      `test_all_valid_lengths_produce_a_nonempty_routine` (unit)
- [x] 24 pure-function unit tests (`tests/unit/test_exercise_routine.py`): every intensity-cap
      rule's threshold and the "no cap" case, opening-with-breathing/closing-with-cooldown
      structure at all four lengths, no exercise ever repeated in one routine
- [x] **188/188 backend tests pass** (`apps/api`), `ruff check .` clean, `tsc --noEmit` clean,
      `eslint` clean (frontend)

### Manual (live, real backend + real Postgres, browser-driven)

- [x] Picked a 10-minute routine on a healthy-baseline test account: got an 8-exercise "Full
      routine" starting with Diaphragmatic breathing and ending with Vocal cooldown hum, a live
      countdown timer per exercise, and correctly logged each "Mark done" through to a session
      summary showing 8 of 8 completed
- [x] Set `throat_discomfort: 9` on the same account's check-in, then started a new routine:
      the app correctly showed a "Before you start" safety screen with the exact escalation
      message before any exercise, and the resulting routine was labeled "Gentle routine" with
      only low-intensity exercises
- [x] No new console errors beyond the same pre-existing, expected 401/404 noise already
      documented in Stage 4/5 testing

### Result: PASS

Every scenario from the product brief's Stage 6 test plan behaves as specified, confirmed
against the real check-in/routine/exercise-session endpoints (not mocks), plus live in-browser
verification of both the full-intensity and safety-gated routine paths. No user-facing critical
bugs found.

## 11. Stage 7 test plan

**From the product brief — measure:**

- [ ] Analysis latency
- [ ] Feedback latency
- [ ] CPU load
- [ ] Memory use
- [ ] Battery impact if possible
- [ ] Pitch accuracy
- [ ] False feedback frequency

**From the product brief — test:**

- [ ] Quiet room
- [ ] Moderate background noise
- [ ] Headset microphone
- [ ] Laptop microphone
- [ ] Phone microphone

**Environment honesty note, up front (same principle as Stage 2's "no real microphone hardware
was available" disclosure):** this environment has no physical microphone, cannot measure
battery impact, and cannot compare real headset/laptop/phone hardware. What follows is measured
where it genuinely could be (algorithm timing and accuracy, via synthetic Web Audio signals —
the same substitution Stage 2 used to validate the capture pipeline), and explicitly marked
"not measurable here" where it couldn't be, rather than a fabricated number either way.

**PASS criteria:** analysis/feedback latency low enough to feel real-time; pitch accuracy
verified against known frequencies; false-corrective-feedback rate on clean signal is zero;
every measurable item reported honestly, with unmeasurable items explicitly disclosed rather
than guessed.

**Actual results:** recorded below, run 2026-08-11. Frontend unit tests via `vitest`
(`apps/web`, first real use of the framework already named in section 3's table); backend via
`pytest` (`apps/api`, unchanged from Stage 6 plus the new `measured_result` field).

### Automated

- [x] **Pitch accuracy**: 110/220/440Hz pure synthetic tones detected within 1% of true
      frequency; silence and pure white noise correctly return `null` (never a fabricated
      pitch); a tone mixed with simulated moderate background noise (a realistic
      signal-to-noise ratio, since no real noisy room was available) still detected within 2% —
      `pitchDetector.test.ts`
- [x] **Analysis latency, measured**: a one-time benchmark (500 calls to `detectPitch` on a
      warmed-up 4096-sample/44.1kHz buffer, the same size `AudioRecorder`'s `ScriptProcessorNode`
      delivers) averaged **~2.4ms per call** — about 2.6% of the ~93ms of wall-clock time
      available before the next audio chunk arrives at that buffer size. This is the dominant
      cost in the real-time loop (feedback-rule evaluation on top of it is negligible,
      synchronous arithmetic over a small rolling window), so it stands in for both "analysis
      latency" and "feedback latency" from the test plan — there is no meaningful additional
      delay between a frame being analyzed and a feedback decision being made.
- [x] **CPU load / memory use — partial, honestly labeled.** The ~2.6%-of-budget timing above is
      a defensible *proxy* for CPU headroom (plenty of margin at a ~90ms cadence), but this
      environment has no OS-level CPU/memory profiler, so no true CPU-percentage or
      memory-footprint number is reported. Not fabricated — left explicitly unmeasured.
- [x] **Battery impact**: not measurable in this environment. Explicitly not reported rather
      than guessed.
- [x] **False feedback frequency**: a gently-onset, steady synthetic tone run through the full
      feedback engine for 4 seconds never produces a single corrective message — 0% false
      corrective-feedback rate across every clean-signal test case
      (`feedbackEngine.test.ts` — "clean signal" describe block, 4 tests). Rule-by-rule,
      each corrective rule is confirmed to fire on a deliberately bad synthetic signal AND to
      stay silent on a clean one: onset (harsh vs. gradual), volume spike (established baseline
      vs. sudden jump), pitch drift (>0.7 semitone rise vs. a small in-tolerance wobble), and
      comfortable range (only when a personal baseline exists — never fires on a fabricated
      target).
- [x] **Configurable feedback frequency / "avoid overwhelming the user"**: two feedback-worthy
      events closer together than the configured minimum interval produce only one message; a
      shorter configured interval measurably allows feedback to repeat sooner than a longer one
      — `feedbackEngine.test.ts`, "feedback frequency / cooldown" describe block
- [x] **Quiet room vs. moderate background noise**: quiet room = the standard clean-tone tests;
      moderate background noise = a tone mixed with white noise at a realistic SNR (see pitch
      accuracy above) — both pass. **Headset/laptop/phone microphone comparison: not testable**
      without real hardware, consistent with Stage 2's documented limitation.
- [x] A real octave-down bug in the pitch detector's peak-picking was found, root-caused, and
      fixed before any of the above tests were finalized — see "Bug found and fixed" below.
- [x] Backend: `measured_result` (voiced ratio, frame count, average analysis latency) round-trips
      correctly through `POST /api/v1/exercise-sessions/{id}/results` both with and without
      telemetry present (omitted entirely for Breathing exercises or a denied microphone).
- [x] **188 backend tests + 44 new frontend unit tests, all passing.** `ruff check .` clean,
      `tsc --noEmit` clean, `eslint` clean.

### Manual (live, real backend + real Postgres, browser-driven)

- [x] Walked a full 4-exercise routine live in-browser end to end (Breathing → SOVT → SOVT
      glide → cooldown). This environment's Browser pane blocks real `getUserMedia` access —
      confirmed live: the app correctly caught the permission failure, showed "Live coaching
      unavailable (microphone access denied) — continue at your own pace" without blocking the
      exercise, requested the microphone only once per session (not re-prompted on later
      exercises after the first denial), and the routine completed normally (4 of 4 logged) with
      no console errors beyond the same pre-existing 401/404 noise from earlier stages.
      **This confirms the graceful-degradation path works correctly; it does not, and cannot in
      this environment, confirm the live pitch-tracking/feedback-rendering path against a real
      microphone** — that gap is covered instead by the pitchDetector/feedbackEngine unit tests
      above, run against synthetic audio.
- [x] The feedback-frequency selector (Frequent/Normal/Minimal) renders and is selectable on the
      routine-setup screen before starting.

### Bug found and fixed during development

1. **Octave-down error in the pitch detector.** The first implementation picked the single
   highest-correlation lag across the whole search range. A pure tone correlates strongly not
   just at its true period but at every integer multiple of it too, so the naive "global max"
   consistently locked onto a subharmonic — a 220Hz and a 440Hz test tone both incorrectly
   reported ~110Hz. Root-caused immediately via the known-frequency unit tests (before they were
   ever reported as passing) and fixed by walking from the shortest lag upward and taking the
   first strong local peak instead of the global max — the standard fix for this exact,
   well-known failure mode in autocorrelation pitch trackers. Re-verified: 110/220/440Hz all now
   detected within 1%.

### Result: PASS

Every measurable item from the Stage 7 test plan was measured and reported honestly (pitch
accuracy, analysis/feedback latency, false-feedback frequency, feedback-frequency
configurability, quiet-room and simulated-background-noise robustness); every item this
environment genuinely cannot measure (battery impact, true CPU/memory profiling, real
headset/laptop/phone hardware comparison) is explicitly disclosed as unmeasured rather than
fabricated. One real bug was found, root-caused, and fixed before being reported as working —
not discovered afterward. No user-facing critical bugs found.

## 12. Stage 8 test plan

**From the product brief:**

- [ ] Validate MIDI/note conversion
- [ ] Validate semitone calculations
- [ ] Reject accidental octave errors
- [ ] Test male/female/high/low voice ranges
- [ ] Test falsetto
- [ ] Test background instruments contaminating recording

**From the user's explicit Stage 8 additions:**

- [ ] Exercises are "listened to" and analyzed (Stage 3's real DSP, not a new algorithm)
- [ ] Trends (improving/declining/stable) are tracked per exercise over repeated attempts
- [ ] The system "challenges" the user's voice as they improve, always subordinate to Stage 6's
      existing safety caps — never overrides discomfort, red recovery status, or rest-day rules

**PASS criteria:** every scenario above behaves as specified, verified against the real
recordings-upload/vocal-range/exercise-result/exercise-trends/routine endpoints (not just pure
functions in isolation), and the register-classification prohibition is verified by its literal
absence from every response, not just by omission from the UI.

**Actual results:** recorded below, run 2026-08-11/12 against the real running backend, real
Postgres, and the real Parselmouth/librosa pipeline (no mocks).

### Automated

- [x] **MIDI/note conversion validated** against known references (A4=440Hz, G4=392Hz,
      C4=261.63Hz/middle C, A3=220Hz, A5=880Hz, C5=523.25Hz) and octave boundaries (B3→C4) —
      `tests/unit/test_vocal_range.py`
- [x] **Semitone calculations validated**: an octave is exactly 12 semitones in both directions,
      zero for the same note, round-trips through MIDI correctly
- [x] **Octave errors rejected** — but this exposed a real one first, see "Bug found and fixed"
      below. After the fix, both known-frequency and falsetto-range tones convert correctly and
      the fix is locked in by a permanent regression test in `packages/audio-engine`
- [x] **Male/female/high/low voice ranges and falsetto tested**, simulated via synthetic tones
      across typical published F0 bands (male chest ~85-180Hz, female chest ~165-255Hz,
      falsetto ~550-660Hz) through the real upload → analyze → convert → store pipeline —
      `tests/integration/test_vocal_range.py`
- [x] **Background instrument contamination tested**: a second, unrelated tone mixed into the
      recording never crashes the pipeline (upload and range-submission both still succeed);
      documented as a robustness check, not a pitch-tracking-correctness claim, given Stage 3's
      already-documented "missing fundamental" limitation
- [x] **Quality/duration gating**: a recording under the 1.0s minimum duration correctly
      contributes no note at all — "only count notes meeting quality and duration criteria,"
      the product brief's own words
- [x] **No register-classification field anywhere in the API response** — verified directly by
      asserting the response JSON's keys are disjoint from a forbidden set
      (`register`/`chest_voice`/`mix_voice`/`head_voice`/`voice_type`/`fach`)
- [x] **Historical best and 30/90-day change** computed correctly against backdated history
      (100/40/1 days ago), confirmed to pick the closest-prior-entry semantics correctly for
      each window
- [x] **Exercise audio is actually analyzed**: uploading real synthetic audio alongside an
      exercise result produces genuine Parselmouth-computed measurements
      (`f0_mean_hz`, `hnr_db`, etc.) in the stored `measured_result`, not just live-coaching
      telemetry; a Breathing exercise (no vocal signal) and an exercise with no
      `target_measurement` both correctly receive no acoustic analysis at all
- [x] **Trend classification**: 5 repeated attempts of the same exercise produce a classified
      trend (`tests/integration/test_exercise_trends.py`); fewer than the minimum never produces
      a guessed direction; an exercise with no `target_measurement` never appears in trends at
      all
- [x] **Adaptive challenge never overrides a safety rule**: a positive trend on a day already
      capped by high discomfort, a red recovery status, or several rest days produces the exact
      same `intensity_cap` as without the positive trend — `tests/unit/test_exercise_routine.py`,
      `TestAdaptiveChallenge` class (6 tests)
- [x] **Adaptive challenge is visibly disclosed**: when active, `routine.reasons` includes a
      plain-language note; when inactive, it doesn't — the same transparency pattern as every
      other adaptive decision in the app
- [x] **244 backend tests + 34 audio-engine tests + 56 frontend unit tests, all passing.**
      `ruff check .` clean (both Python packages), `tsc --noEmit` clean, `eslint` clean, frontend
      production build compiles

### Manual (live, real backend + real Postgres, browser-driven)

- [x] Seeded real vocal-range data via the actual upload/submit endpoints, then loaded
      `/vocal-range` fresh: the page correctly skipped the recording flow and went straight to
      the summary (current range, historical best, falsetto note, piano visualization) — a real
      UX gap (no way to just *view* existing data without starting a new test) was found and
      fixed during this same manual pass, before being reported as working
- [x] Walked a full exercise routine live in-browser end to end, including the "Why this
      routine?" disclosure (expanded and confirmed it lists the actual active safety reasons)
      and the completion screen; this environment's Browser pane blocks real `getUserMedia`
      (same limitation as Stage 7), so the live audio-capture/trend-badge path is verified
      instead by the automated integration tests against synthetic audio above — the manual
      pass here confirms the surrounding UI (disclosure, graceful mic-denial degradation,
      completion flow) works correctly end to end
- [x] No new console errors beyond the same pre-existing, expected 401/404 noise already
      documented in Stage 4-7 testing

### Bug found and fixed during development

1. **Stage 3's F0 pitch ceiling (600Hz) was too low for genuine falsetto/head voice**, and the
   limitation was mis-documented as "covers the full human vocal range." A 660Hz falsetto test
   tone was tracked as its own octave-down subharmonic (330Hz) because it fell outside the
   search range entirely — not a bug in the octave-detection logic itself, but in an upstream
   constant this stage was the first to actually exercise at that range. Fixed by raising
   `F0_CEILING_HZ` to 1000Hz in `packages/audio-engine/src/vepair_audio_engine/measurements.py`,
   correcting the doc comment's overclaim, and adding a permanent regression test
   (`test_falsetto_range_frequency_detected_within_tolerance`) so it can't silently regress.
   Whistle register above ~1000Hz remains a documented, real, current limitation — not silently
   mishandled.
2. **No way to view existing vocal-range data without starting a new test.** `/vocal-range`
   always jumped straight into the recording flow, even for a returning user who just wanted to
   check their progress. Found live in-browser before being reported as working. Fixed by
   fetching the summary on mount and showing it directly when data exists, with an explicit
   "Record a new range test" action to start fresh.

### Result: PASS

Every scenario from the product brief's Stage 8 test plan, plus both explicit user-requested
additions (exercise listening/trend tracking, safety-subordinate adaptive challenge), behaves as
specified — confirmed against the real endpoints, not mocks. Two real issues were found,
root-caused, and fixed during this same development/testing pass, not discovered afterward: an
upstream pitch-ceiling limitation this stage's falsetto testing was the first to expose, and a
real UX gap in the range-summary page. No user-facing critical bugs remain open.

## 13. Stage 9 test plan

**From the user's own spec:** choose a Repair or Improvement track during profile setup; once
the app has heard the user's voice, generate an appropriate 90-day plan specific to the range it
analyzed; auto-move a user from Repair to Improvement once it looks like their voice has
stabilized, with Improvement being "one step up" — more aggressive about safely stretching
range — than Repair.

**PASS criteria:** track selection, plan generation, and auto-graduation all behave as
specified against the real endpoints; track can only ever adjust how readily existing
Stage 6/8 safety-bounded behavior engages, never weaken or bypass a hard safety rule; every
graduation-readiness reason is always shown, not just the binding one; no fabricated plan is
ever created without real underlying data.

**Actual results:** recorded below, run 2026-08-12 against the real running backend, real
Postgres, and a real Next.js production build (no mocks).

### Automated

- [x] **`assess_graduation_readiness`** correctly requires all three criteria (14+ days of
      data, ≥70% non-red status, baseline confidence "developing"/"established", zero declining
      exercise trends) and always returns all three reasons regardless of outcome —
      `tests/unit/test_vocal_plan.py`
- [x] **`build_target_milestones`** produces a stability goal for Repair and a range-extension
      goal (anchored to the user's own measured high note) for Improvement; rejects an unknown
      track
- [x] **`suggest_stretch_target`'s track parameter**: Repair suppresses the suggestion outright
      even with an improving trend; Improvement allows +2 semitones only when the trend is
      genuinely improving (not just non-declining), otherwise stays at the standard +1; every
      existing safety check (discomfort, red status, declining trend) still suppresses it
      regardless of track — `tests/unit/test_vocal_range.py`, `TestSuggestStretchTargetTrack`
- [x] **`RoutineSignals.track`**: Repair never enters challenge mode even with a positive trend;
      Improvement enters it without needing a positive trend; no track keeps Stage 8's original
      trend-gated behavior; Improvement's challenge mode still never overrides a high-discomfort
      cap or a red recovery status — `tests/unit/test_exercise_routine.py`, `TestTrackChallengeMode`
- [x] **Track selection end-to-end**: rejects an unknown track; requires onboarding to be
      completed first; a track chosen before assessment data exists reports why the plan isn't
      ready yet instead of fabricating one; a track chosen after assessment data exists creates
      a plan immediately with the correct milestones; submitting a vocal-range entry after
      choosing a track (in either order) creates the pending plan automatically —
      `tests/integration/test_vocal_plan.py`
- [x] **Auto-graduation end-to-end**: seeding 14 days of green recovery-score history plus an
      established baseline correctly graduates a Repair plan to Improvement, flips
      `UserProfile.track`, and reports `just_graduated: true`; without that history the plan
      correctly stays on Repair with `ready: false` and full reasons
- [x] **Improvement plans never report graduation readiness** (nowhere further to graduate to)
- [x] **283 backend tests + 34 audio-engine tests + 56 frontend unit tests, all passing.**
      `ruff check .` clean (both Python packages), `alembic check` reports no schema drift,
      `tsc --noEmit` clean, `eslint` clean, frontend production build compiles and registers the
      new `/vocal-plan` route

### Manual (live, real backend + real Postgres, real Next.js dev server, browser-driven)

- [x] Completed onboarding, then selected Repair on a real account that already had recorded
      voice-sample and vocal-range data from earlier stage testing: a plan appeared immediately
      with the correct stability-goal description, target date (start + 90 days), and days
      remaining, and the Progress-toward-Improvement section showed all three readiness reasons
      in plain language
- [x] Visited `/vocal-plan` for an account with no track chosen yet: showed the expected
      "you don't have a plan yet" state with links to choose a track and complete a vocal-range
      test, never a crash or a fabricated plan
- [x] Switched the same account from Repair to Improvement through the selector: the plan view
      updated to the range-extension goal — this exposed the bug described below before being
      reported as working
- [x] No new console errors beyond the same pre-existing, expected 401/404 noise already
      documented in Stage 4-8 testing

### Bug found and fixed during development

1. **Manually switching track through the selector silently kept the old, now-mismatched plan
   active.** `ensure_plan_exists` was a no-op whenever *any* active plan existed, regardless of
   whether its track matched the profile's newly chosen one — so selecting Improvement after an
   active Repair plan updated `profile.track` but left the Repair plan (and everything
   `/vocal-plan` displayed) unchanged. Found live in-browser, not by the original test suite,
   which only exercised the "no plan yet" and "plan already matches" cases. Fixed by adding
   `sync_plan_to_track`, used only by the track-set endpoint, which always produces a plan
   matching the track just chosen — while `ensure_plan_exists` keeps its original, more
   conservative no-op behavior for the unrelated-submission case, so an ordinary vocal-range or
   recording upload still can never accidentally restart the 90-day clock. Regression-tested:
   `test_manually_switching_track_replaces_a_mismatched_active_plan` and
   `test_reselecting_the_same_track_keeps_the_existing_plan`.

### Result: PASS

Every behavior from the user's Stage 9 spec — track selection during profile setup, an
auto-generated 90-day plan specific to the analyzed range, and auto-graduation from Repair to a
more aggressive Improvement track — works as specified, confirmed against the real endpoints
and a real browser session, not mocks. One real bug was found and fixed during this same
development/testing pass, not discovered afterward: manually switching track didn't replace a
stale plan from the old track. No user-facing critical bugs remain open.

## 14. Stage 10 test plan

**From the founder's own spec:** two read-only, exportable 1080×1920 images ("Today's Voice",
"My Progress") built entirely from real VepAIr data. Missing metrics must be omitted, never
fabricated; negative progress must be reported honestly; every displayed number must match its
source calculation; the feature must never modify voice measurements, the VepAIr Score,
baselines, recordings, or historical data.

**PASS criteria:** all of the above hold against the real endpoints; no email/account
ID/location/notes ever appear in either response; the export path produces a real image file.

**Actual results:** recorded below, run 2026-08-12 against the real running backend, real
Postgres, and a real Next.js production build.

### Automated

- [x] **Vocal Endurance measurement**: a continuous sustained tone's longest-voiced-run is close
      to the tone's full duration; a tone interrupted by a silent gap correctly reports only the
      longer unbroken segment, not the combined voiced time —
      `packages/audio-engine/tests/unit/test_measurements.py`
- [x] **Every Today/Progress field is independently omittable**: missing range, missing
      endurance, missing fatigue, a fresh user with zero data, and low measurement confidence
      (which specifically excludes Pitch Stability) all produce `null` fields rather than a
      fabricated value — `tests/integration/test_share_progress.py`
- [x] **Pitch Stability requires a real baseline**: omitted with only 2 sustained recordings
      (below the app's own `MIN_SAMPLES_FOR_ANOMALY_DETECTION` threshold), present once enough
      recordings exist to actually support the comparison
- [x] **Vocal Endurance requires at least two data points** to report a start-vs-now comparison;
      omitted with only one recording
- [x] **Negative progress reported honestly**: a fatigue check-in that rose from 2 to 8 reports
      `delta: 6` (worse), not hidden, reframed, or excluded
- [x] **Comparison basis is real and per-metric**: Comfortable Range and Reported Fatigue report
      `"first_valid_session"` from real seeded history with the exact expected start/now values
      and semitone delta
- [x] **"BUILDING YOUR BASELINE" fallback**: a fresh user with nothing recorded gets
      `insufficient_data: true` with a real (zero) valid-session count, not a fabricated
      comparison
- [x] **Score delta only appears when a real prior-day score exists** — omitted otherwise, never
      computed against a day that was never scored
- [x] **Privacy**: neither response's keys ever include email, user/account ID, location, or
      notes — `TestPrivacy` in `tests/integration/test_share_progress.py`
- [x] **Data validation**: the share-progress score and confidence label exactly match the same
      date's real `/api/v1/recovery-score` response; the comfortable-range note exactly matches
      the real `/api/v1/vocal-range/summary` response — guards "must match the source
      calculation" beyond documented rounding
- [x] **Regression**: the full pre-existing 283-test backend suite plus 34 pre-existing
      audio-engine tests still pass unchanged after adding Vocal Endurance — confirming the new
      measurement never altered the daily VepAIr Score or any other existing computation.
      **306 backend tests + 36 audio-engine tests + 56 frontend unit tests, all passing.**
      `ruff check .` clean, `alembic check` reports no drift, `tsc --noEmit` clean, `eslint`
      clean, frontend production build compiles and registers the new `/share` route

### Manual (live, real backend + real Postgres, real Next.js dev server, browser-driven)

- [x] Visited `/share` on a real account: Page 1 correctly showed `LOW MEASUREMENT CONFIDENCE`
      and omitted every confidence-gated field while still showing Comfortable Range and
      Training Completed (which don't depend on that gate) — confirming the "rebalance the page"
      behavior live, not just in tests
- [x] Page 2 correctly showed real Comfortable Range and Reported Fatigue start-vs-now
      comparisons with their basis label, Days Tracked/Sessions Completed/Training Compliance,
      and correctly omitted Pitch Stability/Vocal Endurance for this account's actual data
      state — Previous/Next navigation between pages worked correctly
- [~] **Save/Share image export could not be fully pixel-verified in this sandboxed
      environment.** The Browser pane here does not composite frames unless actively displayed
      to a human, which stalls `html-to-image`'s canvas-decode step (confirmed via
      `document.fonts.ready` resolving normally, and the library's DOM-to-SVG serialization step
      — its most failure-prone part — completing successfully over the network log as a real
      `data:image/svg+xml` request). This is the same category of sandbox limitation already
      documented for `getUserMedia` in every prior stage: real-device testing works differently
      than this harness. **Recommended: the founder verify Save/Share produces a real image on
      their own device before relying on this path in production.**
- [x] No new console errors beyond the same pre-existing, expected 401/404 noise already
      documented in Stage 4-9 testing

### Result: PASS, with one flagged manual-verification gap

Every behavior that could be tested against the real endpoints and a real browser session
behaves exactly as specified — accurate, honest, omission-over-fabrication, and provably
unchanged existing computations. The one item this sandbox structurally cannot confirm is
pixel-level image export; the underlying mechanism is verified as far as this environment
allows (font loading, DOM serialization) and the remaining step is a known category of headless-
browser limitation, not a code defect found here. Flagged explicitly above rather than silently
reported as fully verified.

## 15. Stage 11 test plan

**Scope, confirmed with the founder before building:** a new `/progress` page with a VepAIr
Score history chart, a training-consistency (streak) view, and a consolidated exercise trend
list — the three genuine gaps a pre-build codebase survey found (a vocal-range history chart was
surveyed but not selected, so it's out of scope for this stage).

**PASS criteria:** the score-history endpoint never backfills or mutates a day that wasn't
already scored; streaks are computed correctly across every edge case and never clipped to the
requested display range; the page renders correctly against real data in a real browser.

**Actual results:** recorded below, run 2026-08-12 against the real running backend, real
Postgres, and a real Next.js dev server.

### Automated

- [x] **`compute_streaks` covers every edge case**: no sessions ever; a single session today;
      a consecutive run ending today; a consecutive run ending yesterday (still counts — today
      isn't "broken" until the day is over); a streak broken two days ago (current correctly
      reports 0); a gap in the middle (longest picks the bigger run, current only reflects the
      run touching `as_of`); scattered non-consecutive days; current never exceeds longest —
      `tests/unit/test_training_consistency.py`
- [x] **Score history never backfills**: an empty account returns an empty list, not fabricated
      zeros; only days with an actually-stored `RecoveryScore` row appear; out-of-range days are
      excluded; days outside the range are excluded — `tests/integration/test_recovery_score_history.py`
- [x] **Score history never mutates a stored day**: seeding a past day's score, then giving
      *today* wildly different check-in data and requesting history spanning both days, leaves
      the past day's stored row byte-for-byte unchanged (checked directly against the database
      row, not through `GET /recovery-score`, which recomputes by design — the regression this
      test guards is specific to the read-only history endpoint)
- [x] **Training consistency reflects real completed sessions**: correct streak and per-day
      counts against real seeded `ExerciseSession` rows; multiple sessions on the same day count
      toward the total but never inflate the streak past one day; incomplete sessions
      (`completed_at is null`) never count at all; a streak that started before the requested
      display window still reports its true length, not clipped to the window —
      `tests/integration/test_training_consistency.py`
- [x] **325 backend tests + 36 audio-engine tests + 56 frontend unit tests, all passing.**
      `ruff check .` clean, `alembic check` reports no drift (no schema changes this stage),
      `tsc --noEmit` clean, `eslint` clean, frontend production build compiles and registers the
      new `/progress` route

### Manual (live, real backend + real Postgres, real Next.js dev server, browser-driven)

- [x] Visited `/progress` on a real account: the Score history chart rendered with real data
      (`latest: 89`), training-consistency streak counters and sessions-in-range showed correct
      real numbers, and the exercise-trend section correctly showed its empty state for this
      account (no exercise attempts with a qualifying `target_measurement`/quality result yet —
      consistent with this environment's documented `getUserMedia` limitation, not a bug)
- [x] Switched between every range option (7/30/90/180 days, 1 year, all-time) live: each click
      sent the correct `from_date`/`to_date` to both endpoints (confirmed via the network log,
      e.g. 90 days → an exact 90-day span, all-time → `2020-01-01`), and the page re-rendered
      without error or crash even at the largest range
- [x] Confirmed the new "Progress" nav link on the dashboard homepage reaches the page correctly
- [x] No new console errors beyond the same pre-existing, expected 401/404 noise already
      documented in Stage 4-10 testing

### Result: PASS

Every piece of the confirmed scope — score history, training consistency, consolidated exercise
trends — works as specified against real endpoints and a real browser session. No bugs found
during this stage's development or testing pass. No user-facing critical bugs remain open.

## 16. Stage 12, Phase II test plan — VepAIr Coach pilot (dev-only)

**Scope, per the approved plan (`C:\Users\ADMIN\.claude\plans\linear-plotting-garden.md`):**
invite lifecycle, per-category revocable consent, a read-only coach dashboard that reuses the
singer's own scoring functions, training assignment that can never bypass an existing safety
cap, recording comparison, and professional notes with concrete clinical-language mitigations.
**Built and tested dev-only, per explicit founder instruction — nothing in this section ran
against production Supabase or the deployed app; all of it ran against local dev Postgres and
`npm run dev`/`uvicorn --reload`, same as every prior stage's verification pattern.**

**PASS criteria:** every authorization boundary holds (a coach can only ever read a singer who
granted them access, only for granted categories); the coach dashboard's numbers are provably
identical to the singer's own, not a re-derived copy; a coach assignment can never push a routine
past today's existing safety cap, confirmed even when a coach actively tries to; hardcoded
free-text fields never appear in any coach-facing response regardless of category grants; revoke
is immediate for future access and forward-only for the past, exactly as the UI claims.

**Actual results:** recorded below, run 2026-08-12 against the real running backend, real local
Postgres, and a real Next.js dev server (no mocks).

### Automated

- [x] **Coach auth boundary**: 403 `not_a_coach` for a singer calling any `/api/v1/coach/*`
      endpoint; 403 `no_active_access` with no/revoked `CoachAccess`; 403 `category_not_shared`
      for an ungranted category — `tests/integration/test_coach_auth.py`
- [x] **Invite lifecycle**: invite-by-email happy path; 404 on a nonexistent email; no duplicate
      pending invites (409); accept requires ≥1 category; decline creates no `CoachAccess`;
      cancel; **a second singer cannot accept an invite addressed to someone else**;
      **cannot accept a second invite while one coach is already active** (409, backed by the DB
      partial unique index, not just the application check); **the singer list returns real
      identifying info (email, granted categories, granted-at), never bare UUIDs** — this guards
      a real bug caught and fixed before the frontend was built around the broken shape —
      `tests/integration/test_coach_invites.py` (12 tests)
- [x] **Coach dashboard reuse, the centerpiece regression tests**:
      `test_coach_dashboard_recovery_score_matches_singers_own_endpoint` and
      `test_coach_vocal_range_summary_matches_singers_own_endpoint` call both the singer's own
      endpoint and the coach's endpoint, as two different authenticated actors, for the same
      user/date, and assert byte-identical JSON — proves the coach dashboard calls the same
      scoring functions rather than a re-derived copy; category gating (recordings denied when
      only trends granted); coach A cannot read coach B's singer; **`DailyCheckIn` free-text
      fields never appear in any coach response**, asserted as a negative-content check, same
      style as Stage 10's share-progress regression; every consent change appends a new
      `ConsentRecord`; category toggle-off blocks only that category; revoke immediately blocks
      reads but not previously-written notes — `tests/integration/test_coach_access.py` (11
      tests)
- [x] **Recording comparison**: category-gated playback, 404 for a recording belonging to a
      different singer, structured audit log line confirmed on a real access —
      `tests/integration/test_coach_recordings.py` (4 tests)
- [x] **Training assignment — the highest-risk regression in this stage**:
      `test_discomfort_hard_override_cannot_be_bypassed_by_coach_assignment` and five further
      cases in `TestCoachAssignment` (`tests/unit/test_exercise_routine.py`) confirm an assigned
      exercise is included only when it's already in the safety-filtered `allowed` list, excluded
      with a visible reason when it isn't, and never changes the computed intensity cap itself;
      end-to-end: a real routine reflects an active assignment, a revoked `CoachAccess` stops
      influencing the routine immediately, a new assignment supersedes rather than deletes the
      old one — `tests/integration/test_coach_assignments.py` (5 tests)
- [x] **Professional notes**: blocklist match still saves the note (flags, never blocks); no
      warning without a trigger word; over-2000-char rejected (422); the singer can read notes
      about them, another singer cannot; soft-delete removes a note from the coach's list but
      never from the singer's read access — `tests/integration/test_coach_notes.py` (8 tests)
- [x] **398 backend tests pass** (up from 339 before this stage — 59 new), `ruff check .` clean
      (migration files excluded, same pre-existing exception as every prior migration),
      `alembic check` reports no drift against the applied local migration
- [x] Frontend: `tsc --noEmit` clean, `eslint` clean (two stray `eslint-disable` comments left
      over from defensive copy-paste were caught and removed — the rule never actually fired at
      those two call sites), `vitest` — **63/63 passing**, `next build` succeeds and registers
      every new coach route (`/coach`, `/coach-signup`, `/coach-access`, `/coach/invite`,
      `/coach/singers/[singerId]` + its three sub-routes)

### Manual

**Not yet performed as of this report** — the plan's Verification section calls for a live,
two-real-account pass (sign up a second account as a coach, invite the first, accept with a
subset of categories, confirm the coach dashboard matches the singer's own dashboard exactly,
assign an exercise and confirm safe inclusion/exclusion in the singer's next routine, write a
blocklisted-term note and confirm the warn-but-save behavior, then revoke and confirm the coach
is immediately locked out while the singer still sees the note history). This is explicitly
deferred: the dev-only build constraint means this pass happens against local dev, not the live
app, and is the founder's to run (or request) before deciding whether to move Phase II toward
real pilot coaches — recorded here as an open item, not silently skipped.

### Result: PASS on everything automated; manual end-to-end pass still pending

Every authorization boundary, reuse-regression, safety-cap regression, and privacy-boundary test
from the approved plan passes against the real endpoints (not mocks). No user-facing critical
bugs found during this stage's development. The one explicitly open item is the founder's own
manual two-account walkthrough, which by design hasn't run yet — this stage stays dev-only,
unmerged, and undeployed until that happens and an explicit go-ahead is given.
