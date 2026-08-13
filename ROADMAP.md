# VepAIr Roadmap

VepAIr is built in strict, sequential stages. **No stage begins until the previous stage has a
PASS test report and explicit approval from the founder (Pete).**

## Release grouping

| Release | Stages | Goal |
|---|---|---|
| **VepAIr Alpha** | 0–5 | Measure voice consistently, establish a personal baseline, produce meaningful personalized trends. |
| **VepAIr Beta** | 6–11 | Actively help users train and understand their voice. |
| **VepAIr Coach (B2B SaaS)** | 12 | Turn VepAIr into a professional platform for vocal coaches/studios — see below. |
| **VepAIr Pro / Backlog** | unscheduled | Computer vision, wearables, and other deprioritized ideas — revisited only if they become a priority. |

## Stage list

| Stage | Name | Status |
|---|---|---|
| 0 | Foundation and Architecture | ✅ Built and approved |
| 1 | User Account + Daily Vocal Journal | ✅ Built and approved |
| 2 | Voice Recording Lab | ✅ Built and approved |
| 3 | Acoustic Analysis Engine | ✅ Built and approved |
| 4 | Personal Vocal Baseline | ✅ Built and approved |
| 5 | VepAIr Daily Recovery Score | ✅ Built and approved |
| 6 | Personalized Daily Exercises | ✅ Built and approved |
| 7 | Live AI Vocal Coach | ✅ Built and approved |
| 8 | Vocal Range Mapping | ✅ Built and approved |
| 9 | Personalized Vocal Track & 90-Day Plan | ✅ Built and awaiting approval |
| 10 | Share My Progress | ✅ Built and awaiting approval |
| 11 | Progress Dashboard | ✅ Built and awaiting approval |
| — | **Deployment milestone**: move to Supabase dev/prod, set up the GitHub workflow, prepare for Google Play submission | ⚪ Happens after Stage 11 is approved, before Stage 12 begins — see "Deployment milestone" below |
| 12 | VepAIr Coach (Professional SaaS for vocal coaches/studios) | 🟡 Phase II (Coach pilot) built on `feature/coach-portal`, dev-only, not yet merged/deployed — see below |

**Backlog (deprioritized, not scheduled):** Computer Vision Coach (optional/experimental),
Wearables + Vocal Load. Revisited only if they become a priority — removed from the numbered
sequence so they stop implying an order they no longer have.

### VepAIr Coach — phased rollout (Stage 12, from the founder's monetization strategy doc)

Stage 12 is large enough that it will be scoped in detail (like Stages 9 and 10 were) only once
we reach it, but the founder's doc already lays out a phase order worth recording now so later
scoping starts from it rather than re-deriving it.

**Core workflow, confirmed directly by the founder:** a coach invites a user (singer) to their
portal; the user must accept before the coach gets any access (never automatic just because the
coach knows the user — see the consent workflow below); once accepted, the coach can set up
custom training for that user (assigning specific routines/exercises, not just the app's own
adaptive default); the coach can see that user's results and trends in something close to real
time — the same measurements and trend data the user already sees in their own app, surfaced on
the coach's side once authorized.

Phases:

1. **Phase I — Prove the consumer engine.** Already underway: reliable recordings, personal
   baselines, validated measurements, range/endurance tracking (Stages 1-10).
2. **Phase II — Coach pilot.** Singer dashboard, training assignment, progress tracking,
   recording comparison, professional notes — unpaid, with a small number of real coaches, to
   test whether they actually use it. **Built** on `feature/coach-portal` (invite/accept
   lifecycle, per-category revocable consent, read-only dashboard reusing the singer's own
   scoring functions, training assignment that can never bypass an existing safety cap,
   coach-signup flow, professional notes with blocklist + disclaimer mitigations) — see
   `ARCHITECTURE.md` §6m, `MEDICAL_SAFETY.md` §12, `PRIVACY.md` §3/§6, `TESTING.md` §16. **Not
   yet merged to `main` or deployed** — stays dev-only until the founder gives an explicit
   go-ahead to invite real pilot coaches.
3. **Phase III — Paid VepAIr Coach.** Professional subscriptions for independent coaches/singing
   teachers first (~$79-149/mo per the doc's proposed range — to be validated, not fixed).
4. **Phase IV — VepAIr Studio.** Multiple coaches, seat management, centralized billing,
   organization reporting (~$299-499+/mo).
5. **Phase V — University/Enterprise.** Annual contracts for music programs, performing arts
   programs, large studios, voice organizations.

**Explicitly out of scope, not a future phase, not on this roadmap at all: anything clinical or
regulatory.** VepAIr Coach is for vocal coaches, singing teachers, studios, and educational
programs — information purposes only, same as the consumer product. The founder's source doc
sketched a hypothetical future "VepAIr Clinical" layer for credentialed clinical use; that idea
is dropped, not deferred — it is not part of Stage 12 in any form, present or future. This
replaces the standalone "Clinician Portal" stage that was previously on this roadmap.

Non-negotiable from the doc, carried into every phase's eventual build: singer-controlled,
revocable, per-category consent before any professional gets access to a singer's data (never
automatic just because a coach knows the singer); the platform never auto-diagnoses a medical
condition — same `MEDICAL_SAFETY.md` boundary as the consumer product; one shared Voice
Intelligence engine, not a second parallel one for professionals.

