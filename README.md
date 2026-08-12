# VepAIr

**voice repair + AI** — an AI-assisted vocal recovery, conditioning, and performance platform.

> VepAIr learns an individual user's voice, establishes their personal vocal baseline, monitors
> how that voice changes over time, provides safe personalized exercises, measures progress,
> identifies potentially concerning changes, and helps singers protect, condition, and improve
> their voices.

VepAIr is **not** a medical diagnostic device. See [`MEDICAL_SAFETY.md`](MEDICAL_SAFETY.md).

## Project status

**Stage 11 — Progress Dashboard.** You can create an account, complete onboarding, log a daily
vocal check-in, see trend charts of your history, and record a guided voice sample session
(sustained vowels, hum, glide, a reading sentence, optional singing). Every recording is
automatically analyzed for F0, jitter, shimmer, HNR, and other acoustic measurements, plus a
0-100 recording quality score. Sustained-vowel recordings also build a personal vocal baseline
(robust median/MAD statistics, compared only against your own past recordings) with a
confidence indicator and anomaly detection for recordings that look notably different from your
recent normal. The dashboard shows a daily 0-100 **VepAIr Score** — a transparent, explainable
training/recovery indicator (not a medical score) with a tappable "why did I get this score?"
breakdown and a GREEN/YELLOW/RED daily status. A **Voice exercises** flow builds a 5/10/15/20
minute exercise routine adapted to today's recovery status, fatigue, recent vocal load, sleep,
and baseline deviations — drawn from a 23-exercise library across 12 categories — with reported
discomfort always capping the routine to the gentlest exercises and never recommending "pushing
through" it. Exercises with a vocal signal give **real-time coaching feedback** (pitch, volume,
onset, glide smoothness) entirely client-side via the Web Audio API. As of Stage 8, a **Vocal
range** flow maps your comfortable low/high/falsetto notes over time (piano-style
visualization, historical best, 30/90-day change), exercises with a measurable target are
analyzed and tracked for **improving/declining trends**, and the system gently **adapts to your
progress** — never overriding any safety rule, always subordinate to reported discomfort,
recovery status, and rest. As of Stage 9, you can choose a self-selected **Vocal Repair or Vocal
Improvement track** — once VepAIr has a recent voice sample and vocal-range test, it generates a
**90-day plan** specific to your own measured range, and automatically moves you from Repair to
Improvement once your recent data looks consistently stable (never framed as "healed," always
"consistently stable" — see [`MEDICAL_SAFETY.md`](MEDICAL_SAFETY.md)). As of Stage 10, after an
exercise session you can tap **Share My Progress** to generate two ready-to-post 1080×1920
images — today's snapshot and a start-vs-now comparison — built entirely from your own real
data, with missing metrics simply left out rather than invented. As of Stage 11, a **Progress**
page shows your VepAIr Score charted over any range up to all-time, your training streak and
consistency, and every exercise's current trend in one place. See
[`ROADMAP.md`](ROADMAP.md) for the full staged build plan and [`CHANGELOG.md`](CHANGELOG.md)
for what's shipped so far.

## Documentation

| File | Contents |
|---|---|
| [`USER_GUIDE.md`](USER_GUIDE.md) | Plain-English walkthrough of the app for people using it |
| [`FEATURES.md`](FEATURES.md) | Catalog of every feature — what it does and why, live vs. planned |
| [`TECHNICAL_GUIDE.md`](TECHNICAL_GUIDE.md) | Deployment/operations guide — GitHub, Vercel, Cloud Run, Supabase, and how they fit together |
| [`ROADMAP.md`](ROADMAP.md) | Stage-by-stage build plan and release grouping |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Repo structure, tech stack, data model, system diagram |
| [`TESTING.md`](TESTING.md) | Test pyramid, test plans, and actual results per stage |
| [`MEDICAL_SAFETY.md`](MEDICAL_SAFETY.md) | Binding rules on what VepAIr may and may not claim |
| [`PRIVACY.md`](PRIVACY.md) | Data handling, consent, and user rights requirements |
| [`CHANGELOG.md`](CHANGELOG.md) | What changed, stage by stage |
| [`docs/acoustic-measurements.md`](docs/acoustic-measurements.md) | Every voice measurement: definition, algorithm, units, limitations |
| [`docs/golden-voice-set.md`](docs/golden-voice-set.md) | The permanent synthetic audio regression fixtures |

