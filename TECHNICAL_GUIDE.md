# VepAIr Technical Guide

This is the operator's guide: how VepAIr is actually deployed, which cloud accounts it lives in,
how a code change gets from a local edit to the live app, and the gotchas that have already bitten
us once. For local development setup, see [`README.md`](README.md). For system design and data
model, see [`ARCHITECTURE.md`](ARCHITECTURE.md) — this document does not repeat either.

## 1. The four accounts and what each one owns

| Account | Owns | Console |
|---|---|---|
| **GitHub** | Source of truth for all code. Triggers Vercel's build automatically on push. | `https://github.com/Peteloaff/Vepair` |
| **Vercel** | Hosts the frontend (`apps/web`, Next.js). Auto-deploys on every push to `main`. | vercel.com dashboard, project `vepair/vepair` |
| **Google Cloud (Cloud Run)** | Hosts the backend (`apps/api`, FastAPI + `packages/audio-engine`). **Deploys manually** — pushing to GitHub does *not* redeploy it. | console.cloud.google.com, project `project-f0a451eb-7b60-43b9-b93` |
| **Supabase** | Hosts the production Postgres database and the private Storage bucket recordings live in. Auth is **not** here — see §4. | supabase.com dashboard, project `vepair-dev`, ref `hyuhszgtfcsaawmtbwzz` |

The single most important thing to understand about this setup: **the frontend and backend
deploy on two completely different triggers.** A `git push` updates the live frontend within a
couple of minutes automatically. It does **nothing** to the live backend — that needs a manual
`gcloud run deploy` every time `apps/api`, `packages/audio-engine`, or the root `Dockerfile`
changes. Forgetting this is the single most common way to ship a backend fix that "isn't showing
up" — it built and tested fine locally, it's sitting on `main`, but the running Cloud Run
container is still the old image.

## 2. GitHub

- Repo: `https://github.com/Peteloaff/Vepair.git`, single branch `main` used for both source of
  truth and the Vercel deploy trigger (no separate staging branch yet).
- GitHub itself does nothing beyond hosting the code and firing Vercel's webhook — there is no
  GitHub Actions CI configured. Tests are run manually (locally, or via a subagent) before a
  push, not gated automatically. If a CI pipeline gets added later, this is the file to update.
- Cloning into Google Cloud Shell (for backend deploys, see §3) has been a recurring friction
  point: GitHub deprecated password auth for git operations, so `git clone`/`git pull` inside
  Cloud Shell needs either a Personal Access Token or the repo to be public. **Never paste a
  real PAT into chat** — if one is ever accidentally exposed that way, revoke it immediately at
  github.com/settings/tokens and generate a new one. If token auth keeps failing and it's not
  worth fighting, temporarily making the repo public removes the auth requirement entirely for
  `git clone` (this was the actual workaround used the first time).

## 3. Google Cloud Run (backend)

- Project: `project-f0a451eb-7b60-43b9-b93` (project number `302841837670`).
- Service: `vepair-api`, region `us-west1`.
- Live URL: `https://vepair-api-302841837670.us-west1.run.app`.
- Deploys are run from **Cloud Shell** (browser-based, no local `gcloud` install currently), not
  from this machine. Standard deploy sequence:

```bash
cd ~/Vepair
git pull
gcloud run deploy vepair-api \
  --source . \
  --region us-west1 \
  --allow-unauthenticated \
  --port 8000 \
  --env-vars-file ~/env.yaml
```

- `--source .` builds from the **repo root**, not `apps/api` — this is required. See the
  Dockerfile-location gotcha in §6.
- `~/env.yaml` on Cloud Shell holds the production environment variables (database URL, JWT
  secret, Supabase keys, CORS origins, storage backend). It is not committed anywhere — it only
  exists in that Cloud Shell session's home directory. If Cloud Shell resets and wipes it,
  recreate it from `apps/api/.env.example`'s variable names with real production values.
- **To change a single env var without a full rebuild** (much faster — no image build, just a
  new revision with updated config), use `gcloud run services update` instead:

```bash
gcloud run services update vepair-api \
  --region us-west1 \
  --update-env-vars API_CORS_ORIGINS=https://vepair.vercel.app,https://vepair.com,https://www.vepair.com
```

