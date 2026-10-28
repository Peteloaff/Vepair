# VepAIr to-do

What is left to do, scoped. Updated 2026-10-28. Sizes are rough: **S** = under a day,
**M** = a few days, **L** = a week or more. "Blocked" means a decision or an account is needed
from Pete before any code is written. Finished work lives in `CHANGELOG.md` and the Technical
Reference's "Live in production" list; the long-form decisions behind billing are in
`ROADMAP.md`.

## 1. Waiting on Pete (no code needed)

- [x] **Real iPhone check**: logo, icons, home-screen install and audio all work on a real
      iPhone. Confirmed by Pete 2026-10-28.
- [x] **Confirm assigned exercises**: John's assignment shows on Home under "Assigned by your
      coach" for pete@vepair.com. Confirmed by Pete 2026-10-28.
- [x] **Try the Team page for real**: added a coach with a real email and the set-your-password
      email arrived. Confirmed by Pete 2026-10-28.
- [x] **Admin accounts**: pete@vepair.com is the main admin and pete@abc.com is a demo account.
      Sorted out by Pete 2026-10-28.
- [ ] **Decide when to remove the "beta" tag**: one line, `SHOW_BETA_BADGE` in
      `apps/web/src/components/TopNav.tsx`.

## 2. Small, ready to build (S)

All five items below were built and deployed on 2026-10-28.

- [x] **Edit the organization name**: today a clinic's name is set once at signup and can't be
      changed by its admin. Add it to the Team page (and the admin console).
- [x] **Nicer set-your-password page for new team members**: `/reset-password` still says "Enter
      the reset token" with a developer hint. Hide the token field and hint when the token is
      already in the link, and use "Choose your password" wording.
- [x] **Add an existing account to a team** (admin console only): today adding an email that
      already has an account is refused. Needs a deliberate rule about what happens to that
      person's own data and singer connections.
- [x] **Refresh the Getting Started guide**: it predates Assigned exercises and Teams. Add a
      screenshot and short section for each, rebuild the PDF and the shared page.
- [x] **Refresh stale docs**: `FEATURES.md` "Planned" table still lists built things (coach
      portal, recording deletion, reset emails); `ROADMAP.md` stage table and "Coach
      organizations" section describe the old one-coach-per-org design; `CHANGELOG.md` needs the
      post-Stage-12 work (redesign, equipment prompts, invites by email, demo data, teams,
      assigned exercises).

## 3. Medium builds (M)

- [x] **Automate the backend deploy**: a GitHub Action (`.github/workflows/ci-cd.yml`) runs the
      tests and then deploys to Cloud Run on a push to `main`, using Workload Identity Federation
      (no keys in the repo). Set up and verified with a real deploy 2026-10-28.
- [x] **CI on every branch**: pytest, ruff, `tsc`, `eslint`, vitest and `npm run build` run on
      every push. Same workflow as above. Live 2026-10-28.
- [x] **Coach leaves a team**: built on `feature/org-vrotege-management` (2026-10-28), with remove-
      from-team, org-admin Vrotégé connections (invite for a coach, move, end connection).
      Deployed 2026-10-28.
- [x] **Org-level reporting for admins**: built on `feature/org-reporting` (2026-10-28): a Team
      activity table on the Team page, counts only, practice figures hidden below 3 sharing
      Vrotégés. Ticked as deployed once that branch ships.
- [ ] **Google Play packaging**: wrap the PWA (TWA or Capacitor, to be confirmed), Play Console
      listing, store assets. Needs a Play developer account. The iPhone/App Store equivalent
      would be a separate decision.

## 4. Big, blocked on decisions (L)

These come from `ROADMAP.md`. None has any code yet.

- [ ] **Singer paywall (Free / User Pro)**: a `Subscription` table, a `require_tier` gate on the
      "AI coaching" features (live coaching, adaptive routine, Goal Tones, Recovery Score
      insights), a webhook, and a self-serve manage/cancel screen.
      **Blocked on**: User Pro price points; whether the 7-day trial needs a card; confirming Square
      is still the provider (the roadmap chose it in 2026-09 for its QuickBooks link, but its
      subscription-management screens are thinner than Stripe's); the exact list of gated
      endpoints.
- [ ] **QuickBooks monthly invoice sync (coach overage)**: a monthly job that drafts an invoice
      per organization in QuickBooks Online. **Blocked on**: the per-invite overage price; how an
      organization maps to a QuickBooks customer; whether the draft shows only overage or also the
      base Coach Pro fee (the code and docs currently say all coach billing is manual through
      QuickBooks, which contradicts the Square plan in the roadmap); a one-time QuickBooks OAuth
      authorization by Pete.
- [ ] **Studio features beyond teams** (roadmap "Phase IV"): seat-based billing and
      organization-wide reporting. Teams gives the structure; pricing is the open question.
- [ ] **Cross-user Tone Match leaderboard**: scoped but unscheduled. Needs a privacy decision
      first, since Tone Match results are private today.

## 5. Backlog (deliberately not scheduled)

- Computer Vision Coach and Wearables + Vocal Load (deprioritized; revisit only if they become a
  priority).
- Anything clinical or regulatory is permanently out of scope, not deferred.

## How this list is used

Work is built on a feature branch, tested, pushed, and merged to `main` only when Pete says
"merge and deploy". After a deploy is confirmed, the feature is added to the Technical
Reference's "Live in production" list and ticked off here.
