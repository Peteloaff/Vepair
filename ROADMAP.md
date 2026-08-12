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
| 12 | VepAIr Coach (Professional SaaS for vocal coaches/studios) | ⚪ Not started — high-level phases scoped below from the founder's monetization strategy doc; detailed design deferred until Stage 11 is beta-tested |

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
   test whether they actually use it.
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

### Internal admin backend (founder's operational tooling — confirmed need, new)

Distinct from the VepAIr Coach portal above (which is for external vocal coaches/studios): the
founder needs an internal, GUI admin backend for running the business — user administration,
data pulls for contact lists, and reporting. Not a customer-facing feature, but grouped into
Stage 12 because it depends on the same foundation that stage already has to build (role-based
access beyond today's single "user" role; audit logging for who accessed what).

To be scoped in detail when Stage 12 is reached, but the shape is already clear:

- **Admin auth**: a real admin role, not a flag on the existing `User` model — this is the first
  actual consumer of `PRIVACY.md` §4's "auditable access" commitment (every non-owner read of a
  user's data attributable to a specific actor and reason), so that requirement needs to land for
  real here, not stay aspirational.
- **User administration**: search/view/manage accounts for support (password resets, account
  issues) — scoped access for a specific task, not unrestricted bulk data access by default.
- **Reporting**: aggregate business/usage metrics (signups, retention, engagement) — the kind of
  data `PRIVACY.md`'s existing "product analytics consent" purpose already anticipates.
- **Contact list / data export for outreach — needs a privacy decision before it's built, not
  just an engineering task**: `PRIVACY.md` §3's consent model currently covers product analytics,
  model training, and vocal-professional sharing — it does not cover marketing/outreach contact
  use. Pulling emails to build contact lists is a distinct purpose from those three and likely
  needs its own explicit consent grant (or at minimum a clear opt-out) rather than assuming every
  registered user is contactable for outreach by default. `PRIVACY.md` should be updated with
  that decision before this ships, not worked around in code.

Same non-negotiables as the rest of Stage 12 apply here: no clinical/diagnostic data exposure,
audit-logged access, never a shortcut around the consent model.

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