- To read backend startup/runtime errors when something's wrong after a deploy:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=vepair-api" --limit 50
```

- A local `gcloud` CLI install (mirroring the local Vercel CLI setup) has been discussed but not
  yet done — currently all Cloud Run operations go through Cloud Shell.

## 4. Vercel (frontend)

- Project: `vepair/vepair` (there is also a stray, empty, unused project literally named `web`
  from an early `vercel link` mistake — harmless, zero traffic, safe to delete manually from the
  Vercel dashboard whenever, not urgent).
- Production domains: `https://vepair.com` and `https://www.vepair.com` (custom domain, added
  via `vercel domains add`, DNS hosted at GoDaddy — see below) plus the original
  `https://vepair.vercel.app`, which still works and doesn't need to be removed.
- **Custom domain DNS**: `vepair.com` is registered at GoDaddy but keeps GoDaddy's default
  nameservers (`ns13`/`ns14.domaincontrol.com`) rather than switching to Vercel's — simpler, and
  avoids handing over DNS for the whole domain just to serve one subdomain from Vercel. Two `A`
  records on `@` point it at Vercel's edge network:

  | Type | Name | Value |
  |---|---|---|
  | A | `@` | `216.150.1.1` |
  | A | `@` | `216.150.16.1` |
  | A | `www` | (same two values, or Vercel's suggested CNAME target) |

  Verify a domain's config any time with `vercel domains inspect <domain>` (shows current vs.
  recommended records) or `vercel domains verify <domain>` (re-checks and flips status once DNS
  propagates). Vercel auto-provisions SSL once verification passes — no separate certificate
  step.
- **Whenever a new domain is added here, it must also be added to the backend's
  `API_CORS_ORIGINS` on Cloud Run** (see §6) — otherwise signup/login on that domain fails with
  a CORS error even though the domain itself loads fine.
- **Deploys automatically** on every push to `main` via the GitHub integration — no manual step
  needed for frontend-only changes.
- Local Vercel CLI is installed and linked to this project. Useful commands, always run from the
  **repo root** (not `apps/web` — the project's "Root Directory" setting is `apps/web` already,
  and running the CLI from inside `apps/web` double-nests the path and fails):

```bash
vercel env ls production                          # see what's currently set
printf '%s' "https://vepair-api-...run.app" | vercel env add NEXT_PUBLIC_API_URL production
printf '%s' "https://vepair-api-...run.app" | vercel env add API_URL production
```

- **`NEXT_PUBLIC_*` variables are baked into the client bundle at build time.** Changing one in
  the dashboard or via CLI does nothing to an already-built deployment — it only takes effect on
  the *next* build. If you change one and need it live immediately without another code change,
  trigger an empty commit to force a rebuild:

```bash
git commit --allow-empty -m "Trigger Vercel rebuild to pick up updated env vars"
git push
```

- The Vercel CLI's free-tier upload limit (`api-upload-free`, 5000/24h) no longer applies — the
  account is now on Vercel Pro.

## 5. Supabase (database + storage)

