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
| Subjective journal data | daily check-ins | `DailyCheckIn`. The three free-text fields (`illness_symptoms`, `reflux_symptoms`, `notes`) are nulled after `checkin_notes_retention_days` (admin-configurable, default 30) — every quantitative field (voice quality, fatigue, sleep hours, etc.) is kept indefinitely so trend history stays whole. |
| Audio recordings | raw voice samples (guided sessions, vocal range tests) | Object storage (local FS in dev; access-controlled bucket in prod), never inline in the DB. Auto-purged after `recording_retention_days` (admin-configurable, default 90) — the file is deleted and `Recording.file_path` nulled, but the row and its derived measurements are kept so trend history stays whole; see Section 6. |
| Derived measurements | F0, jitter, shimmer, etc. | `AcousticMeasurement`, linked to `Recording` by id only |
| Exercise attempt audio (Stage 8) | audio from an exercise with a target measurement | **Not stored at all** — analyzed in-memory during the upload request, then discarded; only the derived numbers persist in `ExerciseResult.measured_result` |
| Exercise trend data (Stage 8) | per-exercise improving/declining/stable classification | Derived on read from `ExerciseResult.measured_result` history — no separate table |
| Vocal range history (Stage 8) | comfortable low/high/falsetto notes over time | `VocalRange`, `source_recording_id` links back to the underlying `Recording` (stored normally, same as any other guided-session recording) |
| Goal Tones (post-Stage-12) | a singer's target low/avg/high note, AI-suggested or manually set | `VocalGoal` — current-state only, one row per user, no history kept |
| Tone Match average-pitch recording (post-Stage-12) | `sample_type: "tone_baseline"` | Same `Recording`/`AcousticMeasurement` storage and rules as every other recording (Section 4) — an ordinary sustained sample, not a new category |
| Share My Progress images (Stage 10) | rendered PNGs of the user's own aggregate stats | **Never stored anywhere** — generated client-side, in the browser, from an authenticated read of already-stored data, and only saved to the user's own device or handed to the OS share sheet when they explicitly tap Save/Share. No server-side rendering, no upload, no copy retained by VepAIr. |
| Device metadata | mic/device fingerprint | `DeviceMetadata` |
| Consent records | what the user agreed to, when | `ConsentRecord` |
| Login events | timestamp of each successful password login | `LoginEvent` — deliberately **not** IP address or user-agent; auto-purged past `login_event_retention_days` (admin-configurable, default 365) |

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

- **Recording deletion**: `DELETE /api/v1/recordings/{id}` removes the underlying audio file
  from object storage and cascades to its `AcousticMeasurement` (`ON DELETE CASCADE`). **Not**
  fully retroactive: it removes the recording from future trend/baseline computation but does
  not recompute an already-stored `Baseline`/`RecoveryScore` row that incorporated it — a known,
  User-Guide-documented limitation, not a silent gap.
- **Automatic audio purge**: independent of the above, raw audio for *every* recording is
  auto-deleted from storage after `recording_retention_days` (Section 2) regardless of whether
  the user ever asks — a passive minimization default, not a user action. The `Recording` row,
  `quality_flags`, and `AcousticMeasurement` are kept either way, so trend charts and scores stay
  intact after the audio itself is gone; playback 404s with `audio_purged` instead of erroring.
- **Account deletion**: cascades across all tables scoped to that `User`, including object
  storage cleanup.
- **Data export**: `GET /api/v1/profile/export` returns a machine-readable JSON download
  (`app/data_export.py`) covering every table keyed to the user — profile, consent history,
  check-ins, sessions/recordings metadata and measurements, baselines, scores, vocal range,
  goals/plans, exercises, coach connections (notes and messages, both directions) — everything
  except raw audio bytes, which link back to the existing authenticated playback endpoint instead
  of being embedded. Reachable from Settings, directly above account deletion.
