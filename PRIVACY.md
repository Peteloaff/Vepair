# VepAIr Privacy Policy (Engineering Reference)

Voice recordings are extremely personal — potentially identifying and health-adjacent. This
document sets binding engineering requirements, not a public-facing legal privacy policy.

## 1. Principles

- **Minimal collection**: collect only what a current stage's features need. Don't add fields
  "for later."
- **User control**: users can export or delete their data at any time.
- **No public-by-guessable-URL storage**: recordings are never reachable via a predictable URL.
  All access goes through an authorized, authenticated API call that checks ownership.
- **Consent is granular**, not a single checkbox — see Section 3.

## 2. Data categories

| Category | Examples | Storage |
|---|---|---|
| Account data | email, auth identity | Supabase Auth + `User` table |
| Profile data | onboarding answers, goals | `UserProfile` |
| Subjective journal data | daily check-ins | `DailyCheckIn` |
| Audio recordings | raw voice samples (guided sessions, vocal range tests) | Object storage (local FS in dev; access-controlled bucket in prod), never inline in the DB |
| Derived measurements | F0, jitter, shimmer, etc. | `AcousticMeasurement`, linked to `Recording` by id only |
| Exercise attempt audio (Stage 8) | audio from an exercise with a target measurement | **Not stored at all** — analyzed in-memory during the upload request, then discarded; only the derived numbers persist in `ExerciseResult.measured_result` |
| Exercise trend data (Stage 8) | per-exercise improving/declining/stable classification | Derived on read from `ExerciseResult.measured_result` history — no separate table |
| Vocal range history (Stage 8) | comfortable low/high/falsetto notes over time | `VocalRange`, `source_recording_id` links back to the underlying `Recording` (stored normally, same as any other guided-session recording) |
| Share My Progress images (Stage 10) | rendered PNGs of the user's own aggregate stats | **Never stored anywhere** — generated client-side, in the browser, from an authenticated read of already-stored data, and only saved to the user's own device or handed to the OS share sheet when they explicitly tap Save/Share. No server-side rendering, no upload, no copy retained by VepAIr. |
| Device metadata | mic/device fingerprint | `DeviceMetadata` |
| Consent records | what the user agreed to, when | `ConsentRecord` |

## 3. Consent is separated by purpose

At minimum, VepAIr tracks these as **independent** consent grants (a user can accept one and
decline another):

1. **Product analytics consent** — aggregate, non-audio usage analytics (see `ANALYTICS`
   section of the product brief: DAU, check-in completion, retention, etc.).
2. **Model training consent** — using a user's recordings/derived data to improve VepAIr's
   models. Off by default. Never inferred from analytics consent.