- Project: `vepair-dev`, ref `hyuhszgtfcsaawmtbwzz`, region `us-west-2`.
- URL: `https://hyuhszgtfcsaawmtbwzz.supabase.co`.
- **Two separate roles, don't conflate them:**
  1. **Postgres database** — the actual `DATABASE_URL` the backend connects to for everything
     (users, recordings metadata, check-ins, scores, plans — all of it). Use the **Session
     pooler** connection string on **port 5432** (not port 6543, which is the transaction
     pooler and is the wrong one for this backend's connection pattern).
  2. **Storage** — a private bucket named `recordings` (`public = false`) that holds the actual
     recorded audio files, used only when `STORAGE_BACKEND=supabase`. Recordings are **never**
     served directly from Supabase's own URLs — the backend always reads/writes with the secret
     (service role) key, and the only way a client ever gets audio bytes back is through the
     backend's own authenticated, ownership-checked endpoint
     (`GET /api/v1/recordings/{id}/audio`). This is deliberate — see `PRIVACY.md`'s "no
     public-by-guessable-URL storage" rule. Don't ever flip the bucket to public.
- **Auth is explicitly not here.** VepAIr uses its own self-hosted email/password + JWT system
  (see `ARCHITECTURE.md` §6a), not Supabase Auth, even though the User table's id format mirrors
  what Supabase Auth would produce (a deliberate swap-point for later, not a current dependency).
- API keys live under **Project Settings → API Keys** (not "General") — the newer key system
  uses **Publishable key** (`sb_publishable_...`, client-safe) and **Secret key**
  (`sb_secret_...`, server-only, maps to `SUPABASE_SERVICE_ROLE_KEY`). Never put the secret key
  anywhere client-facing (Vercel's `NEXT_PUBLIC_*` vars, frontend code, etc.) — it bypasses row
  security and is meant for the backend only.
- Migrations run via Alembic against this database from wherever the backend is being deployed
  from (currently Cloud Shell, as part of the Cloud Run deploy flow, or locally against a local
  Postgres for dev). There's no separate CI migration step yet.

## 6. Known gotchas (already hit once — don't rediscover these)

- **`gcloud logging read --format="value(textPayload)"` misses all application-level log
  lines.** `app/logging_config.py`'s `JsonFormatter` prints every `logger.*()` call as a JSON
  string on stdout; Cloud Logging auto-detects that and files it under `jsonPayload`, not
  `textPayload`. Only uvicorn's own access logs (`INFO:     GET /path HTTP/1.1 200 OK`) are
  plain text. Filtering on `jsonPayload.logger="<name>"` and reading `jsonPayload.message` is
  the only way to see anything `app/email.py`, `app/admin_audit.py`, etc. actually logged — this
  cost real time diagnosing a "Graph email isn't working" report that turned out not to be a bug
  at all (see the next item).
- **Microsoft Graph `sendMail` returning `202` does not mean the email was delivered.** A `202`
  only means Graph *accepted the request for processing* — Exchange Online's own outbound
  protection can still silently drop the message afterward, with nothing logged on our side
  (there's no success-path log line in `app/email.py`, only a fallback line and a failure line —
  see below) and no error surfaced to the caller. Diagnosed 2026-08-14 by testing delivery to two
  independent providers (Gmail and a disposable mail.tm inbox) — zero delivery to either, which
  ruled out "Gmail is just filtering a new domain" and pointed at something on Microsoft's side
  instead of DNS or app config.
- **The actual cause, found via Message Trace: `550 5.7.708 Access denied, traffic not accepted
  from this IP`** — Exchange Online's own outbound anti-abuse protection had restricted the
  tenant/mailbox from sending, most likely triggered by the burst of near-identical automated
  "password reset" test emails sent in rapid succession from a brand-new, low-reputation tenant
  during this very debugging session. Not a DNS issue (SPF/DKIM/DMARC were all confirmed
  correctly configured before this was found) and not a code/Azure-permission bug. Check
  `security.microsoft.com/restrictedentities` first (self-service unblock if the mailbox is
  listed); if not listed, it's a tenant-wide throttle and needs a Microsoft support ticket
  (Admin Center → Help & support → New service request, referencing the NDR and `5.7.708`) — see
  ticket `#2608140040004549`, filed 2026-08-14, for precedent if this recurs.
- **Message Trace works far better filtered by recipient than by sender.** Searching by sender
  (`noreply@vepair.com`) in the Exchange admin center's classic message trace errored with an
  unrelated-looking "Sender validation failed: Invalid email address" — a red herring. The modern
  `security.microsoft.com` trace, searched by **recipient** address instead, is what actually
  surfaced the real `5.7.708` NDR.
- **`gcloud logging read --format="value(textPayload)"` misses all application-level log
  lines** — `app/logging_config.py`'s `JsonFormatter` prints every `logger.*()` call as JSON on
  stdout; Cloud Logging files that under `jsonPayload`, not `textPayload`. Only uvicorn's own
  access logs are plain text. Filter on `jsonPayload.logger="<name>"` and read
  `jsonPayload.message` instead — and always scope with `--freshness` when testing something
  live, since an old matching log line (e.g. a stale `[email:log]` entry from before
  `EMAIL_BACKEND=graph` was ever set) can look like current signal otherwise.
- **Dockerfile must live at the repo root, not `apps/api/`.** `gcloud run deploy --source .`
  only auto-detects a Dockerfile build when a file literally named `Dockerfile` sits at the root
  of `--source`; anywhere else it silently falls back to Buildpacks, which can't handle a
  monorepo with both a Python backend and a Next.js frontend present. This is also *why* the
  Dockerfile is at the root and not next to `apps/api`: `apps/api` depends on the sibling
  `packages/audio-engine` package (not published anywhere, so it must be in the same build
  context), and root is the only location where both are reachable.
- **Alembic + `%` in the database password.** Python's `configparser` (which backs Alembic's
  `Config` object) treats a bare `%` as string-interpolation syntax. A URL-encoded password
  character like `%40` (`@`) crashes `config.set_main_option` unless escaped as `%%` first — see
  `apps/api/migrations/env.py`.
- **CORS must explicitly list the live frontend origin.** `API_CORS_ORIGINS` defaults to
  `http://localhost:3000` and does not include the production Vercel domain unless it's
  explicitly set. If it's missing, every POST from the live frontend (signup, login, refresh —
  anything that triggers a CORS preflight) fails in the browser with a generic-looking error,
  even though the backend itself is completely healthy and reachable directly (e.g. via `curl`
  or a script). If real users report "can't sign up" or "can't sign in" on the live app, check
  the browser console for a CORS error *before* assuming it's an auth/DB bug — this exact
  scenario has happened. Fix:

