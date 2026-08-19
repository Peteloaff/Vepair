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

### Subscription tiers / paywall (pricing decided 2026-08-19, not yet built)

**Founder confirmed directly (2026-08-13): a paid tier is coming for the consumer app, not just
for VepAIr Coach.** Until then, every monetization plan on this roadmap was B2B — VepAIr Coach's
own Phase III–V pricing above is coaches/studios paying for the coach portal. This is a
**second, separate axis**: individual accounts (both singers and coaches) get Free vs. Pro tiers
on the consumer/coach-pilot product itself. As of 2026-08-19 the founder made the feature-boundary
and business-model calls below; nothing has been built yet — no schema, no billing integration,
no gating code — this section still documents scope, not shipped work, per the standing rule that
nothing gets built until real pricing decisions exist. What changed is that those decisions now
exist and are recorded here so they aren't re-derived or re-litigated later.

**Decided:**

- **Three tiers**: **Free**, **User Pro** (paid singer tier), **Coach Pro** (paid coach tier).
- **Feature boundary**: Free covers tracking — check-ins, recordings, and history stay available
  with no card on file, forever. User Pro is required for the "AI coaching" surface: live
  coaching feedback during exercises, the adaptive daily routine, Goal Tones, and Recovery Score
  insights. (Exact endpoint-by-endpoint gating list still needs to be drawn up when this is
  actually built — this is the boundary, not yet the implementation checklist.)
- **No free Coach tier.** `coach_pro` is required from signup to use any coach feature at all —
  inviting a singer, viewing a dashboard, everything. There is no capped free-coach state to
  design around.
- **Billing cadence**: both monthly and annual, with an annual discount. Two Stripe price points
  per paid tier, not one.
- **Trial**: a 7-day free trial of the paid tier, one-time per account (not repeatable by
  clearing/re-subscribing on the same account). No card-required gate before the trial starts is
  assumed unless payment-provider constraints force one when this is actually built. A trial that
  ends without conversion drops the account to Free (tracking-only), not to zero access.
- **Lapsed `CoachAccess` on a lapsed coach subscription**: access pauses immediately. The coach
  loses the ability to view singer data or send new notes the moment `coach_pro` lapses; existing
  `CoachNote` rows and the connection itself aren't deleted, just inaccessible to the coach until
  they resubscribe. A singer's own data is never affected by their coach's subscription state.
- **Downgrade/cancellation timing**: takes effect at the end of the current billing period, not
  immediately — standard Stripe pattern. The account keeps paid-tier access through whatever
  they already paid for, then reverts to Free (or loses coach access entirely, for a lapsed
  `coach_pro`) at `current_period_end`.

**Shape of the eventual work, for when building actually starts:**

