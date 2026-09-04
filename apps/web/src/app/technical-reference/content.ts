// Self-contained HTML document rendered inside an isolated <iframe srcDoc> on the
// matching page.tsx -- keeps this document's own CSS (:root tokens, resets like
// `* { box-sizing }` and `a { color: inherit }`) from ever touching the app shell's
// TopNav/footer that also render on that page, and vice versa. Content originates from
// the published VepAIr artifact of the same name; kept in sync by hand.
export const TECHNICAL_REFERENCE_HTML = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VepAIr Technical Reference</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  /* Always dark -- matches the rest of the VepAIr app, which has no theme toggle. */
  :root {
    --ink: #0a0e13; --surface: #121922; --surface-2: #1a2430; --line: #29394a;
    --text: #e6edf4; --text-dim: #9fb1c2; --text-faint: #61748a;
    --accent: #4fd1c5; --accent-strong: #7ee0d6; --accent-ink: #04211d;
    --accent-soft-bg: rgba(79, 209, 197, 0.12);
    --danger: #f87171; --danger-soft-bg: rgba(248, 113, 113, 0.1);
    --ok: #34d399; --ok-soft-bg: rgba(52, 211, 153, 0.1);
    --warn: #f2b134; --warn-soft-bg: rgba(242, 177, 52, 0.1);
  }

  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0; background: var(--ink); color: var(--text);
    font-family: "IBM Plex Sans", -apple-system, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6; -webkit-font-smoothing: antialiased;
  }
  code, .mono, .path { font-family: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
  a { color: var(--accent); }
  a.quiet { color: inherit; text-decoration: none; }
  ::selection { background: var(--accent-soft-bg); }

  .shell { max-width: 1220px; margin: 0 auto; padding: 0 24px; }

  .masthead { border-bottom: 1px solid var(--line); padding: 30px 0; }
  .masthead-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .brand { display: flex; align-items: center; gap: 10px; }
  .brand-mark {
    width: 30px; height: 30px; border-radius: 7px; background: var(--surface-2); border: 1px solid var(--line);
    display: flex; align-items: center; justify-content: center; font-size: 13px; flex: none; color: var(--accent);
    font-family: "IBM Plex Mono", monospace; font-weight: 700;
  }
  .brand-name { font-weight: 700; font-size: 17px; letter-spacing: -0.01em; }
  .eyebrow {
    text-transform: uppercase; letter-spacing: 0.11em; font-size: 11px; color: var(--accent); font-weight: 700;
    background: var(--accent-soft-bg); padding: 3px 9px; border-radius: 999px;
  }
  h1.title { margin: 14px 0 0; font-size: clamp(28px, 4vw, 40px); font-weight: 800; letter-spacing: -0.02em; text-wrap: balance; }
  .dek { max-width: 68ch; color: var(--text-dim); font-size: 15.5px; margin: 12px 0 0; }
  .scope-strip { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 18px; font-size: 12.5px; color: var(--text-faint); }
  .scope-strip b { color: var(--text-dim); font-weight: 600; }

  .layout { display: grid; grid-template-columns: 232px minmax(0, 1fr); gap: 48px; padding: 40px 0 100px; align-items: start; }
  @media (max-width: 900px) { .layout { grid-template-columns: 1fr; gap: 28px; } .toc { position: static !important; order: -1; } }

  .toc { position: sticky; top: 20px; max-height: calc(100vh - 40px); overflow-y: auto; }
  .toc-group + .toc-group { margin-top: 20px; }
  .toc-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-faint); font-weight: 700; margin-bottom: 8px; }
  .toc ul { list-style: none; margin: 0; padding: 0; }
  .toc li a {
    display: block; text-decoration: none; font-size: 13.5px; color: var(--text-dim);
    padding: 5px 0 5px 12px; border-left: 2px solid var(--line); transition: color .15s ease, border-color .15s ease;
  }
  .toc li a:hover { color: var(--text); border-left-color: var(--accent); }

  main { min-width: 0; }
  .intro { max-width: 74ch; color: var(--text-dim); font-size: 15px; margin-bottom: 46px; }
  .intro strong { color: var(--text); font-weight: 600; }

  section.block { margin-bottom: 56px; scroll-margin-top: 20px; }
  .block-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 6px; }
  .block-num { font-family: "IBM Plex Mono", monospace; font-size: 12.5px; color: var(--accent); background: var(--accent-soft-bg); padding: 2px 7px; border-radius: 5px; font-weight: 700; }
  .block-head h2 { font-size: 22px; font-weight: 800; margin: 0; letter-spacing: -0.01em; }
  .block-note { color: var(--text-faint); font-size: 13.5px; margin: 0 0 20px; max-width: 66ch; }

  .card { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); padding: 22px 26px; margin-bottom: 14px; scroll-margin-top: 20px; }
  .card h3 { font-size: 15.5px; font-weight: 700; margin: 0 0 8px; letter-spacing: -0.005em; }
  .card h4 { font-size: 13px; font-weight: 700; margin: 16px 0 6px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .04em; }
  .card p { color: var(--text-dim); font-size: 14px; margin: 8px 0; max-width: 70ch; }
  .card ul, .card ol { color: var(--text-dim); font-size: 14px; max-width: 70ch; margin: 8px 0; padding-left: 20px; }
  .card li { margin-bottom: 4px; }
  .card li b, .card p b, .card li strong, .card p strong { color: var(--text); font-weight: 600; }

  .cols2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  @media (max-width: 700px) { .cols2 { grid-template-columns: 1fr; } }

  .chip { display: inline-flex; align-items: center; gap: 5px; font-size: 10.5px; font-weight: 700; padding: 3px 8px; border-radius: 999px; text-transform: uppercase; letter-spacing: .04em; }
  .chip.a { background: var(--accent-soft-bg); color: var(--accent-strong); }
  .chip.ok { background: var(--ok-soft-bg); color: var(--ok); }
  .chip.warn { background: var(--warn-soft-bg); color: var(--warn); }
  .chip.danger { background: var(--danger-soft-bg); color: var(--danger); }

  pre { background: var(--surface-2); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; overflow-x: auto; font-size: 12.5px; line-height: 1.55; margin: 14px 0 6px; }
  pre code { background: none; padding: 0; }
  code { background: var(--surface-2); border: 1px solid var(--line); border-radius: 5px; padding: 1px 6px; font-size: 0.9em; }

  .callout { margin-top: 14px; padding: 12px 15px; border-radius: 10px; font-size: 13px; line-height: 1.55; }
  .callout.warn { background: var(--warn-soft-bg); color: var(--warn); border: 1px solid color-mix(in srgb, var(--warn) 30%, transparent); }
  .callout.danger { background: var(--danger-soft-bg); color: var(--danger); border: 1px solid color-mix(in srgb, var(--danger) 30%, transparent); }
  .callout.info { background: var(--surface-2); border: 1px solid var(--line); color: var(--text-dim); }
  .callout b { color: var(--text); }

  table.ref { width: 100%; border-collapse: collapse; margin: 14px 0 4px; font-size: 13px; }
  table.ref th, table.ref td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
  table.ref th { color: var(--text-faint); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
  table.ref td.code-cell { font-family: "IBM Plex Mono", monospace; color: var(--text-dim); font-size: 12.5px; white-space: nowrap; }
  .ref-wrap { overflow-x: auto; }

  /* system diagram */
  .diagram { display: flex; align-items: stretch; justify-content: space-between; gap: 0; margin: 18px 0 6px; flex-wrap: wrap; }
  .dbox { flex: 1; min-width: 150px; border: 1px solid var(--line); border-radius: 10px; background: var(--surface-2); padding: 12px 14px; }
  .dbox .dt { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: var(--text-faint); margin-bottom: 4px; }
  .dbox .dn { font-size: 13.5px; font-weight: 700; color: var(--text); }
  .dbox .dd { font-size: 11.5px; color: var(--text-dim); margin-top: 4px; }
  .darrow { display: flex; align-items: center; justify-content: center; padding: 0 8px; color: var(--text-faint); font-size: 16px; min-width: 24px; }
  @media (max-width: 760px) { .diagram { flex-direction: column; } .darrow { transform: rotate(90deg); padding: 6px 0; } }

  .stack-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin: 16px 0 4px; }
  .stack-item { border: 1px solid var(--line); border-radius: 10px; padding: 11px 13px; background: var(--surface-2); }
  .stack-item .k { font-size: 10.5px; color: var(--text-faint); text-transform: uppercase; letter-spacing: .04em; margin-bottom: 3px; }
  .stack-item .v { font-weight: 700; font-size: 13.5px; color: var(--text); }

  footer { border-top: 1px solid var(--line); padding: 26px 0 40px; color: var(--text-faint); font-size: 12.5px; max-width: 72ch; }
  footer a { color: var(--text-dim); text-decoration: underline; text-underline-offset: 2px; }

  @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }

  @media print {
    :root {
      --ink: #ffffff; --surface: #ffffff; --surface-2: #f3f5f7; --line: #d7dee5;
      --text: #16202b; --text-dim: #46596b; --text-faint: #66788a;
      --accent: #0c746c; --accent-strong: #0a5f58; --accent-ink: #eafaf8;
      --accent-soft-bg: #e3f5f3;
      --danger: #b91c1c; --danger-soft-bg: #fbe7e7;
      --ok: #047857; --ok-soft-bg: #e3f6ee;
      --warn: #935f07; --warn-soft-bg: #f8eeda;
    }
    body { background: #ffffff; }
    a { text-decoration: underline; color: var(--accent-strong); }
    .toc { display: none; }
    .layout { grid-template-columns: 1fr; gap: 0; padding-top: 20px; }
    section.block { break-inside: avoid; page-break-inside: avoid; }
    .card { break-inside: avoid; page-break-inside: avoid; box-shadow: none; }
    .masthead { break-after: avoid; }
  }
</style>

<div class="masthead">
  <div class="shell">
    <div class="masthead-row">
      <div class="brand">
        <div class="brand-mark">&gt;_</div>
        <span class="brand-name">VepAIr</span>
      </div>
      <span class="eyebrow">Technical reference</span>
    </div>
    <h1 class="title">How VepAIr is built, end to end</h1>
    <p class="dek">
      Architecture, data model, every subsystem's design rationale, deployment topology, and the
      privacy/medical-safety rules that constrain all of it — one document, current as of this
      build. For day-to-day usage instead of engineering, see the
      <a href="/user-guide" target="_top">VepAIr User Guide</a>.
    </p>
    <div class="scope-strip">
      <span><b>Stack</b> Next.js · FastAPI · Postgres</span>
      <span><b>Entities</b> 28 tables</span>
      <span><b>Deploy</b> Vercel + Cloud Run + Supabase</span>
      <span><b>Status</b> live in production</span>
    </div>
  </div>
</div>

<div class="shell">
  <div class="layout">
    <nav class="toc">
      <div class="toc-group">
        <div class="toc-label">Overview</div>
        <ul>
          <li><a href="#what">What VepAIr is</a></li>
          <li><a href="#diagram">System diagram</a></li>
          <li><a href="#stack">Tech stack</a></li>
        </ul>
      </div>
      <div class="toc-group">
        <div class="toc-label">Data</div>
        <ul>
          <li><a href="#datamodel">Entity reference</a></li>
        </ul>
      </div>
      <div class="toc-group">
        <div class="toc-label">Subsystems</div>
        <ul>
          <li><a href="#auth">Auth & accounts</a></li>
          <li><a href="#dsp">Voice capture & DSP</a></li>
          <li><a href="#baseline">Baseline & recovery score</a></li>
          <li><a href="#exercises">Exercises & live coaching</a></li>
          <li><a href="#range">Vocal range & 90-day plan</a></li>
          <li><a href="#sharing">Progress & sharing</a></li>
          <li><a href="#coach">Coach Portal</a></li>
          <li><a href="#reminders">Notifications & reminders</a></li>
          <li><a href="#retention">Data minimization</a></li>
          <li><a href="#billing">Coach Pro billing (SaaS)</a></li>
          <li><a href="#tonegame">Tone Match Challenge</a></li>
          <li><a href="#admin">Backend Admin</a></li>
        </ul>
      </div>
      <div class="toc-group">
        <div class="toc-label">Operations</div>
        <ul>
          <li><a href="#deploy">Deployment topology</a></li>
          <li><a href="#gotchas">Known gotchas</a></li>
        </ul>
      </div>
      <div class="toc-group">
        <div class="toc-label">Trust</div>
        <ul>
          <li><a href="#privacy">Privacy principles</a></li>
          <li><a href="#medsafety">Medical safety rules</a></li>
        </ul>
      </div>
      <div class="toc-group">
        <div class="toc-label">Status</div>
        <ul>
          <li><a href="#status">What's live vs. planned</a></li>
        </ul>
      </div>
    </nav>

    <main>
      <p class="intro">
        VepAIr is an AI-assisted vocal recovery, conditioning, and performance platform — it
        learns one person's voice, builds a personal baseline, and tracks change against
        <strong>only that person's own history, never a population norm.</strong> This reference
        covers the system as it exists in production today: the singer-facing product, the Coach
        Portal, Coach Pro billing, and the internal admin console. It condenses
        <code class="path">ARCHITECTURE.md</code>, <code class="path">TECHNICAL_GUIDE.md</code>,
        <code class="path">PRIVACY.md</code>, and <code class="path">MEDICAL_SAFETY.md</code> into
        one reading pass — those files remain the source of truth for anything omitted here.
      </p>

      <section class="block" id="what">
        <div class="block-head"><span class="block-num">01</span><h2>What VepAIr is</h2></div>
        <div class="card">
          <p>
            A singer creates an account, completes a short onboarding, and can then: log a daily
            check-in, record a guided voice sample (analyzed for pitch, jitter, shimmer, HNR, and
            more), see a daily 0–100 <b>VepAIr Score</b>, follow a routine of adaptive voice
            exercises with real-time coaching feedback, map their comfortable vocal range over
            time, follow a personalized 90-day plan, and play a 5-tone pitch-matching game. A
            vocal coach can run a separate <b>Coach Portal</b>, invited singer by singer, seeing
            only what each singer explicitly chooses to share. VepAIr operators use an internal
            <b>Admin</b> console for account support and Coach Pro billing activation.
          </p>
          <p>
            <b>VepAIr is not a medical diagnostic device.</b> Every measurement, score, and
            recommendation is compared only against the user's own history — never a population
            norm — and no feature ever names a diagnosis or a specific pathology. See
            <a href="#medsafety">Medical safety rules</a>.
          </p>
        </div>
      </section>

      <section class="block" id="diagram">
        <div class="block-head"><span class="block-num">02</span><h2>System diagram</h2></div>
        <p class="block-note">Request/response shape, unchanged since Stage 1 — there is no separate auth service; the API verifies its own JWTs.</p>
        <div class="card">
          <div class="diagram">
            <div class="dbox">
              <div class="dt">Client</div>
              <div class="dn">apps/web</div>
              <div class="dd">Next.js PWA. Bearer JWT held client-side, attached by one apiFetch() helper.</div>
            </div>
            <div class="darrow">&rarr;</div>
            <div class="dbox">
              <div class="dt">Server</div>
              <div class="dn">apps/api</div>
              <div class="dd">FastAPI. get_current_user() verifies every request; every I/O boundary is a Pydantic model.</div>
            </div>
            <div class="darrow">&rarr;</div>
            <div class="dbox">
              <div class="dt">Server</div>
              <div class="dn">packages/audio-engine</div>
              <div class="dd">Parselmouth (Praat) + librosa. Pure DSP, no DB dependency of its own.</div>
            </div>
          </div>
          <div class="diagram" style="margin-top:10px;">
            <div class="dbox">
              <div class="dt">Data</div>
              <div class="dn">PostgreSQL (Supabase)</div>
              <div class="dd">users → recordings → acoustic_measurements → everything downstream.</div>
            </div>
            <div class="darrow">&harr;</div>
            <div class="dbox">
              <div class="dt">Data</div>
              <div class="dn">Object storage</div>
              <div class="dd">Supabase Storage in prod, private bucket, never served by guessable URL.</div>
            </div>
          </div>
          <p style="margin-top:14px;">Real-time coaching (pitch/volume/onset feedback during an exercise) runs entirely
          client-side via the Web Audio API — it never round-trips to the backend; only the
          <i>finished</i> recording gets the full Parselmouth/librosa analysis server-side.</p>
        </div>
      </section>

      <section class="block" id="stack">
        <div class="block-head"><span class="block-num">03</span><h2>Tech stack</h2></div>
        <div class="card">
          <div class="stack-grid">
            <div class="stack-item"><div class="k">Frontend</div><div class="v">Next.js 16 + React 19 + TS</div></div>
            <div class="stack-item"><div class="k">Styling</div><div class="v">Tailwind CSS</div></div>
            <div class="stack-item"><div class="k">Backend</div><div class="v">Python 3.12 + FastAPI</div></div>
            <div class="stack-item"><div class="k">Validation</div><div class="v">Pydantic v2</div></div>
            <div class="stack-item"><div class="k">Database</div><div class="v">PostgreSQL 17</div></div>
            <div class="stack-item"><div class="k">ORM</div><div class="v">SQLAlchemy 2.0 (typed)</div></div>
            <div class="stack-item"><div class="k">Migrations</div><div class="v">Alembic</div></div>
            <div class="stack-item"><div class="k">Auth</div><div class="v">Self-hosted bcrypt + JWT</div></div>
            <div class="stack-item"><div class="k">Audio DSP</div><div class="v">Parselmouth, librosa, numpy</div></div>
            <div class="stack-item"><div class="k">Storage</div><div class="v">Supabase Storage (S3-shaped)</div></div>
          </div>
          <p style="margin-top:14px;">Auth is self-hosted rather than Supabase Auth by deliberate choice, not a placeholder
          — see <a href="#auth">Auth & accounts</a> for the swap point that keeps a later migration cheap. Nothing
          in this table is final; a change here must be documented with a rationale, not swapped silently.</p>
        </div>
      </section>

      <section class="block" id="datamodel">
        <div class="block-head"><span class="block-num">04</span><h2>Entity reference</h2></div>
        <p class="block-note">Grouped by concern. Column-level detail lives in <code class="path">apps/api/app/models.py</code> and <code class="path">migrations/versions/</code> — this table intentionally doesn't duplicate what will drift.</p>

        <div class="card">
          <h4>Identity & auth</h4>
          <div class="ref-wrap"><table class="ref">
            <tr><th>Entity</th><th>Purpose</th></tr>
            <tr><td class="code-cell">User</td><td>Auth identity. <code>is_admin</code>/<code>is_active</code> back Admin.</td></tr>
            <tr><td class="code-cell">AuthCredential</td><td>Bcrypt password hash, 1:1 with User.</td></tr>
            <tr><td class="code-cell">RefreshToken</td><td>Hashed opaque token, revocable, rotated on every use.</td></tr>
            <tr><td class="code-cell">PasswordResetToken</td><td>Hashed, single-use, 60-minute expiry.</td></tr>
            <tr><td class="code-cell">UserProfile</td><td>Onboarding answers — voice use, goals, no medical fields.</td></tr>
            <tr><td class="code-cell">ConsentRecord</td><td>Append-only consent ledger, one row per purpose per change.</td></tr>
          </table></div>

          <h4>Voice measurement</h4>
          <div class="ref-wrap"><table class="ref">
            <tr><th>Entity</th><th>Purpose</th></tr>
            <tr><td class="code-cell">DailyCheckIn</td><td>Subjective journal — voice quality, fatigue, sleep, load, all skippable.</td></tr>
            <tr><td class="code-cell">VoiceSession / Recording</td><td>One guided session; one raw audio asset within it.</td></tr>
            <tr><td class="code-cell">AcousticMeasurement</td><td>Parselmouth/librosa output per recording — F0, jitter, shimmer, HNR, etc.</td></tr>
            <tr><td class="code-cell">DeviceMetadata</td><td>Mic/device fingerprint, reused across sessions.</td></tr>
            <tr><td class="code-cell">Baseline</td><td>Median/MAD personal baseline, one row per (user, metric), upserted in place.</td></tr>
            <tr><td class="code-cell">RecoveryScore</td><td>Daily 0–100 score, one row per (user, date), recomputed fresh on read.</td></tr>
            <tr><td class="code-cell">VocalRange</td><td>Comfortable low/high/falsetto note history — growing ledger, not upserted.</td></tr>
            <tr><td class="code-cell">VocalGoal</td><td>Target low/avg/high note — current-state, one row per user.</td></tr>
            <tr><td class="code-cell">VocalPlan</td><td>90-day Repair/Improvement plan; past plans superseded, not deleted.</td></tr>
          </table></div>

          <h4>Exercises</h4>
          <div class="ref-wrap"><table class="ref">
            <tr><th>Entity</th><th>Purpose</th></tr>
            <tr><td class="code-cell">Exercise</td><td>Library entry — 23 seeded + coach-authored. <code>created_by_coach_id</code> nullable.</td></tr>
            <tr><td class="code-cell">ExerciseSession / ExerciseResult</td><td>One routine instance; per-exercise completion + measured outcome.</td></tr>
          </table></div>

          <h4>Coach Portal</h4>
          <div class="ref-wrap"><table class="ref">
            <tr><th>Entity</th><th>Purpose</th></tr>
            <tr><td class="code-cell">CoachProfile</td><td>Coach account extension. Belongs to exactly one Organization.</td></tr>
            <tr><td class="code-cell">CoachInvite</td><td>An invite to a singer, by email — pending/accepted/declined/revoked.</td></tr>
            <tr><td class="code-cell">CoachAccess</td><td>The active grant. One active coach per singer, DB-enforced (partial unique index).</td></tr>
            <tr><td class="code-cell">CoachAccessCategoryGrant</td><td>Per-category share toggle: recovery_trends / vocal_range / exercise_history / recordings.</td></tr>
            <tr><td class="code-cell">CoachAssignment</td><td>A coach's exercise assignment, with optional per-exercise tone targets.</td></tr>
            <tr><td class="code-cell">AssignmentTemplate</td><td>A coach's saved, reusable exercise set — private per coach, not tied to a singer. Prefills the Assign form; never creates a CoachAssignment by itself.</td></tr>
            <tr><td class="code-cell">CoachNote</td><td>Coach-authored, singer-readable, immutable (soft-delete only).</td></tr>
            <tr><td class="code-cell">CoachMessage</td><td>Two-way coach&lt;-&gt;singer chat — separate from CoachNote. <code>sender</code>, <code>flagged_terms</code>, <code>read_at</code>.</td></tr>
          </table></div>

          <h4>Notifications</h4>
          <div class="ref-wrap"><table class="ref">
            <tr><th>Entity</th><th>Purpose</th></tr>
            <tr><td class="code-cell">NotificationLog</td><td>Idempotency ledger for the daily reminder job — unique on (user, type, date).</td></tr>
          </table></div>

          <h4>Coach Pro billing (SaaS)</h4>
          <div class="ref-wrap"><table class="ref">
            <tr><th>Entity</th><th>Purpose</th></tr>
            <tr><td class="code-cell">Organization</td><td>One per coach, always. Holds <code>is_coach_pro_active</code> and the invite quota.</td></tr>
            <tr><td class="code-cell">UserSubscription</td><td>Singer-side tier (free/user_pro) — laid down, not yet enforced (Square integration not built).</td></tr>
            <tr><td class="code-cell">OrganizationInvoiceLog</td><td>Idempotency + ledger for the (not-yet-built) monthly QuickBooks sync.</td></tr>
          </table></div>

          <h4>Games & admin</h4>
          <div class="ref-wrap"><table class="ref">
            <tr><th>Entity</th><th>Purpose</th></tr>
            <tr><td class="code-cell">ToneGameSession / ToneGameAttempt</td><td>5-Tone Challenge results — client-graded, server-persisted.</td></tr>
            <tr><td class="code-cell">AdminAuditLog</td><td>Append-only trail of every state-changing admin action.</td></tr>
            <tr><td class="code-cell">LoginEvent</td><td>Real login history — password-based logins only, no IP/user-agent.</td></tr>
            <tr><td class="code-cell">SiteSettings</td><td>Singleton row — signup lockdown, beta-NDA gate, and three retention windows.</td></tr>
          </table></div>
        </div>
      </section>

      <section class="block" id="auth">
        <div class="block-head"><span class="block-num">05</span><h2>Auth & accounts</h2></div>
        <div class="card">
          <p><b>Self-hosted email/password, not Supabase Auth</b> — a deliberate Stage-1 deviation
          (Supabase Auth would need the founder's own external signup first) built with one
          explicit swap point: <code>verify_access_token()</code> in <code class="path">app/auth.py</code>.
          Every route depends on <code>get_current_user</code>, never on the token format directly,
          so replacing that one function with Supabase JWT/JWKS verification is the entire migration.</p>
          <table class="ref">
            <tr><th>Token</th><th>Shape</th><th>Expiry</th></tr>
            <tr><td>Access</td><td class="code-cell">JWT, HS256, sub = user id, type: "access"</td><td>15 min</td></tr>
            <tr><td>Impersonation</td><td class="code-cell">Same JWT, type: "impersonation" + impersonated_by claim, no refresh token issued</td><td>15 min, no renewal</td></tr>
            <tr><td>Refresh</td><td class="code-cell">opaque random, SHA-256 hash stored</td><td>30 days, rotated every use</td></tr>
            <tr><td>Password reset</td><td class="code-cell">opaque, hashed, single-use</td><td>60 min</td></tr>
          </table>
          <p>An impersonation token authenticates as the target user but is read-only, enforced
          once in <code>get_current_user</code> — see §16 (Backend Admin) for the full mechanism
          and why the frontend deliberately never wires it into the shared auth context.</p>
          <p><b>Three account shapes</b>, all on the same <code>User</code> table: a <b>singer</b>
          (has a <code>UserProfile</code>), a <b>coach</b> (has a <code>CoachProfile</code>, created
          via <code class="path">POST /api/v1/auth/coach-signup</code> or by an admin), and a
          <b>dual-role</b> account (both — only reachable by an admin attaching coach status to an
          existing singer). One account can never self-serve into dual-role.</p>
        </div>
      </section>

      <section class="block" id="dsp">
        <div class="block-head"><span class="block-num">06</span><h2>Voice capture & DSP</h2></div>
        <div class="card">
          <p><b>Real WAV, not compressed webm/opus.</b> <code class="path">apps/web/src/lib/recorder.ts</code>
          captures raw PCM via <code>getUserMedia</code> + <code>AudioContext</code> and encodes
          16-bit WAV in-browser — DSP needs precise, uncompressed samples.</p>
          <p><b>packages/audio-engine</b> (Parselmouth/Praat for F0, jitter, shimmer, HNR — the
          field-standard tool for exactly those; librosa for spectral centroid/rolloff/ZCR) runs
          automatically on every upload. Jitter/shimmer/HNR are only computed for sustained
          phonation — computing them on a glide or running speech would produce a
          scientifically-invalid number, so those fields return <code>null</code> on other sample
          types rather than fabricate a value.</p>
          <p><b>Recording Quality Score</b> is a separate, deliberately narrow 0–100 score built
          only from capture-technical signals (clipping, gain, duration, noise floor) — it never
          factors in the voice measurements above, so a low score always means "re-record this,"
          never "something may be wrong with your voice." A unit test inspects the scoring
          function's own source for forbidden terms to guard this boundary.</p>
        </div>
      </section>

      <section class="block" id="baseline">
        <div class="block-head"><span class="block-num">07</span><h2>Personal baseline & recovery score</h2></div>
        <div class="card">
          <p><b>Median + MAD, never mean/stddev</b> — robust statistics so a handful of bad
          recordings can't drag the baseline. Anomaly detection is the modified z-score
          (<code>0.6745 × (x − median) / MAD</code>, threshold 3.5), a published method, not
          invented here. A baseline always compares a user only to their own prior sessions,
          computed <i>before</i> the new recording joins it.</p>
          <p><b>VepAIr Score (0–100)</b> is a weighted blend of six components, each either an
          objective measurement vs. the user's own baseline or a same-day self-report. Missing
          components regress toward neutral (50), never zero or dropped — the fix for a real early
          bug where one bad self-report answer alone could tank the whole score. Discomfort ≥ 7/10
          is a hard override to RED regardless of everything else, checked separately, after the
          weighted score. The score is recomputed fresh on every read, never cached stale.</p>
        </div>
      </section>

      <section class="block" id="exercises">
        <div class="block-head"><span class="block-num">08</span><h2>Exercises & live coaching</h2></div>
        <div class="card">
          <p>23-exercise library across 12 categories (breathing, SOVT, trills, sirens, range
          exploration, cooldown...) — no aggressive screaming/distortion technique is included, by
          policy, until a qualified methodology exists. Each category carries an intensity tier;
          <code>throat_discomfort ≥ 7</code> forces the lowest tier and can never be outvoted by
          any other signal — the same hard-override pattern as the recovery score.</p>
          <p><b>Live coaching runs 100% client-side</b> via a dependency-free normalized-
          autocorrelation pitch detector (<code class="path">pitchDetector.ts</code>) — deliberately
          simple, not ML-based, since it only needs "roughly what note is this right now," not
          archival precision. Feedback rules (comfortable-range, gentle-onset, volume-spike,
          pitch-drift, positive reinforcement) are pure and independently unit-tested; a
          configurable minimum interval between messages prevents overwhelming the user. The
          recording itself is discarded at the end — nothing from live coaching is ever uploaded.</p>
          <p>A coach can assign exercises (including their own custom ones); an assignment can
          never push past what today's own safety cap would already allow — it's filtered through
          the exact same <code>allowed</code> list every adaptively-chosen exercise draws from.</p>
        </div>
      </section>

      <section class="block" id="range">
        <div class="block-head"><span class="block-num">09</span><h2>Vocal range & 90-day plan</h2></div>
        <div class="card">
          <p>Range tests reuse the ordinary recording pipeline with three new sample types
          (<code>range_low</code>/<code>range_high</code>/<code>range_falsetto</code>), excluded
          from the personal baseline since an intentionally-extreme note isn't "normal day-to-day
          variation." No register (chest/mix/head-voice) classification exists anywhere — only
          three independently-tracked notes, never combined into a claimed voice "type."</p>
          <p>Once both a recent recording and a range test exist, a 90-day plan (Repair or
          Improvement track, self-selected) generates automatically from that real, already-
          measured data. Auto-graduation from Repair to Improvement checks three independent
          criteria (14+ days ≥70% non-red status, baseline confidence, zero declining trends) and
          is always described as "consistently stable," never "healed."</p>
        </div>
      </section>

      <section class="block" id="sharing">
        <div class="block-head"><span class="block-num">10</span><h2>Progress & sharing</h2></div>
        <div class="card">
          <p><b>Share My Progress</b> renders two 1080×1920 images (today's snapshot, start-vs-now)
          entirely client-side from an authenticated read of already-stored data — nothing is
          computed server-side for this, nothing is uploaded, and a metric with no real data is
          omitted, never invented.</p>
          <p><b>Progress dashboard</b> (<code class="path">/progress</code>) charts the VepAIr
          Score over any range up to all-time, training streaks with a calendar grid, and every
          exercise's improving/declining/stable trend — all built from data other endpoints
          already compute, no new backend logic beyond a couple of read-only aggregation
          functions.</p>
        </div>
      </section>

      <section class="block" id="coach">
        <div class="block-head"><span class="block-num">11</span><h2>Coach Portal</h2></div>
        <div class="card">
          <p><b>The authorization seam:</b> <code class="path">app/coach_auth.py</code>'s
          <code>get_current_coach</code> and <code>require_coach_access(category=...)</code> are
          the only place any endpoint learns "may this coach read this singer's data." Everything
          downstream reuses the singer's own functions unmodified, parameterized by
          <code>singer_user_id</code> instead of <code>current_user.id</code> — a coach's view is
          regression-tested to produce byte-identical JSON to the singer's own endpoint for the
          same data.</p>
          <p><b>Sharing is per-category, per-coach, revocable, never automatic:</b> a singer
          accepts an invite by choosing at least one of four categories
          (<code>recovery_trends</code>, <code>vocal_range</code>, <code>exercise_history</code>,
          <code>recordings</code>), all unchecked by default. One active coach per singer at a
          time is enforced by a real Postgres partial unique index, not just an application check.
          <code>illness_symptoms</code>/<code>reflux_symptoms</code>/free-text notes are
          permanently excluded from every coach-facing response regardless of any grant.</p>
          <p><b>Recording playback</b> for a coach streams the singer's single existing audio
          file via an authenticated, ownership-checked endpoint — VepAIr never creates a second
          copy of a singer's voice for coach access.</p>
          <p><b>Messaging</b> (<code class="path">CoachMessage</code>) is a separate model from
          Notes — a two-way, ephemeral thread rather than a structured one-way record, and
          deliberately not gated by any of the four sharing categories, same reasoning as Notes:
          it's a channel the singer already fully controls. Sending requires
          <code>CoachAccess.status == "active"</code>; reading a singer's own history does not,
          so it survives a revoke the same way Notes does. Reuses Notes' clinical-language
          blocklist (flag, never block) on both senders' messages.</p>
        </div>
      </section>

      <section class="block" id="reminders">
        <div class="block-head"><span class="block-num">12</span><h2>Notifications & reminders</h2></div>
        <div class="card">
          <p><b>No in-process scheduler</b> — Cloud Run scales to zero and runs multiple
          instances, so a daily reminder can't be an in-process timer. Instead,
          <code>POST /api/v1/system/send-reminders</code> is called once a day by an external
          <b>Cloud Scheduler</b> job (see <code class="path">TECHNICAL_GUIDE.md</code> §11 for
          the setup), authenticated by a shared secret header
          (<code>X-Internal-Job-Secret</code> vs. <code>INTERNAL_JOB_SECRET</code>) rather than a
          human admin's 15-minute JWT — the right credential for an unattended job, not the
          wrong one.</p>
          <p><b>Idempotent by construction:</b> <code>NotificationLog</code> carries a unique
          constraint on <code>(user_id, notification_type, sent_for_date)</code>, so calling the
          endpoint twice in a day (a retry, a manual test run) never double-emails anyone — the
          second call simply sends to whoever's left. The job also commits once per user sent,
          not once at the end, so a mid-batch crash never causes a retry to double-send to
          already-processed users.</p>
          <p>The only v1 reminder type: a "How's your voice today?" email to every singer who
          hasn't submitted a <code>DailyCheckIn</code> for the day and has explicit
          <code>notifications</code> consent granted — never for null/undecided or an explicit
          decline. New-message notifications (from Messaging, above) are a separate, synchronous
          send at message-creation time, not part of this batch.</p>
        </div>
      </section>

      <section class="block" id="retention">
        <div class="block-head"><span class="block-num">13</span><h2>Data minimization</h2></div>
        <div class="card">
          <p><b>Self-serve account deletion</b> (<code class="path">DELETE /api/v1/auth/me</code>)
          requires the current password, same bar as changing one. Shares
          <code class="path">app/account_deletion.py</code>'s <code>delete_user_and_storage</code>
          with the admin hard-delete path — every stored recording's actual audio file is
          deleted from object storage before the cascading DB delete removes everything else
          (profile, check-ins, recordings, measurements, coach connections, notes, messages,
          consent records). No admin involvement needed.</p>
          <p><b>Per-recording deletion</b> (<code class="path">DELETE /api/v1/recordings/{"{"}id{"}"}</code>)
          is a full, user-initiated removal — the row and its <code>AcousticMeasurement</code>
          both go (via <code>ondelete="CASCADE"</code>, with <code>passive_deletes=True</code>
          on the relationship so SQLAlchemy trusts the DB's cascade rather than trying to null
          a NOT NULL FK itself). Deliberately different from the retention job below: this is
          the user saying "remove this," not a passive policy.</p>
          <p><b>Retention purge job</b> (<code class="path">POST /api/v1/system/purge-stale-data</code>,
          same shared-secret auth and Cloud Scheduler pattern as <code class="path">send-reminders</code>
          — see §12) runs two independent policies from <code class="path">app/data_retention.py</code>,
          both configurable via <code>SiteSettings</code> (admin-editable, no redeploy):</p>
          <table class="ref">
            <tr><th>Policy</th><th>Default</th><th>What it touches</th></tr>
            <tr><td class="code-cell">recording_retention_days</td><td>90 days</td><td>Deletes the object-storage file and nulls <code>Recording.file_path</code>; the row, <code>AcousticMeasurement</code>, and <code>quality_flags</code> survive.</td></tr>
            <tr><td class="code-cell">checkin_notes_retention_days</td><td>30 days</td><td>Nulls just <code>illness_symptoms</code>/<code>reflux_symptoms</code>/<code>notes</code> on <code>DailyCheckIn</code>; every quantitative field is untouched.</td></tr>
          </table>
          <p><b>Data export</b> (<code class="path">GET /api/v1/profile/export</code>,
          <code class="path">app/data_export.py</code>) returns a JSON file via
          <code>Content-Disposition: attachment</code> covering every table keyed to the
          caller's own id — profile, consent history, check-ins, recordings (metadata +
          measurements, not raw audio bytes — each links back to the existing audio endpoint
          instead), baselines, scores, vocal range/goals/plans, exercise and Tone Match
          history, and coach connections/notes/messages (both directions, plus what a
          coach account has authored). Synchronous, single request — no async job at this
          data scale.</p>
        </div>
      </section>

      <section class="block" id="billing">
        <div class="block-head"><span class="block-num">14</span><h2>Coach Pro billing (SaaS)</h2></div>
        <p class="block-note">Live in production. No Square (or any automated payment provider) on the coach side — see <code class="path">TECHNICAL_GUIDE.md</code> §10 for the operator walkthrough.</p>
        <div class="card">
          <p>Every coach belongs to exactly one <code>Organization</code>, created automatically at
          signup, <code>is_coach_pro_active = false</code> by default — there is no free coach
          tier. <code>get_current_coach</code> 403s with <code>coach_pro_required</code> for every
          coach endpoint until an admin flips this on, which is the single enforcement seam for the
          entire coach surface.</p>
          <p>Payment is collected outside the app; activation is a manual admin action
          (<code class="path">POST /api/v1/admin/organizations/{id}/set-coach-pro</code>), setting
          a 12-month period. 50 <code>CoachInvite</code>s are included per year, computed live
          (never a maintained counter, to avoid drift) — going over doesn't block, it's meant to
          accrue as overage on the org's next QuickBooks draft invoice once that sync exists.</p>
          <div class="callout info">
            <b>Not built yet:</b> the QuickBooks Online monthly sync job (draft-invoice creation,
            OAuth connection) and the singer-side Square/User Pro billing track. Both are scoped
            in <code class="path">ROADMAP.md</code>; <code>UserSubscription</code>/
            <code>OrganizationInvoiceLog</code> already exist so neither needs a future migration
            just to start.
          </div>
        </div>
      </section>

      <section class="block" id="tonegame">
        <div class="block-head"><span class="block-num">15</span><h2>Tone Match Challenge</h2></div>
        <div class="card">
          <p>Five target notes are drawn from the singer's own measured vocal range (not the
          generic reference range the free-practice mode uses), one every 6 seconds (1s tone +
          5s listening window), 30 seconds total. Grading — accuracy (0–60), hold time (0–30),
          reaction speed (0–10) per note — runs entirely client-side on the same pitch-sample
          stream the free-practice mode already collects; the backend's only job is persisting the
          5 graded attempts.</p>
          <p>Personal only, by design: no coach-sharing category exists for game results. A
          home-page trend card (best score per day) stays hidden until a singer has completed 2+
          games, so there's nothing to trend on a single play.</p>
        </div>
      </section>

      <section class="block" id="admin">
        <div class="block-head"><span class="block-num">16</span><h2>Backend Admin</h2></div>
        <div class="card">
          <p>An internal operator surface, not user-facing. <code class="path">app/admin_auth.py</code>'s
          <code>get_current_admin</code> mirrors the coach gate exactly, keyed on
          <code>User.is_admin</code>. No self-serve or API path ever grants the first admin — a
          one-time manual SQL <code>UPDATE</code> against production, documented in
          <code class="path">TECHNICAL_GUIDE.md</code> §9. Every subsequent grant/revoke, and
          every deactivate/reactivate/delete/reset/bulk-action/impersonation/export, goes through
          the UI and is written to <code>AdminAuditLog</code> before it takes effect —
          read-only actions (search, detail, reports) are not logged.</p>
          <p>Hard delete requires the account to already be deactivated
          (<code>409 must_deactivate_first</code> otherwise) and reuses the exact same deletion
          routine self-serve account deletion uses, so there is exactly one deletion code path in
          the app. See the User Guide's Admin section for the operational walkthrough.</p>
          <p><b>Two admin tiers</b> (<code>User.admin_role</code>, nullable — null reads as
          <code>"full"</code>): <code>app/admin_auth.py</code>'s <code>require_full_admin</code>
          gates create-user, hard-delete, grant/revoke-admin, set-coach, set-password,
          impersonate, and the contact-list export; <code>get_current_admin</code> alone (any
          tier) covers search, detail, reports, deactivate/reactivate (including bulk), and
          triggering a password-reset email.</p>
          <p><b>Bulk operations</b> (<code class="path">POST /api/v1/admin/users/bulk-deactivate</code>
          / <code>bulk-reactivate</code>) are deliberately the only two — both already
          fully-reversible single-account actions before this. One <code>AdminAuditLog</code> row
          per affected account, not one for the whole batch.</p>
          <p><b>Impersonation</b> (<code class="path">POST /api/v1/admin/users/{"{"}id{"}"}/impersonate</code>,
          full-admin-only) issues a JWT with <code>type: "impersonation"</code> and an
          <code>impersonated_by</code> claim instead of <code>type: "access"</code> — same expiry
          as a normal access token, no refresh token at all. Read-only enforcement lives in one
          place, <code class="path">app/auth.py</code>'s <code>get_current_user</code>: any
          non-GET request carrying an impersonation-typed token 403s
          (<code>impersonation_read_only</code>) before the route handler ever runs, since every
          authenticated endpoint resolves the caller through that function already. The frontend
          (<code class="path">/admin/users/{"{"}id{"}"}/view-as</code>) deliberately never wires
          the impersonation token into the shared auth context — it does its own raw
          <code>fetch</code> calls and never touches the admin's own access/refresh tokens, so an
          expired impersonation token can't fall into the normal refresh flow and silently
          re-mint a real admin token while the "Viewing as..." banner is still showing. Shows
          account/engagement facts only (practice frequency, musical style, a 7-day check-in
          count) — deliberately nothing about voice health or recovery status, even in summary
          form.</p>
          <p><b>Login events</b> (<code>LoginEvent</code>, written only by a password-based
          <code class="path">POST /api/v1/auth/login</code> — not signup, not a token refresh)
          replaced the old RefreshToken-issued-at proxy for <code>last_session_at</code>. DAU/WAU
          deliberately keep their existing check-in-or-recording-based definition rather than
          switching to raw login counts — a real product-engagement signal, not a worse one now
          that login data exists. <code>SiteSettings.login_event_retention_days</code> (default
          365) purges old rows via the same daily job as §13's other retention policies.</p>
          <p><b>Contact-list export</b> (<code class="path">GET /api/v1/admin/users/export</code>,
          CSV, full-admin-only) reuses <code>query_report</code>'s exact filter-building helper,
          uncapped instead of 200-row-limited. Deliberately email-address-only — this app keeps
          no other contact PII — and the one action in the whole admin surface that hands raw
          data out as a file, so it gets hard-delete-level audit rigor: the filters used are
          logged, never the resulting rows.</p>
          <div class="callout warn"><b>Route-ordering gotcha</b>:
          <code class="path">GET /users/export</code> is registered <i>before</i>
          <code class="path">GET /users/{"{"}user_id{"}"}</code> in <code class="path">admin.py</code>
          — FastAPI matches routes in registration order, so the reverse order would have
          "export" captured as a UUID path param and 422 before ever reaching the export
          handler.</div>
        </div>
      </section>

      <section class="block" id="deploy">
        <div class="block-head"><span class="block-num">17</span><h2>Deployment topology</h2></div>
        <div class="card">
          <table class="ref">
            <tr><th>Account</th><th>Owns</th><th>Trigger</th></tr>
            <tr><td>GitHub</td><td>Source of truth</td><td>—</td></tr>
            <tr><td>Vercel</td><td>Frontend (<code class="path">apps/web</code>)</td><td>Auto, every push to <code>main</code></td></tr>
            <tr><td>Cloud Run</td><td>Backend (<code class="path">apps/api</code>)</td><td class="code-cell">Manual — gcloud run deploy</td></tr>
            <tr><td>Supabase</td><td>Postgres + Storage</td><td>Migrations run as part of the manual backend deploy</td></tr>
          </table>
          <div class="callout warn">
            <b>The single most important operational fact:</b> a <code>git push</code> updates the
            live frontend automatically in minutes. It does <b>nothing</b> to the live backend — a
            code change to <code class="path">apps/api</code> is not actually live until a manual
            <code>gcloud run deploy</code> runs from Cloud Shell.
          </div>
        </div>
      </section>

      <section class="block" id="gotchas">
        <div class="block-head"><span class="block-num">18</span><h2>Known gotchas</h2></div>
        <div class="card">
          <ul>
            <li><b>Application logs land under <code>jsonPayload</code>, not <code>textPayload</code></b> in Cloud Logging — filter on <code>jsonPayload.logger</code>.</li>
            <li><b>Microsoft Graph <code>sendMail</code> returning 202 ≠ delivered</b> — Exchange Online's own outbound protection can silently drop it afterward.</li>
            <li><b>Dockerfile must sit at the repo root</b>, not <code class="path">apps/api/</code> — <code>gcloud run deploy --source .</code> only auto-detects a root-level Dockerfile.</li>
            <li><b>A literal <code>%</code> in the DB password crashes Alembic's config parser</b> unless escaped as <code>%%</code> — Python's <code>configparser</code> treats it as interpolation syntax.</li>
            <li><b><code>API_CORS_ORIGINS</code> must explicitly list every live frontend origin</b> — a missing one fails every POST from that domain with a browser-side CORS error that looks unrelated to auth.</li>
            <li><b><code>STORAGE_BACKEND=local</code> does not survive Cloud Run</b> — containers are ephemeral; production must run <code>supabase</code>.</li>
          </ul>
          <p>Full detail, exact commands, and incident history for each: <code class="path">TECHNICAL_GUIDE.md</code> §6.</p>
        </div>
      </section>

      <section class="block" id="privacy">
        <div class="block-head"><span class="block-num">19</span><h2>Privacy principles</h2></div>
        <div class="card">
          <ul>
            <li><b>Minimal collection</b> — collect only what a shipped feature needs. Exercise-attempt audio is analyzed in-memory and never written to storage at all; only the derived numbers persist.</li>
            <li><b>No public-by-guessable-URL storage</b> — every recording read goes through an authenticated, ownership-checked endpoint.</li>
            <li><b>Consent is granular, never one checkbox</b> — product analytics, model training, coach sharing, and notifications are four independent grants; accepting one never implies another.</li>
            <li><b>User rights at the data-model level</b> — self-serve account deletion, per-recording deletion, and a full data export are all live (§13); an automatic retention window on raw audio and the most sensitive check-in free-text fields means even undeleted data doesn't sit forever.</li>
            <li><b>Admin access is itself access to user data</b> — not gated by user consent (it's operational, not a sharing relationship), but every state-changing action is audited the same way.</li>
          </ul>
        </div>
      </section>

      <section class="block" id="medsafety">
        <div class="block-head"><span class="block-num">20</span><h2>Medical safety rules</h2></div>
        <div class="card">
          <p>Binding on all product copy, UI strings, and AI-generated text, at every stage.</p>
          <ul>
            <li>Never name a diagnosis or pathology, and never claim a microphone can observe anatomy — <i>"Your voice appears less stable than your typical measurements today"</i>, never <i>"your vocal folds are swollen."</i></li>
            <li>Escalation language recommends a qualified professional on urgent-symptom signals — never "push through it," never suppressed to preserve engagement.</li>
            <li>Confidence labels (baseline, recovery score) are data-sufficiency indicators, explicitly labeled as such — never a clinical probability.</li>
            <li>"Consistently stable," never "healed." Track choice is self-selected, never a diagnosis, and can never weaken a hard safety rule.</li>
            <li>Coach notes carry a non-dismissible disclaimer and a server-side blocklist (flags, never blocks) for clinical-sounding terms — friction, not prevention, since legitimate escalation language must stay possible.</li>
          </ul>
        </div>
      </section>

      <section class="block" id="status" style="margin-bottom: 0;">
        <div class="block-head"><span class="block-num">21</span><h2>What's live vs. planned</h2></div>
        <div class="card">
          <div class="cols2">
            <div>
              <h4>Live in production</h4>
              <ul>
                <li>Full singer product through Progress Dashboard</li>
                <li>Coach Portal (roster, invites, assign, notes, messaging, custom exercises)</li>
                <li>Coach Pro billing/gating (manual activation)</li>
                <li>Backend Admin (users, orgs, reports, audit log, role tiers, bulk ops, impersonation, contact export — §16)</li>
                <li>Tone Match Challenge (5-tone game + trend)</li>
                <li>Practice reminders (Cloud Scheduler-triggered daily email)</li>
                <li>Data minimization (self-serve delete, per-recording delete, export, retention purge — §13)</li>
                <li>Real login-event table, replacing the old last-login proxy</li>
              </ul>
            </div>
            <div>
              <h4>Scoped, not built</h4>
              <ul>
                <li>QuickBooks Online monthly invoicing sync</li>
                <li>Singer-side Square/User Pro billing</li>
                <li>Cross-user Tone Match leaderboard</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</div>

<footer>
  <div class="shell">
    Synthesized from <code class="path">ARCHITECTURE.md</code>, <code class="path">TECHNICAL_GUIDE.md</code>,
    <code class="path">PRIVACY.md</code>, and <code class="path">MEDICAL_SAFETY.md</code> — those files are the
    living source of truth; this page is a snapshot for fast onboarding and external review.
  </div>
</footer>

</html>`;