```bash
gcloud run services update vepair-api --region us-west1 --update-env-vars API_CORS_ORIGINS=https://vepair.vercel.app,https://vepair.com,https://www.vepair.com
```

- **`STORAGE_BACKEND=local` does not survive Cloud Run.** Cloud Run containers are ephemeral —
  local disk is wiped on every restart/redeploy. Production must run
  `STORAGE_BACKEND=supabase`; `local` is fine only for local dev.
- **`vercel` CLI must be run from the repo root**, not from inside `apps/web` — the project's
  Root Directory setting (`apps/web`) is layered on top of wherever the CLI is invoked from, so
  running it from inside `apps/web` looks for `apps/web/apps/web` and fails.

## 7. Making a change end to end

**Frontend-only change** (anything in `apps/web`):
1. Edit, test locally (`npm run lint && npx tsc --noEmit && npm test && npm run build`).
2. Commit and push to `main`.
3. Done — Vercel picks it up automatically. Check the Vercel dashboard for build status if
   unsure.

**Backend change** (anything in `apps/api` or `packages/audio-engine`):
1. Edit, test locally (`pytest`, `ruff check .` from `apps/api`; `pytest` from
   `packages/audio-engine`).
2. Commit and push to `main`.
3. **Manually redeploy** — open Cloud Shell, run the deploy sequence in §3. This is the step
   that's easy to forget since the frontend half "just works" on push.

**Database schema change** (a new Alembic migration):
1. Generate/write the migration locally, test against local Postgres.
2. It ships as part of the normal backend deploy (`gcloud run deploy --source .` from §3) —
   there's no separate migration-only step; the deploy process (or whatever entrypoint runs
   `alembic upgrade head`) applies it against the same Supabase Postgres the backend connects
   to. Double-check this actually runs before relying on it silently happening — verify with a
   direct query against Supabase after deploying if it's a schema change you care about.

## 8. Direct database access (diagnostics)

For diagnosing live issues (e.g. "does this user actually have an account"), connect directly to
the production Supabase Postgres database with the Session pooler connection string:

```
postgresql+psycopg://postgres.hyuhszgtfcsaawmtbwzz:<password>@aws-0-us-west-2.pooler.supabase.com:5432/postgres
```

This has been useful for confirming real bug reports against real production data rather than
guessing — e.g. confirming a "can't sign in" report was actually "never signed up" by querying
the `users` table directly, or confirming a "missing plan" report was correctly-behaving (missing
prerequisite data) rather than a bug. Treat this connection string like any other production
credential — never commit it, never log it.

## 9. Bootstrapping the first admin

The backend admin section (`/admin` in the frontend, `/api/v1/admin/*` in the backend — see
`ARCHITECTURE.md` §6o) has no self-serve path to grant admin access, ever, by design. The *very
first* admin still requires a one-time manual UPDATE against the production database, using the
same §8 connection, since there is by definition no existing admin yet to grant it through the
UI:

```sql
UPDATE users SET is_admin = true WHERE email = '<founder email>';
```

Run this once for the founder's own account after the admin migration has been deployed. There is
no "list current admins" UI — if that's ever needed, query `users WHERE is_admin = true` directly.

Once at least one admin exists, granting or revoking admin (and coach) access for *other*
accounts goes through the UI itself — on a user's detail page (`/admin/users/{id}`), the "Roles"
section has "Grant admin"/"Revoke admin" and "Make coach"/"Remove coach" controls
(`POST /api/v1/admin/users/{id}/set-admin` / `.../set-coach`). An admin can't target their own
account with either (self-lockout prevention) — only this manual SQL path can recover from
"every admin account got revoked/deactivated," which is exactly why it stays documented here
rather than being fully replaced by the UI.