## Repository layout

```
/vepair
  /apps/web         Next.js (TypeScript, Tailwind) frontend
  /apps/api         FastAPI (Python) backend
  /packages
    /audio-engine   Python DSP package (Parselmouth/Praat + librosa)
  /docs             Per-metric acoustic measurement documentation
  /tests            Cross-cutting integration/e2e tests
  /scripts          Dev environment setup scripts
  /data/fixtures    Golden Voice Set synthetic audio fixtures
```

## Prerequisites

- Node.js 20+ and npm
- Python 3.12+
- PostgreSQL 17 (or Docker, if you'd rather run everything in containers)

## Quickstart (Windows, no Docker)

```powershell
# One-time: creates the `vepair` Postgres role/database (a UAC prompt will appear once —
# approve it), installs backend + frontend deps, runs migrations.
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

Then, in two terminals:

```powershell
# Terminal 1 — backend
cd apps/api
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

```powershell
# Terminal 2 — frontend
cd apps/web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and sign up for an account — you'll land on
onboarding, then the dashboard. The old Stage 0 connectivity check now lives at
[http://localhost:3000/status](http://localhost:3000/status).

Password reset doesn't send a real email yet (no provider is configured) — the reset token is
printed to the `apps/api` server log instead. Look for a line like `Password reset requested for
<email> — token: <token>` and paste that token into the reset-password page.

Click **Record voice sample** on the dashboard (or go to `/record`) to try the guided recording
flow — it needs real microphone access (browser will prompt for permission). Each recording is
now automatically analyzed (F0, jitter, shimmer, HNR for sustained vowels/hum; a recording
quality score for everything) — the results show up on the session-complete screen. Recording
deletion isn't implemented yet, so anything you record stays around; see `PRIVACY.md`.

Click **Voice exercises** on the dashboard (or go to `/exercises`) to try the adaptive exercise
routine — pick a length (5/10/15/20 minutes) and walk through it. Exercises with a vocal signal
(anything except Breathing) request microphone access for real-time coaching feedback — pitch,
volume, onset, and glide smoothness, analyzed entirely in your browser, nothing uploaded. If you
deny or don't have a microphone, the routine still works fine without live feedback. `scripts/
setup.ps1` seeds the exercise library automatically; if you ever need to reseed it manually
(e.g. after editing `apps/api/app/exercise_library.py`), run:

```powershell
cd apps/api
.venv\Scripts\python.exe scripts\seed_exercises.py
```

Click **Vocal range** on the dashboard (or go to `/vocal-range`) to map your comfortable low,
high, and (optional) falsetto notes — needs microphone access, same as recording. If you already
have range data, the page shows your current summary directly instead of jumping into a new
test; use **Record a new range test** to add another data point.

If the Postgres service is ever stopped, restart it with (requires admin):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-db-start.ps1
```

## Quickstart (Docker)

```bash
docker compose up --build
```

This brings up Postgres (5432), the API (8000), and the web app (3000).
**Not exercised in this environment** (Docker wasn't installed here) — verify on a machine with
Docker before relying on it.

## Running tests

```powershell
cd apps/api
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
```

```powershell
cd packages/audio-engine
C:\Users\...\apps\api\.venv\Scripts\python.exe -m pytest tests\
```

```powershell
cd apps/web
npm run lint
npx tsc --noEmit
npm test
npm run build
```

## Environment variables

Never commit real secrets. Copy the example files and fill in real values:

- `apps/api/.env.example` → `apps/api/.env`
- `apps/web/.env.example` → `apps/web/.env.local`