- **Auditable access**: every read of a `Recording`'s audio by anyone other than its owner
  (e.g. an authorized vocal coach, via VepAIr Coach's consent system above) must be attributable
  to a specific actor and reason.
- **Admin access is itself access to user data, and is audited the same way.** The backend
  admin account type (Section 6) can view any account's email, activity summary, and
  onboarding/status flags, and can deactivate, reactivate (individually or in bulk), permanently
  delete, or trigger a password reset on any account; a `full`-tier admin can additionally
  impersonate an account read-only or export the contact list (Section 6). None of this is gated
  by the singer's own consent — it is operational access, not a coach-style sharing relationship
  — but every state-changing admin action, including each user affected by a bulk action, every
  impersonation start/end, and every contact-list export, is written to `AdminAuditLog` (admin,
  action, target, timestamp) before it takes effect, so "who did what to which account, and when"
  is always reconstructable. Admin reads (search, detail view, reports) are not individually
  logged — only actions that change state or hand data out (impersonation, export) — consistent
  with this document's existing practice of logging events, not every read.

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

**Account deletion (with storage cleanup) is implemented.** `DELETE /api/v1/auth/me` is a
self-serve, password-gated (same bar as changing a password) endpoint: it deletes every
`Recording`'s actual audio file from object storage via `get_storage().delete(...)` *before*
deleting the `User` row, then lets `ON DELETE CASCADE` remove every remaining database record
scoped to that user. A single flaky storage call is logged and skipped rather than blocking the
deletion, so a user can never be stuck unable to delete their own account. This closes the gap
this section used to describe.

**Per-recording deletion, automatic audio purge, data export, and shortened check-in-note
retention are all implemented** (the data-minimization round referenced throughout this
document). `DELETE /api/v1/recordings/{id}` gives users a full-removal option per recording;
independently, `app/data_retention.py`'s `purge_stale_recordings` and
`purge_stale_checkin_notes` run daily via `POST /api/v1/system/purge-stale-data` (Cloud
Scheduler job, `X-Internal-Job-Secret` auth — same pattern and secret as the reminders job, see
`TECHNICAL_GUIDE.md` §12) to auto-delete stale raw audio and null stale sensitive free-text
check-in fields on a rolling basis, no user action required. Both retention windows are
admin-configurable from `/admin` without a redeploy. `GET /api/v1/profile/export`
(`app/data_export.py`) closes the export gap. The only remaining open item against Section 4 is
retroactive baseline recomputation on recording delete (noted above) — everything else this
section used to flag as missing is now shipped.

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

**Backend Admin** is implemented: `User.is_admin`/`User.is_active` (additive columns, both
default to the pre-existing behavior) plus `AdminAuditLog`, a `ConsentRecord`-shaped append-only
table (`app/admin_audit.py`'s `log_admin_action`, called by every state-changing admin endpoint
in the same transaction as the change). `app/admin_auth.py`'s `get_current_admin` gates every
`/api/v1/admin/*` route on the `is_admin` flag, checked server-side on every request — never a
client-trusted claim. There is no self-serve or API path to become an admin; see
`TECHNICAL_GUIDE.md` §9 for the one-time manual bootstrap. Hard delete requires the target
account to already be deactivated first (`409 must_deactivate_first` otherwise) and reuses the
exact same `app/account_deletion.py`'s `delete_user_and_storage` self-serve delete already uses,
so there remains exactly one account-deletion code path in the app. See Section 4's new bullet
above for how this reconciles with "auditable access."

**Admin role tiers, bulk operations, impersonation, login events, and contact export** are all
implemented, each with the narrower guardrails this document's minimization theme calls for
rather than the loosest possible version:
- `User.admin_role` splits admin accounts into `support` (search, detail, reports, deactivate/
  reactivate including bulk, password reset) and `full` (everything `support` can plus
  hard-delete, grant/revoke admin, coach/coach-pro flags, site settings, password overwrite,
  impersonation, and contact export) — enforced server-side by `require_full_admin`
  (`app/admin_auth.py`), never a client-trusted flag.
- **Bulk operations** are deliberately scoped to the two already-fully-reversible actions —
  bulk deactivate/reactivate — never bulk hard-delete or bulk admin-grant. One `AdminAuditLog`
  row per affected user, not one for the whole batch, so the audit trail's granularity is
  unchanged.
- **Impersonation** (`full`-admin only) issues a short-lived (~15 min), non-refreshable access
  token carrying an `impersonated_by` claim, and is **enforced read-only at the framework level**
  — `get_current_user` (`app/auth.py`) rejects any non-GET/HEAD/OPTIONS request carrying an
  impersonation token, so it isn't a per-endpoint convention that could be missed on a future
  route. The "view as" page itself surfaces only non-health account/engagement facts (practice
  frequency, musical style, a 7-day check-in count) — never recovery scores or check-in wellness
  content, by explicit design, not omission. Every start and end is its own `AdminAuditLog` row.
- **Login events** (`LoginEvent`, Section 2) record only a timestamp per successful password
  login — no IP, no user-agent — replacing the previous refresh-token-based last-login proxy
  with a real signal, on the same minimize-what's-kept footing as the rest of this document.
- **Contact-list export** (`GET /api/v1/admin/users/export`, `full`-admin only) returns **email
  address only** — no name, no health or activity data — matching "email is the only contact PII
  this app keeps." Every call is logged via `log_admin_action` with the filters used (not the
  row contents), the same hard-delete-level audit rigor, since it's the one action in the admin
  surface that hands raw PII out of the system.