3. **Coach sharing consent** (`coach_sharing` — VepAIr Coach, Stage 12 Phase II, see
   `ROADMAP.md`; information purposes only, never clinical) — per-coach, revocable grant letting
   a vocal coach the user has explicitly accepted an invite from view a specific singer's data.
   Not automatic just because a coach knows the singer: the singer must accept an invite, and
   accepting requires choosing at least one of four independent categories —
   **`recovery_trends`** (VepAIr Score + history), **`vocal_range`** (comfortable range summary),
   **`exercise_history`** (routine, exercise trends, training consistency), **`recordings`**
   (uploaded audio + playback) — all unchecked by default, independently toggleable later without
   a full revoke. One active coach per singer at a time (DB-enforced). Revoking is immediate for
   future access (the coach's next request is rejected) but forward-only for the past — already-
   viewed data isn't retroactively unshown, and the revoke confirmation says so plainly.
   **`recordings` specifically: VepAIr never creates or stores a separate copy of a singer's
   audio for a coach.** There is exactly one copy of any recording, ever — the singer's own,
   in the same storage this document already describes. A coach with the `recordings` category
   granted gets a live, authenticated link into that single copy (`GET /api/v1/coach/singers/
   {id}/recordings/{id}/audio`), gated by the same category-grant check as every other read;
   nothing is downloaded, cached, or persisted on the coach's side by the app itself, and
   revoking the category or the connection cuts off that link immediately, same as any other
   category. We don't retain a singer's voice anywhere beyond the one copy they already own.
   `DailyCheckIn.illness_symptoms`/`.reflux_symptoms`/`.notes` and `VoiceSession.notes` are never
   readable by a coach regardless of any grant — a code-level omission, not a togglable category.
   Coach-authored notes about a singer are readable by that singer permanently, surviving revoke
   (see `MEDICAL_SAFETY.md` §12 for the freeform-note-specific mitigations). Renamed from
   "clinician sharing consent" / `clinician_sharing` — see `CHANGELOG.md`.
4. **Notifications / product communications consent** — whether VepAIr may contact the user
   (e.g. by email) with notifications or updates. Off (unset) by default until the user makes
   an explicit choice — see the Yes/No control on the onboarding page, backed by
   `GET`/`PUT /api/v1/consent/notifications`. **If granted, VepAIr may use the user's contact
   information (their account email) to reach them for this purpose.** This is a distinct
   purpose from analytics, model training, and professional sharing above — granting one never
   implies granting another, and this consent specifically does not authorize using contact
   data for anything beyond notifications/updates (e.g. it is not blanket permission for
   unrelated marketing or third-party sharing).

No recording or derived measurement may be used for population-level model training without
explicit, purpose-specific, informed consent — never bundled into a generic ToS acceptance.

## 4. User rights implemented at the data-model level

- **Recording deletion**: deleting a `Recording` removes the underlying audio file and cascades
  to its `AcousticMeasurement`s. Aggregated/statistical baselines that already incorporated it
  are recomputed, not silently left stale.
- **Account deletion**: cascades across all tables scoped to that `User`, including object
  storage cleanup.
- **Data export**: a user can request a machine-readable export of their own data (JSON initially
  for structured data; audio files as-is).
- **Auditable access**: every read of a `Recording`'s audio by anyone other than its owner
  (e.g. a future authorized vocal coach, via VepAIr Coach's consent system above) must be
  attributable to a specific actor and reason.

## 5. Transport & storage security

- All traffic over HTTPS/TLS in any non-local environment.
- Object storage access uses short-lived, scoped credentials/signed URLs — never a permanently
  public bucket or object.
- Secrets (DB credentials, storage keys, Supabase keys) live only in environment variables /
  secret managers, never in source control. See `.env.example` files and `.gitignore`.

## 6. What's actually implemented so far

Stage 0 shipped the schema (`ConsentRecord`, ownership foreign keys on every user-scoped table)
and the architectural seam for object storage access control.

Stage 2 shipped recording **upload** and **playback**, both ownership-scoped (a recording is
only ever reachable by the user who created it — verified with cross-user authorization tests,
not just asserted) and never served from a predictable/guessable URL (playback requires a valid
bearer token and an ownership check, not just knowing the recording id).

**Still not implemented: recording deletion and data export.** Deleting a `User` cascades the
database rows (`VoiceSession` → `Recording` via `ON DELETE CASCADE`) but does **not** delete the
underlying audio file from storage — there is no deletion code path at all yet for an individual
recording (no delete endpoint exists). This is a real gap against this document's "recording
deletion" and "data export" requirements above, tracked as a recommended change before Stage 3.

Stage 8 shipped exercise-attempt audio analysis with the strictest "minimal collection" posture
in the app: audio uploaded alongside an exercise result is analyzed in-memory during that one
request (`app/exercise_audio.py`) and never written to storage — no `Recording` row, no object
storage key, nothing to later delete or export because nothing was kept. Only the derived
numbers (jitter, shimmer, HNR, etc., whichever the exercise's `target_measurement` is) persist
in `ExerciseResult.measured_result`. Vocal range test recordings (Stage 8) go through the
ordinary Stage 2 upload/storage path like any other recording, so they inherit both the
capabilities above (ownership-scoped playback) and the same still-open gap (no per-recording
deletion yet).

Stage 10's Share My Progress endpoints (`GET /api/v1/share-progress/today`,
`GET /api/v1/share-progress/progress`) are read-only aggregate views over already-stored data —
no email, account ID, location, or raw journal/notes text is ever included in either response
(confirmed by an explicit regression test). The two exported images never touch the server: they
are rendered entirely client-side from that authenticated response and only leave the device
when the user explicitly taps Save or Share.

The **notifications consent** purpose (section 3, #4) is implemented via
`GET`/`PUT /api/v1/consent/{consent_type}`, backed by the `ConsentRecord` table Stage 0 already
shipped the schema for. Every choice is inserted as a new, timestamped row rather than updated
in place — the full history of what a user decided, and when, is preserved, matching this
document's "auditable access" principle. A user who has never been asked reads back as
`granted: null`, distinct from an explicit `false`, so "hasn't decided" is never conflated with
"said no." The other two consent types this table anticipates (`product_analytics`,
`model_training`) are validated by the same endpoint but have no UI or enforcement wired to them
yet.

**Coach sharing consent (Stage 12 Phase II, dev-only build — see `ROADMAP.md`)** is fully
implemented, not just a validated-but-unwired type like the two above. `ConsentRecord` gained a
`category` column (populated only for `consent_type == "coach_sharing"`) and a real FK from
`clinician_id` to the new `coach_profiles` table (previously unconstrained and unused). Every
accept, category toggle, and revoke appends a new `ConsentRecord` row via
`app/routers/coach_access.py` — the append-only audit ledger this section's principles require.
**Authorization at request time never queries this ledger** — a separate materialized
`CoachAccess`/`CoachAccessCategoryGrant` pair (checked by `app/coach_auth.py`'s
`require_coach_access`) is what every coach-facing endpoint actually gates on, since a ledger of
timestamped events is the wrong structure to query on every request. `GET
/api/v1/coach/singers/{id}/recordings/{id}/audio` logs a structured `coach_recording_access` line
(`app/routers/coach.py`) for the "auditable access" requirement above — deliberately just a log
line for pilot scale, not yet a queryable table; a real `CoachDataAccessLog` is deferred to the
admin backend (`ROADMAP.md`'s Stage 12 admin-tooling section) if the pilot's scale warrants it.