### Internal admin backend (founder's operational tooling — scoped, not yet built)

Distinct from the VepAIr Coach portal above (which is for external vocal coaches/studios): the
founder needs an internal, GUI admin backend for running the business — user administration,
data pulls for contact lists, and reporting. Not a customer-facing feature, but grouped into
Stage 12 because it depends on the same foundation that stage already has to build (role-based
access beyond today's single "user" role; audit logging for who accessed what).

**Why this got scoped now, ahead of the rest of Stage 12**: the Coach Pilot's first production
deploy needed two throwaway test accounts and one real account cleaned up, and the only way to
do it was a raw `DELETE FROM users` over a direct Cloud Shell `psql` connection using the
production database's full connection string (password included) — typed straight into a
terminal, with no record of who deleted what or why beyond this chat log. That's the concrete
gap this section closes. Deferred to build until the founder gives the go-ahead (same dev-first,
review-before-release posture as everything else in Stage 12), but scoped in real detail now
rather than left as a stub.

**v1 scope — directly informed by that gap, nothing speculative:**

- **Admin auth**: a real admin role, not a flag repurposed from something else. Simplest correct
  shape: an `is_admin: bool` column on the existing `User` model (additive, same pattern as every
  other optional-attribute rollout in this schema), checked server-side by a `get_current_admin`
  dependency mirroring `app/coach_auth.py`'s `get_current_coach` exactly — 403 if the flag isn't
  set, never a client-trusted role claim. Reuses the existing login endpoint (an admin is still
  a `User` row with `AuthCredential`); no separate admin-auth system to maintain.
- **User search & lookup**: find an account by email, see its type (singer/coach), signup date,
  and onboarding/profile completeness — the exact information that took a manual SQL query to get
  today (see `TECHNICAL_GUIDE.md` §8, "Direct database access (diagnostics)" — this replaces that
  workflow with a real UI, not a parallel one).
- **Account deactivation/deletion through a real endpoint, not raw SQL**: `DELETE FROM users`
  run by hand has no confirmation step, no audit trail, and no soft-delete recovery window. A
  `POST /api/v1/admin/users/{id}/deactivate` (soft, reversible) and a separate, more deliberate
  hard-delete path — both going through the same cascade the schema already guarantees, just
  with a record of who did it and when.
- **Password reset that actually emails the user**: this is arguably a prerequisite, not a nice-
  to-have — `apps/api/app/email.py` still only logs reset tokens server-side (a real gap since
  Stage 1, reconfirmed live during this deploy: production's "Forgot password" doesn't work for
  a real user today). An admin-triggered reset is the fastest path to closing that gap without
  first standing up a full transactional-email provider for self-serve resets.
- **Reporting**: aggregate business/usage metrics (signups, retention, engagement) — the kind of
  data `PRIVACY.md`'s existing "product analytics consent" purpose already anticipates.
- **A real audit log, not just a log line**: `PRIVACY.md` §4's "auditable access" commitment is
  currently honored by exactly one structured log line (coach recording access in
  `app/routers/coach.py`) — good enough for a read, not good enough for a delete. Every admin
  action (who, what, on which account, when) needs a real queryable table here, since this is the
  first place in the app a person can take a destructive action on someone else's data.

**Explicitly deferred past v1**: bulk operations, a second admin role/permission tiers,
impersonation ("log in as this user"), and the contact-list/outreach export called out below —
each is a real feature with its own scope, not a checkbox to add to v1's list.

- **Contact list / data export for outreach — needs a privacy decision before it's built, not
  just an engineering task**: `PRIVACY.md` §3's consent model currently covers product analytics,
  model training, and coach sharing — it does not cover marketing/outreach contact use. Pulling
  emails to build contact lists is a distinct purpose from those three and likely needs its own
  explicit consent grant (or at minimum a clear opt-out) rather than assuming every registered
  user is contactable for outreach by default. `PRIVACY.md` should be updated with that decision
  before this ships, not worked around in code.

Same non-negotiables as the rest of Stage 12 apply here: no clinical/diagnostic data exposure,
audit-logged access, never a shortcut around the consent model.

### Subscription tiers / paywall (confirmed coming, details not yet decided)

**Founder confirmed directly (2026-08-13): a paid tier is coming for the consumer app, not just
for VepAIr Coach.** Until now, every monetization plan on this roadmap was B2B — VepAIr Coach's
own Phase III–V pricing above is coaches/studios paying for the coach portal. This is a
**second, separate axis**: individual accounts (both singers and coaches) will have Free vs.
Pro tiers on the consumer/coach-pilot product itself. Three named tiers so far: **Free**,
**User Pro** (paid singer tier), **Coach Pro** (paid coach tier) — the founder was explicit that
feature boundaries, pricing, and whether a free Coach tier exists at all are **not decided yet**.
Nothing below should be read as locking in those decisions; it's scoped so the architecture
doesn't accidentally make them harder to make later.

**What's worth building structurally now vs. waiting entirely:** nothing — no schema, no billing
integration, no gating code should be built until real pricing decisions exist, same as every
other "confirmed coming, not yet specified" item on this roadmap. This subsection exists so that
when those decisions land, the shape of the work is already understood rather than re-derived,
and so that nothing built in the meantime (the Coach Pilot's schema in particular) has to be
reworked to make room for it.

**Shape of the eventual work, for when it's scoped for real:**

- **A tier/entitlement record, not a flag**: one row per account (singer or coach) with a tier,
  status, and renewal date — its own table (e.g. `Subscription`), not a column bolted onto
  `UserProfile`/`CoachProfile`. A growing ledger of tier *changes* (matching `ConsentRecord`'s
  append-only pattern) is worth considering too, since "when did this account upgrade/downgrade"
  is exactly the kind of question that comes up later and is expensive to reconstruct after the
  fact if only current state was ever stored.
- **One enforcement seam, reused everywhere a feature needs gating** — the same shape as
  `app/coach_auth.py`'s `require_coach_access`: a single dependency every tier-gated endpoint
  calls, so whichever features end up Free vs. Pro, the mechanism enforcing that boundary is
  already correct and tested before the business decision is even finalized.
- **A payment provider integration point.** Not chosen yet; Stripe is the default assumption
  worth validating when this is actually scoped (subscriptions, webhooks, and a customer portal
  for self-serve plan changes are all standard Stripe primitives that would otherwise be
  reinvented). Webhook handling needs to keep the `Subscription` table in sync with the
  provider's own source of truth for renewal/cancellation/payment-failure events — never trust
  client-reported subscription state for gating.
- **Open questions, founder's call, not decided here** (mirroring how Stage 12's own coach-pilot
  plan flagged its open questions rather than guessing): exact Free vs. User Pro feature
  boundary; whether Coach accounts have a Free tier or Coach Pro is the only option; monthly vs.
  annual and proration; trial periods; what happens to an active coach-singer connection
  (`CoachAccess`) if the coach's subscription lapses — does access pause, or does the singer keep
  what they had; whether a downgrade is immediate or takes effect at the end of a billing period.

### Deployment milestone (between Stage 11 and Stage 12)

The founder now has GitHub, Supabase, and Google Cloud accounts set up. Before Stage 12 begins,
and after Stage 11 ships:

- Move the database from local dev Postgres to Supabase (separate dev and prod projects).
- Set up a GitHub-based deploy workflow (CI running the existing test suites, then deploy).
- Prepare the app for Google Play submission (Android packaging — TWA/Capacitor from the
  existing Next.js PWA is the likely path, needs confirming — plus a Play Console listing).

This isn't a numbered "Stage" in the usual sense (no new user-facing feature, no PASS/FAIL test
plan against a product spec) — it's operational readiness work, and will get its own walkthrough
when we reach it rather than being scoped now.

## Development rule

At the end of every stage:

1. Stop development.
2. Run automated tests.
3. Run the manual test plan.
4. Produce a PASS/FAIL report.
5. Document bugs.
6. Fix critical bugs.
7. Update `README.md`.
8. Update `CHANGELOG.md`.
9. Update `ARCHITECTURE.md` if architecture changed.
10. Update `TESTING.md` with actual results.
11. Explain exactly how the founder can test the stage themselves.
12. **Wait for approval before beginning the next stage.**

## Guiding principles

- Accuracy before hype.
- Longitudinal data before diagnoses.
- Personal baseline before population assumptions.
- Safety before engagement.
- Measurement before AI.

## Initial success metric

Not "how many people downloaded VepAIr" — instead:

> Can VepAIr repeatedly measure meaningful changes in one person's voice and help that person
> follow a safe, structured training/recovery routine?

Only after proving that on the founder's own longitudinal data ("My Vocal Journey", see
`ARCHITECTURE.md`) should the product scale to more users.