- **A tier/entitlement record, not a flag**: one row per account (singer or coach) with a tier,
  status, and renewal date — its own table (`Subscription`), not a column bolted onto
  `UserProfile`/`CoachProfile`. An append-only `SubscriptionEvent` ledger (matching
  `ConsentRecord`'s pattern) for upgrade/downgrade/cancel/renew, since "when did this account's
  tier change and why" is exactly the kind of question that's expensive to reconstruct later if
  only current state was ever stored.
- **One enforcement seam, reused everywhere a feature needs gating** — the same shape as
  `app/coach_auth.py`'s `require_coach_access`: `app/subscription_auth.py`'s `require_tier(min_tier)`,
  a single dependency every tier-gated endpoint calls.
- **Stripe as the payment provider** (subscriptions, webhooks, and a hosted customer portal for
  self-serve plan changes/cancellation, rather than building that UI from scratch). A
  `POST /api/v1/billing/webhook` keeps `Subscription` in sync with Stripe's own event stream
  (`checkout.session.completed`, `customer.subscription.updated/deleted`,
  `invoice.payment_failed`) — the webhook is the source of truth; client-reported subscription
  state is never trusted for gating.
- **Still open when this is actually scoped for real**: exact endpoint-by-endpoint gating list
  for what counts as "AI coaching" (live coaching, adaptive routine, Goal Tones, Recovery Score —
  confirm each surfaces individually or as one bundled unlock); exact User Pro / Coach Pro price
  points; whether the 7-day trial requires a card up front or not, which depends on what Stripe's
  trial primitives make easiest.

### Coach organizations & invite quota (decided 2026-08-19, not yet built)

A second piece of the coach monetization model, decided alongside the subscription tiers above.
Not built yet — same rule as everything else in this section.

**Decided:**

- **A new `Organization` entity, one per coach, always.** Not a multi-coach tenant (no org with
  several coach logins under it, no owner/member roles to design) — it formalizes what
  `CoachProfile.studio_name` is today (a free-text label) into a real record with its own id,
  billing fields, and invite pool. `CoachProfile` gets a foreign key to it. The 1:1 constraint is
  deliberate for now, not an oversight — if a real multi-coach studio need shows up later, the
  entity already exists to loosen that constraint against, rather than retrofitting a tenant
  concept onto `CoachProfile` after the fact.
- **The 50-invite quota lives on `Organization`, not on `CoachProfile` directly** — same
  forward-compatibility reasoning: even though it's always exactly one coach's pool today,
  metering against the org record rather than the user record means nothing has to move later.
- **Every `Organization` gets 50 coach-invites (`CoachInvite` rows) included per year of the
  `coach_pro` subscription** — an annual allowance, not a lifetime one-time grant and not a
  monthly reset. The pay-per-invite model stacks with `coach_pro`, it doesn't replace it: a coach
  still needs an active subscription to use coach features at all, and the invite quota is a
  second, independent dimension on top.
- **A declined or revoked `CoachInvite` frees its unit back up** — the org's remaining quota for
  the year goes back up by one, it isn't permanently consumed just because an invite didn't lead
  to a connection.
- **Resending an invite to the same email does not consume a second unit.**
- **Going over 50 in a given year bills automatically, per invite, as a line item on the coach's
  next invoice** — there's no separate "buy a block of additional licenses" purchase path;
  "license" and "invite" are the same unit, and exceeding the included 50 is metered overage, not
  a manual top-up a coach has to remember to buy. Exact per-invite overage price not yet set —
  same "confirmed coming, not yet specified" status as the base tier prices above.

**Still open, worth nailing down before this is built:** the exact per-invite overage price
(pure pricing decision, same status as the base tier prices above).

**Resolved (2026-08-19), superseding the Stripe-modeling concern this section originally raised**:
overage doesn't get billed through Stripe's metered/usage-based billing at all — see "QuickBooks
Online monthly invoicing sync" immediately below. Stripe's job (once it exists) is limited to
collecting the recurring `coach_pro`/`user_pro` subscription charge itself; the variable
per-organization invite/license overage is computed by VepAIr and handed to QuickBooks as a
draft invoice, not metered inside Stripe. This sidesteps the annual-allowance-vs-monthly-overage
billing-interval mismatch entirely, rather than solving it inside Stripe.

### QuickBooks Online monthly invoicing sync (decided 2026-08-19, not yet built)

**Founder's call: invoicing for the license/invite overage isn't automated through Stripe at
all — VepAIr computes the numbers, QuickBooks Online is where the actual invoice gets created
and sent.** Not built yet, same rule as everything else in this section.

**Decided:**

- **QuickBooks Online**, not QuickBooks Desktop — QBO has a real REST API (Intuit Developer
  platform, OAuth2), so a scheduled backend job can call it directly. Desktop has no equivalent;
  it would need Intuit's older Web Connector running as an agent on a machine with QuickBooks
  Desktop installed, a materially different and more fragile architecture. Ruled out.
- **A monthly scheduled job, once per organization**, computes that org's current license count
  and creates a **draft Invoice in QuickBooks Online** — not sent automatically. The founder
  reviews it in QuickBooks and sends it themselves. VepAIr is the data source, QuickBooks is the
  invoicing system of record; nothing about actually collecting payment or emailing an invoice to
  a coach happens inside VepAIr for this piece.
- The line item(s) on that draft invoice reflect **new/removed licenses for the period** — i.e.
  the invite-quota accounting already decided above (revoked invites free their unit, resends
  don't cost a unit), rolled up into whatever net count changed since the last sync.

**Still open, worth nailing down before this is built:**

- **How an `Organization` maps to a QuickBooks Customer.** QBO invoices are created against a
  `Customer` object on Intuit's side — does VepAIr auto-create a matching QBO Customer the first
  time an organization needs a draft invoice, or does the founder manually match/link each
  `Organization` to an existing QBO Customer record once, with VepAIr storing that mapping
  (e.g. `Organization.quickbooks_customer_id`)?
- **Whether this draft invoice covers only the overage/license line items, or also restates the
  base `coach_pro` subscription fee as its own line.** If the base subscription fee is still
  meant to be charged automatically via Stripe (as scoped earlier in this document), the
  QuickBooks draft invoice should probably show *only* the variable license overage, to avoid
  double-billing the base fee through two different systems. Worth confirming explicitly rather
  than assumed, since "we can do the invoicing ourselves" could also mean the founder wants *all*
  coach billing — base fee included — to move through QuickBooks instead of Stripe's automated
  recurring charge. That's a bigger scope difference (it would mean `coach_pro` isn't
  Stripe-auto-billed at all) and hasn't been explicitly confirmed either way yet.
- The OAuth connection itself: QuickBooks Online API access requires the founder to
  authorize VepAIr's backend against their specific QBO company file once (standard OAuth2
  consent flow) — a one-time manual setup step, not something to design further until this is
  actually built.

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