## 10. Coach billing — activating Coach Pro

Every coach account belongs to an `Organization` (one per coach, created automatically at
signup — see `ARCHITECTURE.md` §4/§6o for the data model). Each org has an `is_coach_pro_active`
flag that defaults to **false**: there is no free coach tier, so a brand-new coach account is
locked out of the entire Coach Portal (dashboard, invites, assignments, notes — every coach
endpoint) the moment they sign up, with a "Your account is pending activation" message on their
home page. This is expected, not a bug — see `ROADMAP.md`'s "Subscription tiers / paywall"
section for why the model has no free coach tier.

There is **no Stripe on the coach side**. Coach payment (the base subscription fee, and any
invite overage past the 50 included per year) goes through QuickBooks and is collected outside
the app — see `ROADMAP.md`'s "QuickBooks Online monthly invoicing sync" section. That sync job
isn't built yet (it needs the founder's Intuit Developer app registered first), so today
activation is a manual switch you flip once you've confirmed payment yourself:

1. Log in as an admin.
2. Go to `/admin` → **Organizations**.
3. Search by org name, coach email, or coach name (empty search lists the 100 most recent).
4. Click into the org.
5. Click **Activate Coach Pro**.

This sets a 12-month period from that moment (`coach_pro_period_start`/`coach_pro_period_end`)
and unblocks the coach's account immediately — no redeploy needed, and the coach doesn't need to
log out/in. The same page has **Deactivate Coach Pro** to pull access back (e.g. non-payment,
lapsed renewal) — this only locks the coach out of the Coach Portal; it never touches their own
account data or any singer's data.

The detail page also shows invites used this period vs. the 50 included. Going over 50 doesn't
block sending more invites — it's meant to accrue as overage that bills on the org's next
QuickBooks invoice once that sync exists. Until then, overage just displays; nothing invoices
automatically.

Equivalent API call, if driving this from a script rather than the UI (admin token required):

```bash
curl -X POST "$API_URL/api/v1/admin/organizations/<org_id>/set-coach-pro" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"is_coach_pro_active": true}'
```

## 11. Practice reminders — Cloud Scheduler setup

`POST /api/v1/system/send-reminders` sends the "How's your voice today?" email to every singer
who hasn't checked in yet today and has notifications consent granted (see
`apps/api/app/reminders.py`). Nothing calls this automatically — it's meant to be triggered once
daily by **Google Cloud Scheduler**, which doesn't exist yet as of this writing and needs to be
created once, in the same GCP project as Cloud Run (§3).

This endpoint is **not** protected by a user JWT — a 15-minute admin access token is the wrong
credential for something an unattended job calls once a day with no one signed in. Instead it
checks a shared secret header (`X-Internal-Job-Secret`) against the `INTERNAL_JOB_SECRET` env
var, which defaults to empty and rejects every call until set — so this must be added to
`~/env.yaml` (§3) before the scheduler job is created:

```bash
INTERNAL_JOB_SECRET: "<a long random string, e.g. `openssl rand -hex 32`>"
```

Then, from Cloud Shell (same place Cloud Run deploys run from), create the scheduler job once:

```bash
gcloud scheduler jobs create http vepair-send-reminders \
  --location us-west1 \
  --schedule "0 18 * * *" \
  --time-zone "America/Chicago" \
  --uri "https://vepair-api-302841837670.us-west1.run.app/api/v1/system/send-reminders" \
  --http-method POST \
  --headers "X-Internal-Job-Secret=<same value as INTERNAL_JOB_SECRET above>"
```

- `--schedule "0 18 * * *"` is 6pm daily — adjust the cron expression or `--time-zone` as
  desired; nothing about the endpoint assumes this exact time.
- Safe to trigger more than once in a day — `app/reminders.py`'s `NotificationLog` unique
  constraint means a second call the same day sends nothing further (see its module docstring).
- To change the schedule or secret later: `gcloud scheduler jobs update http
  vepair-send-reminders --location us-west1 ...` with the flags you want to change.
- To test the job immediately without waiting for its schedule:
  `gcloud scheduler jobs run vepair-send-reminders --location us-west1`.
- To check what it actually sent: `gcloud logging read` (§3) filtered to `vepair-api`, or query
  `notification_logs` directly (§8) for today's rows.
