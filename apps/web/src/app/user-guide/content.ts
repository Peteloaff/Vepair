// Self-contained HTML document rendered inside an isolated <iframe srcDoc> on the
// matching page.tsx -- keeps this document's own CSS (:root tokens, resets like
// `* { box-sizing }` and `a { color: inherit }`) from ever touching the app shell's
// TopNav/footer that also render on that page, and vice versa. Content originates from
// the published VepAIr artifact of the same name; kept in sync by hand.
export const USER_GUIDE_HTML = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>VepAIr User Guide</title>
<style>
  :root {
    --ink: #0a0a0a; --surface: #141414; --surface-2: #1b1b1b; --line: #272727;
    --text: #ededed; --text-dim: #a3a3a3; --text-faint: #6f6f6f;
    --accent: #f2b134; --accent-strong: #d99a1f; --accent-ink: #241a02;
    --accent-soft-bg: rgba(242, 177, 52, 0.1);
    --danger: #f87171; --danger-strong: #ef4444; --danger-soft-bg: rgba(248, 113, 113, 0.1);
    --ok: #34d399; --ok-soft-bg: rgba(52, 211, 153, 0.1);
    --coach: #a78bfa; --coach-soft-bg: rgba(167, 139, 250, 0.1);
  }
  /* Always dark -- matches the rest of the VepAIr app, which has no theme toggle. */

  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0; background: var(--ink); color: var(--text);
    font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6; -webkit-font-smoothing: antialiased;
  }
  code, .mono, .cmd, .path { font-family: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace; }
  a { color: inherit; }

  .shell { max-width: 1180px; margin: 0 auto; padding: 0 24px; }

  .masthead { border-bottom: 1px solid var(--line); padding: 28px 0; }
  .masthead-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .brand { display: flex; align-items: center; gap: 10px; }
  .brand-mark {
    width: 30px; height: 30px; border-radius: 8px;
    background: var(--surface-2); border: 1px solid var(--line);
    display: flex; align-items: center; justify-content: center; font-size: 14px; flex: none;
  }
  .brand-name { font-weight: 700; font-size: 17px; letter-spacing: -0.01em; }
  .eyebrow {
    text-transform: uppercase; letter-spacing: 0.11em; font-size: 11px;
    color: var(--accent); font-weight: 700;
    background: var(--accent-soft-bg); padding: 3px 9px; border-radius: 999px;
  }
  h1.title {
    margin: 12px 0 0; font-size: clamp(26px, 4vw, 36px); font-weight: 800;
    letter-spacing: -0.02em; text-wrap: balance;
  }
  .dek { max-width: 68ch; color: var(--text-dim); font-size: 15.5px; margin: 12px 0 0; }
  .scope-strip {
    display: flex; gap: 18px; flex-wrap: wrap; margin-top: 18px;
    font-size: 12.5px; color: var(--text-faint);
  }
  .scope-strip b { color: var(--text-dim); font-weight: 600; }

  .layout { display: grid; grid-template-columns: 228px minmax(0, 1fr); gap: 48px; padding: 40px 0 90px; align-items: start; }
  @media (max-width: 860px) { .layout { grid-template-columns: 1fr; gap: 28px; } .toc { position: static !important; order: -1; } }

  .toc { position: sticky; top: 24px; max-height: calc(100vh - 48px); overflow-y: auto; }
  .toc-group + .toc-group { margin-top: 22px; }
  .toc-label {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-faint);
    font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;
  }
  .toc-dot { width: 6px; height: 6px; border-radius: 999px; flex: none; }
  .toc-dot.singer { background: var(--accent); }
  .toc-dot.coach { background: var(--coach); }
  .toc-dot.admin { background: var(--danger); }
  .toc ul { list-style: none; margin: 0; padding: 0; }
  .toc li a {
    display: block; text-decoration: none; font-size: 13.5px; color: var(--text-dim);
    padding: 5px 0 5px 12px; border-left: 2px solid var(--line);
    transition: color .15s ease, border-color .15s ease;
  }
  .toc li a:hover { color: var(--text); border-left-color: var(--accent); }

  main { min-width: 0; }
  .intro { max-width: 70ch; color: var(--text-dim); font-size: 15px; margin-bottom: 36px; }
  .intro strong { color: var(--text); font-weight: 600; }

  .role-banner {
    display: flex; align-items: center; gap: 12px; margin: 0 0 40px; padding: 14px 18px;
    border-radius: 12px; border: 1px solid var(--line); flex-wrap: wrap;
  }
  .role-banner a {
    text-decoration: none; font-size: 13px; font-weight: 600; padding: 7px 14px; border-radius: 999px;
    border: 1px solid var(--line); color: var(--text-dim);
  }
  .role-banner a.singer:hover { border-color: var(--accent); color: var(--accent); }
  .role-banner a.coach:hover { border-color: var(--coach); color: var(--coach); }
  .role-banner a.admin:hover { border-color: var(--danger); color: var(--danger); }

  .role-head { display: flex; align-items: center; gap: 12px; margin: 64px 0 8px; }
  .role-head:first-of-type { margin-top: 0; }
  .role-head .rh-mark {
    width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center;
    justify-content: center; font-size: 16px; font-weight: 800; flex: none; border: 1px solid var(--line);
  }
  .role-head.singer .rh-mark { background: var(--accent-soft-bg); color: var(--accent); }
  .role-head.coach .rh-mark { background: var(--coach-soft-bg); color: var(--coach); }
  .role-head.admin .rh-mark { background: var(--danger-soft-bg); color: var(--danger); }
  .role-head h1 { font-size: 24px; font-weight: 800; margin: 0; letter-spacing: -0.01em; }
  .role-dek { color: var(--text-faint); font-size: 13.5px; margin: 0 0 34px; max-width: 66ch; }

  section.block { margin-bottom: 48px; scroll-margin-top: 24px; }
  .block-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 6px; }
  .block-num {
    font-family: ui-monospace, monospace; font-size: 12.5px; color: var(--accent);
    background: var(--accent-soft-bg); padding: 2px 7px; border-radius: 5px; font-weight: 700;
  }
  .role-head.coach ~ .block .block-num, .coach-section .block-num { color: var(--coach); background: var(--coach-soft-bg); }
  .role-head.admin ~ .block .block-num, .admin-section .block-num { color: var(--danger); background: var(--danger-soft-bg); }
  .block-head h2 { font-size: 20px; font-weight: 800; margin: 0; letter-spacing: -0.01em; }
  .block-note { color: var(--text-faint); font-size: 13.5px; margin: 0 0 18px; max-width: 62ch; }

  .card {
    border: 1px solid var(--line); border-radius: 14px; background: var(--surface);
    padding: 22px 26px; margin-bottom: 14px; scroll-margin-top: 24px;
  }
  .card h3 { font-size: 16px; font-weight: 700; margin: 0 0 8px; letter-spacing: -0.005em; }
  .card p { color: var(--text-dim); font-size: 14px; margin: 8px 0; max-width: 66ch; }
  .card ul, .card ol.plain { color: var(--text-dim); font-size: 14px; max-width: 66ch; margin: 8px 0; padding-left: 20px; }
  .card li { margin-bottom: 4px; }
  .card b, .card strong { color: var(--text); font-weight: 600; }

  .chip {
    display: inline-flex; align-items: center; gap: 5px; font-size: 10.5px; font-weight: 700;
    padding: 3px 8px; border-radius: 999px; text-transform: uppercase; letter-spacing: .04em;
  }
  .chip.get { background: var(--ok-soft-bg); color: var(--ok); }
  .chip.post { background: var(--accent-soft-bg); color: var(--accent); }
  .chip.danger-chip { background: var(--danger-soft-bg); color: var(--danger); }
  .chip.coach-chip { background: var(--coach-soft-bg); color: var(--coach); }
  .chip.pro { background: var(--ok-soft-bg); color: var(--ok); }

  .endpoint { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
  .endpoint .path { font-size: 13px; color: var(--text-dim); }

  .steps { margin: 14px 0 4px; padding-left: 0; list-style: none; counter-reset: step; }
  .steps li {
    counter-increment: step; position: relative; padding-left: 30px;
    font-size: 13.5px; color: var(--text-dim); margin-bottom: 8px;
  }
  .steps li::before {
    content: counter(step); position: absolute; left: 0; top: .05em;
    width: 19px; height: 19px; border-radius: 5px; background: var(--surface-2);
    border: 1px solid var(--line); color: var(--text-faint); font-size: 10.5px; font-weight: 700;
    display: flex; align-items: center; justify-content: center; font-family: ui-monospace, monospace;
  }
  .steps b { color: var(--text); font-weight: 600; }

  .ui-btn {
    display: inline-block; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 7px;
    font-family: ui-monospace, monospace;
  }
  .ui-btn.solid { background: var(--accent); color: var(--accent-ink); }
  .ui-btn.outline { border: 1px solid var(--line); color: var(--text-dim); background: var(--surface-2); }
  .ui-btn.danger { border: 1px solid var(--danger); color: var(--danger); background: var(--danger-soft-bg); }

  pre {
    background: var(--surface-2); border: 1px solid var(--line); border-radius: 10px;
    padding: 14px 16px; overflow-x: auto; font-size: 12.5px; line-height: 1.55; margin: 14px 0 6px;
  }
  pre code { background: none; padding: 0; }
  code {
    background: var(--surface-2); border: 1px solid var(--line); border-radius: 5px;
    padding: 1px 6px; font-size: 0.9em;
  }

  .callout { margin-top: 14px; padding: 12px 15px; border-radius: 10px; font-size: 13px; line-height: 1.55; }
  .callout.warn { background: var(--danger-soft-bg); color: var(--danger); border: 1px solid color-mix(in srgb, var(--danger) 30%, transparent); }
  .callout.info { background: var(--surface-2); border: 1px solid var(--line); color: var(--text-dim); }
  .callout.note { background: var(--accent-soft-bg); border: 1px solid color-mix(in srgb, var(--accent) 25%, transparent); color: var(--text-dim); }
  .callout.coach { background: var(--coach-soft-bg); border: 1px solid color-mix(in srgb, var(--coach) 25%, transparent); color: var(--text-dim); }
  .callout b { color: var(--text); }

  .lifecycle { display: flex; align-items: center; gap: 0; margin: 18px 0 6px; flex-wrap: wrap; }
  .lc-state {
    padding: 9px 16px; border-radius: 999px; font-size: 12.5px; font-weight: 700;
    border: 1px solid var(--line); background: var(--surface-2); white-space: nowrap;
  }
  .lc-state.active { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 40%, var(--line)); }
  .lc-state.inactive { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 40%, var(--line)); }
  .lc-state.gone { color: var(--danger); border-color: color-mix(in srgb, var(--danger) 40%, var(--line)); }
  .lc-arrow { color: var(--text-faint); font-size: 12px; padding: 0 10px; white-space: nowrap; }

  .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; margin: 16px 0 4px; }
  .stat { border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; background: var(--surface-2); }
  .stat .k { font-size: 11px; color: var(--text-faint); margin-bottom: 3px; }
  .stat .v { font-family: ui-monospace, monospace; font-weight: 700; font-size: 15px; color: var(--text); }

  .share-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; margin: 14px 0 4px; }
  .share-item { border: 1px solid var(--line); border-radius: 10px; padding: 10px 13px; background: var(--surface-2); font-size: 13px; color: var(--text-dim); }
  .share-item b { display: block; color: var(--text); font-size: 13.5px; margin-bottom: 2px; }

  table.ref { width: 100%; border-collapse: collapse; margin: 14px 0 4px; font-size: 13px; }
  table.ref th, table.ref td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); }
  table.ref th { color: var(--text-faint); font-weight: 600; font-size: 11.5px; text-transform: uppercase; letter-spacing: .05em; }
  table.ref td.code-cell { font-family: ui-monospace, monospace; color: var(--text-dim); font-size: 12.5px; }
  .ref-wrap { overflow-x: auto; }

  footer {
    border-top: 1px solid var(--line); padding: 26px 0 40px; color: var(--text-faint);
    font-size: 12.5px; max-width: 70ch;
  }
  footer a { color: var(--text-dim); text-decoration: underline; text-underline-offset: 2px; }

  @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }

  @media print {
    :root {
      --ink: #ffffff; --surface: #ffffff; --surface-2: #f5f4f2; --line: #e0ddd8;
      --text: #171717; --text-dim: #52525b; --text-faint: #7a7a75;
      --accent: #935f07; --accent-strong: #7a4e06; --accent-ink: #fff7e6;
      --accent-soft-bg: #f7ecd6;
      --danger: #b91c1c; --danger-soft-bg: #fbe7e7;
      --ok: #047857; --ok-soft-bg: #e3f6ee;
      --coach: #6d28d9; --coach-soft-bg: #efe7fc;
    }
    body { background: #ffffff; }
    a { text-decoration: underline; }
    .toc { display: none; }
    .layout { grid-template-columns: 1fr; gap: 0; padding-top: 20px; }
    .role-banner { display: none; }
    section.block { break-inside: avoid; page-break-inside: avoid; }
    .card { break-inside: avoid; page-break-inside: avoid; box-shadow: none; }
    .role-head { break-before: page; break-after: avoid; }
    .role-head:first-of-type { break-before: avoid; }
    .masthead { break-after: avoid; }
  }
</style>

<div class="masthead">
  <div class="shell">
    <div class="masthead-row">
      <div class="brand">
        <div class="brand-mark">🎙</div>
        <span class="brand-name">VepAIr</span>
      </div>
      <span class="eyebrow">User guide</span>
    </div>
    <h1 class="title">Everything VepAIr does, role by role</h1>
    <p class="dek">
      A plain-English walkthrough for the three people who use this app: the Vrotégé training
      their voice, the coach following a roster of Vrotégés, and the admin keeping the whole thing
      running. VepAIr is <strong>not</strong> a medical diagnostic device — it compares your voice
      only to your own past recordings, never to anyone else's.
    </p>
    <div class="scope-strip">
      <span><b>Vrotégé</b> the core app</span>
      <span><b>Coach</b> /coach</span>
      <span><b>Admin</b> /admin</span>
      <span><b>Updated</b> 2026-08-26</span>
    </div>
  </div>
</div>

<div class="shell">
  <div class="layout">
    <nav class="toc">
      <div class="toc-group">
        <div class="toc-label"><span class="toc-dot singer"></span>Vrotégé</div>
        <ul>
          <li><a href="#getting-started">Getting started</a></li>
          <li><a href="#dashboard">Your dashboard</a></li>
          <li><a href="#recording">Recording a voice sample</a></li>
          <li><a href="#exercises">Voice exercises</a></li>
          <li><a href="#range">Vocal range mapping</a></li>
          <li><a href="#plan">Your 90-day plan</a></li>
          <li><a href="#tonematch">Tone Match & the 5-Tone Challenge</a></li>
          <li><a href="#share">Share My Progress</a></li>
          <li><a href="#progress">Progress dashboard</a></li>
          <li><a href="#coach-access">Sharing with a coach</a></li>
          <li><a href="#reminders">Practice reminders</a></li>
          <li><a href="#singer-troubleshooting">Troubleshooting</a></li>
        </ul>
      </div>
      <div class="toc-group">
        <div class="toc-label"><span class="toc-dot coach"></span>Coach</div>
        <ul>
          <li><a href="#coach-account">Your coach account</a></li>
          <li><a href="#coach-pro">Coach Pro activation</a></li>
          <li><a href="#coach-invite">Inviting a Vrotégé</a></li>
          <li><a href="#coach-roster">Your roster</a></li>
          <li><a href="#coach-singer-view">A Vrotégé's dashboard</a></li>
          <li><a href="#coach-assign">Assign training</a></li>
          <li><a href="#coach-notes">Notes</a></li>
          <li><a href="#coach-messages">Messages</a></li>
          <li><a href="#coach-privacy">What you can never see</a></li>
        </ul>
      </div>
      <div class="toc-group">
        <div class="toc-label"><span class="toc-dot admin"></span>Admin</div>
        <ul>
          <li><a href="#bootstrap">Granting the first admin</a></li>
          <li><a href="#search">Finding an account</a></li>
          <li><a href="#lifecycle">Deactivate / reactivate</a></li>
          <li><a href="#roles">Roles & dual-role accounts</a></li>
          <li><a href="#impersonate">Viewing as a user</a></li>
          <li><a href="#reset">Password reset</a></li>
          <li><a href="#delete">Hard delete</a></li>
          <li><a href="#orgs">Organizations & Coach Pro</a></li>
          <li><a href="#reports">Reports</a></li>
          <li><a href="#site-settings">Site settings</a></li>
          <li><a href="#audit">The audit trail</a></li>
          <li><a href="#gaps">Known gaps</a></li>
        </ul>
      </div>
    </nav>

    <main>
      <p class="intro">
        Jump to whichever role is yours — most people only ever need one section. A single VepAIr
        account is exactly one of these at a time, except an admin, which is a privilege layered
        on top of an existing Vrotégé or coach account, not a fourth account type.
      </p>
      <div class="role-banner">
        <a class="singer" href="#getting-started">🎤 I'm a Vrotégé</a>
        <a class="coach" href="#coach-account">🎓 I'm a coach</a>
        <a class="admin" href="#bootstrap">⚙ I'm an admin</a>
      </div>

      <!-- ============ SINGER ============ -->
      <div class="role-head singer">
        <div class="rh-mark">S</div>
        <h1>For Vrotégés</h1>
      </div>
      <p class="role-dek">The core app — training, tracking, and understanding your own voice over time.</p>

      <section class="block" id="getting-started">
        <div class="block-head"><span class="block-num">01</span><h2>Getting started</h2></div>
        <div class="card">
          <h3>Create an account</h3>
          <ol class="plain">
            <li>Tap <b>Create an account</b> (not <b>Log in</b> — that's only for returning users).</li>
            <li>Enter an email and a password (8+ characters).</li>
            <li>You land directly on <b>onboarding</b> — no separate step.</li>
          </ol>
        </div>
        <div class="card">
          <h3>Onboarding</h3>
          <p>Everything here is optional — skip anything you'd rather not answer. It only personalizes the app; it never gates access.</p>
          <ul>
            <li><b>Pick a track</b>: <b>Vocal Repair</b> (gentle, steadiness-focused) or <b>Vocal Improvement</b> (a step up, more demanding). Self-selected, not a diagnosis — change it any time.</li>
            <li>A few background questions: how you use your voice, singing style, practice frequency, your own sense of your range, goals, coaching history.</li>
            <li>Tap <b>Save</b>, then <b>Done</b>.</li>
          </ul>
        </div>
        <div class="card">
          <h3>Forgot your password?</h3>
          <p><b>Forgot password?</b> on the login page → enter your email → follow the reset link. For privacy, VepAIr always shows the same "a reset link is on its way" message whether or not that email has an account.</p>
        </div>
        <div class="card">
          <h3>Your account (Settings)</h3>
          <p><b>Download my data</b> gets you a single file with everything VepAIr has on your account — check-ins, measurements, vocal range history, exercise history, coach notes and messages, and more. Raw audio isn't bundled into it; each recording links to where you can get it separately (see <a href="#recording">Recording a voice sample</a>).</p>
          <p><b>Delete my account</b> is fully self-serve — no need to contact anyone. It requires your password and typing <code class="mono">DELETE</code> to confirm, and it's permanent: every recording's actual audio file, every check-in, and everything derived from them is gone, not just hidden.</p>
        </div>
      </section>

      <section class="block" id="dashboard">
        <div class="block-head"><span class="block-num">02</span><h2>Your dashboard</h2></div>
        <div class="card">
          <p>Home base — reach Progress, Vocal plan, Vocal range, Voice exercises, Tone Match, and Record voice sample from here.</p>
          <h3>Daily check-in</h3>
          <p>A quick, entirely optional journal — every field can be skipped individually.</p>
          <table class="ref">
            <tr><th>Field</th><th>Captures</th></tr>
            <tr><td>Voice quality / Fatigue</td><td>1–10, your own judgment</td></tr>
            <tr><td>Throat discomfort</td><td>0–10</td></tr>
            <tr><td>Speaking / singing load</td><td>None / Low / Moderate / High</td></tr>
            <tr><td>Sleep</td><td>Hours</td></tr>
            <tr><td>Hydration, alcohol, smoke/vape</td><td>None / Low / Moderate / High</td></tr>
            <tr><td>Illness, reflux, notes</td><td>Free text — private to you, never shared with a coach</td></tr>
          </table>
          <p>Once submitted it's a read-only summary with an <b>Edit</b> link. Feeds your VepAIr Score and your exercise routine.</p>
          <h3>VepAIr Score</h3>
          <p>A daily 0–100 score with a GREEN / YELLOW / RED status. Tap <b>"why did I get this score?"</b> for the actual breakdown. A training/recovery indicator, not a medical score — fully explainable by design.</p>
        </div>
      </section>

      <section class="block" id="recording">
        <div class="block-head"><span class="block-num">03</span><h2>Recording a voice sample</h2></div>
        <div class="card">
          <p>Tap <b>Record voice sample</b> — a guided ~3–5 minute session. Find a quiet room, hold your device at a consistent distance, avoid touching the mic, and use the same mic across sessions if you can.</p>
          <ol class="steps">
            <li>Sustained <b>"Ah"</b> — hold it steady, as long as feels natural.</li>
            <li>Sustained <b>"Ee"</b></li>
            <li>Sustained <b>"Oo"</b></li>
            <li>A comfortable hum, no strain.</li>
            <li>A gentle pitch glide, low to high — don't push for range.</li>
            <li>Read a standard sentence aloud at your normal pace.</li>
            <li><b>Optional, skippable</b>: sing a short phrase you know well.</li>
          </ol>
          <p>Each step offers <b>Retake</b> or <b>Use this take</b>. Clipped/too quiet/too short takes show a warning but you can still use them. At the end: a quality label (excellent/good/fair/poor) and the raw numbers behind it — always labeled as raw acoustic measurements, never a diagnosis.</p>
          <p><b>Recordings</b> (nav bar) lists every past recording session. Play any recording back, or <b>Delete</b> it — permanent, removes the audio and its measurements immediately, and it stops counting toward your trends. Raw audio is also automatically removed after a retention period even if you never delete it yourself; your measurements and trend history are unaffected either way, only the playable audio goes.</p>
        </div>
      </section>

      <section class="block" id="exercises">
        <div class="block-head"><span class="block-num">04</span><h2>Voice exercises</h2></div>
        <div class="card">
          <p>Tap <b>Voice exercises</b>. Pick how much time you have and how often you want live coaching feedback (Frequent / Normal / Minimal). VepAIr builds a routine from today's check-in, your recent recordings, and your recovery status — different every day, on purpose.</p>
          <p>If your recent data suggests going gentle, you'll see <b>"Before you start"</b> explaining the routine has been kept to the gentlest exercises. Reported discomfort always caps the routine — VepAIr never tells you to push through anything.</p>
          <p>During each exercise: instructions, a countdown, and (mic permitting) live feedback on pitch, volume, onset, or glide smoothness — entirely on your device, nothing uploaded for this part. <b>Skip</b> or <b>Mark done</b> on any exercise. At the end: completion count, per-exercise trend notes, and a <b>Share My Progress</b> button.</p>
        </div>
      </section>

      <section class="block" id="range">
        <div class="block-head"><span class="block-num">05</span><h2>Vocal range mapping</h2></div>
        <div class="card">
          <p>Tap <b>Vocal range</b>. Never force a note — stop the moment anything feels strained.</p>
          <ol class="plain">
            <li>Your comfortable <b>low</b> note.</li>
            <li>Your comfortable <b>high</b> note.</li>
            <li><b>Optional</b>: a falsetto/head-voice note.</li>
          </ol>
          <p>You get a piano-style visualization of your current range, your historical best, and how much it's changed over 30/90 days — never a definitive classification of your voice type.</p>
        </div>
      </section>

      <section class="block" id="plan">
        <div class="block-head"><span class="block-num">06</span><h2>Your 90-day plan</h2></div>
        <div class="card">
          <p>Once you've picked a track <b>and</b> completed both a recording and a vocal range test, VepAIr builds a 90-day plan under <b>Vocal plan</b> — your goal, a target date, and days remaining.</p>
          <p>On Repair, if your recent data looks consistently stable, VepAIr moves you up to Improvement automatically — always framed as "consistently stable," never "healed." Switch tracks manually any time from onboarding.</p>
          <div class="callout note"><b>Needs both a recent recording and a range test</b> — having just one won't produce a plan yet. The page tells you exactly which one is missing.</div>
        </div>
      </section>

      <section class="block" id="tonematch">
        <div class="block-head"><span class="block-num">07</span><h2>Tone Match & the 5-Tone Challenge</h2></div>
        <div class="card">
          <h3>Free practice</h3>
          <p>Tap <b>Tone Match</b>. Tap any note to hear it, then sing it back — an ungraded, un-tracked practice tool. Nothing here is saved.</p>
          <h3>5-Tone Challenge</h3>
          <p>On the same page, <b>Start the challenge</b> plays 5 notes drawn from <i>your own</i> measured vocal range (not a generic scale) — one every 6 seconds, 30 seconds total. Each note is scored on how close you were, how long you held it, and how fast you found it, for a score out of 100 each (500 total).</p>
          <div class="callout note">
            <b>Needs a vocal range test first.</b> If you haven't mapped your range yet, the
            challenge sends you to <a href="#range">Vocal range mapping</a> instead of starting.
          </div>
          <p>After the round: your total score, a per-note breakdown, and <b>Share</b>/<b>Save</b> buttons for a results card. Unlike free practice, these scores <i>are</i> saved — once you've played 2+ rounds, a trend of your best score per day appears on your home page. This is personal only: no coach ever sees it.</p>
        </div>
      </section>

      <section class="block" id="share">
        <div class="block-head"><span class="block-num">08</span><h2>Share My Progress</h2></div>
        <div class="card">
          <p>After an exercise session (or any time, once you have data), tap <b>Share My Progress</b> — two ready-to-post, vertical (1080×1920) images built entirely from your own real data. Anything you don't have data for is left off, never invented.</p>
          <div class="share-grid">
            <div class="share-item"><b>Page 1 — Today's Voice</b>Today's snapshot</div>
            <div class="share-item"><b>Page 2 — My Progress</b>Start-vs-now comparison</div>
          </div>
          <p><b>Previous/Next</b> to flip between them, then <b>Share</b> (native share sheet, or download), <b>Save</b>, or <b>Save Both</b>.</p>
        </div>
      </section>

      <section class="block" id="progress">
        <div class="block-head"><span class="block-num">09</span><h2>Progress dashboard</h2></div>
        <div class="card">
          <p>Tap <b>Progress</b> for the long view: your VepAIr Score over 7/30/90/180 days, 1 year, or all-time; your current and longest daily training streak with a calendar-style grid; and every exercise's trend (Improving / Declining / Stable / "Not enough data yet"). Always compared against your own history only.</p>
        </div>
      </section>

      <section class="block" id="coach-access">
        <div class="block-head"><span class="block-num">10</span><h2>Sharing with a coach</h2></div>
        <div class="card">
          <p>If a coach invites you, you'll see it under <b>Coach Access</b>. Accepting requires choosing at least one category to share — nothing is selected by default:</p>
          <table class="ref">
            <tr><th>Category</th><th>What it shares</th></tr>
            <tr><td>Recovery trends</td><td>Your VepAIr Score & history</td></tr>
            <tr><td>Vocal range</td><td>Your vocal range history</td></tr>
            <tr><td>Exercise history</td><td>Routine & completion history</td></tr>
            <tr><td>Recordings</td><td>Your voice recordings, for side-by-side comparison</td></tr>
          </table>
          <p>Toggle any category on or off any time from <b>Coach Access</b> — never a full revoke required. <b>Revoke access</b> cuts off everything immediately for anything new (already-viewed data isn't retroactively unshown). Illness/reflux/notes fields and any private journal free-text are <b>never</b> shared, regardless of what you check.</p>
          <p>Your coach may leave you <b>notes</b> — always readable to you, even after you revoke access. You can also <b>message</b> your coach directly, a two-way conversation open to both of you at any time while the connection is active; your own message history stays readable even after a revoke, same as notes.</p>
        </div>
      </section>

      <section class="block" id="reminders">
        <div class="block-head"><span class="block-num">11</span><h2>Practice reminders</h2></div>
        <div class="card">
          <p>Opt in from <b>Settings</b> and VepAIr will email you once a day if you haven't logged a check-in yet — a nudge, not a nag: it never sends twice in one day, and never sends at all once you've checked in. Off by default; turn it on or off any time.</p>
        </div>
      </section>

      <section class="block" id="singer-troubleshooting">
        <div class="block-head"><span class="block-num">12</span><h2>Troubleshooting</h2></div>
        <div class="card">
          <ul>
            <li><b>"I can't sign in"</b> — Login only works with an existing account. A failed login always shows a generic "incorrect email or password" and never confirms whether an account exists, for privacy.</li>
            <li><b>Microphone won't work</b> — check your browser's site permissions. Without a mic, recording and range steps won't work, but check-ins, exercises without live coaching, and viewing progress still do.</li>
            <li><b>"Not enough data yet"</b> — expected early on. Baseline, plan, and trends need a handful of real sessions; VepAIr never fills gaps with invented numbers.</li>
            <li><b>Recording deletion isn't built yet</b> — anything you record stays in your history.</li>
          </ul>
        </div>
      </section>

      <!-- ============ COACH ============ -->
      <div class="role-head coach">
        <div class="rh-mark">C</div>
        <h1>For coaches</h1>
      </div>
      <p class="role-dek">A separate portal for running a roster of Vrotégés who've explicitly chosen to share with you.</p>

      <section class="block coach-section" id="coach-account">
        <div class="block-head"><span class="block-num">01</span><h2>Your coach account</h2></div>
        <div class="card">
          <p>A coach account is separate from a Vrotégé account — created via the public <b>coach signup</b> page, or by an admin. It has its own portal at <code class="path">/coach</code>, not the Vrotégé dashboard. (An admin can also add coach access to an existing Vrotégé account — see <a href="#roles">Roles</a> — in which case you get both.)</p>
          <p>Like any account, <b>Settings</b> lets you download everything VepAIr has on your coach account, or permanently delete it yourself (password + typed confirmation) — no need to contact an admin.</p>
        </div>
      </section>

      <section class="block coach-section" id="coach-pro">
        <div class="block-head"><span class="block-num">02</span><h2>Coach Pro activation</h2></div>
        <div class="card">
          <p>Every coach account needs <b>Coach Pro</b> active to use anything in the portal — there's no free tier. A brand-new account sees:</p>
          <div class="callout coach"><b>"Your account is pending activation"</b> — your account has been created but isn't active yet. Contact VepAIr to get started.</div>
          <p>Coach billing goes through VepAIr directly (invoiced separately, not automated card billing) — once that's sorted, an admin flips your account active and you're straight into the portal, no re-signup needed. Included with an active subscription: <b>50 Vrotégé invites per year</b>; sending more than 50 doesn't block you, it's simply tracked as overage for billing.</p>
        </div>
      </section>

      <section class="block coach-section" id="coach-invite">
        <div class="block-head"><span class="block-num">03</span><h2>Inviting a Vrotégé</h2></div>
        <div class="card">
          <p><b>Invite a Vrotégé</b> on your dashboard. Enter their email (they must already have a VepAIr Vrotégé account) and an optional message.</p>
          <p>They see your invite under their own <b>Coach Access</b> page and must explicitly accept, choosing what to share — you see nothing until they do. Cancel a still-pending invite any time from your dashboard.</p>
        </div>
      </section>

      <section class="block coach-section" id="coach-roster">
        <div class="block-head"><span class="block-num">04</span><h2>Your roster</h2></div>
        <div class="card">
          <p>Your dashboard lists every Vrotégé who's accepted, with a one-line summary of what they've shared. Tap any Vrotégé to open their dashboard. <b>Remove from roster</b> drops your access immediately — it never deletes anything of the Vrotégé's; they can re-invite you later if they choose.</p>
        </div>
      </section>

      <section class="block coach-section" id="coach-singer-view">
        <div class="block-head"><span class="block-num">05</span><h2>A Vrotégé's dashboard</h2></div>
        <div class="card">
          <p>Each section shows real data if the matching category is shared, or <b>"Not shared"</b> if it isn't — never a guess, never blank-by-omission:</p>
          <table class="ref">
            <tr><th>Section</th><th>Needs</th></tr>
            <tr><td>VepAIr Score</td><td>Recovery trends</td></tr>
            <tr><td>Vocal range & target tones</td><td>Vocal range</td></tr>
            <tr><td>Exercise trends, training consistency, today's routine</td><td>Exercise history</td></tr>
          </table>
          <p>From here: <b>Progress</b> (full trend charts over any range), <b>Recordings</b> (play a shared recording — streamed live, VepAIr never keeps a second copy of a Vrotégé's audio), <b>Assign training</b>, <b>Notes</b>, and <b>Messages</b>.</p>
        </div>
      </section>

      <section class="block coach-section" id="coach-assign">
        <div class="block-head"><span class="block-num">06</span><h2>Assign training</h2></div>
        <div class="card">
          <p>Select one or more exercises, an optional target tone per exercise, and an optional note to the Vrotégé. <b>+ Add custom exercise</b> lets you write your own (title, instructions, category, duration, difficulty) — it's immediately available to select and assign.</p>
          <div class="callout coach">An assignment is included in the Vrotégé's routine only where <i>today's own safety limits</i> already allow it — an assignment can never push a Vrotégé past what would be safe for them today, regardless of what you assign.</div>
        </div>
      </section>

      <section class="block coach-section" id="coach-notes">
        <div class="block-head"><span class="block-num">07</span><h2>Notes</h2></div>
        <div class="card">
          <p>Short, plain-text observations the Vrotégé can read too — up to 2000 characters, permanent once saved (delete removes it from view, mistakes aren't silently rewritten).</p>
          <div class="callout warn"><b>Not a medical or clinical record.</b> Never record diagnoses, medical history, or clinical assessments here. Language that reads as clinical is flagged (still saves, but shown as "flagged for review") — rephrase as an observation or a suggestion to see a professional.</div>
        </div>
      </section>

      <section class="block coach-section" id="coach-messages">
        <div class="block-head"><span class="block-num">08</span><h2>Messages</h2></div>
        <div class="card">
          <p>A real back-and-forth with your Vrotégé, separate from Notes — up to 2000 characters per message, both of you can send and read. Sending requires an active connection (a revoked Vrotégé can't be messaged), but a Vrotégé's own read access to the history you already exchanged never goes away, same as Notes.</p>
          <div class="callout warn"><b>Not a medical or clinical record.</b> Same non-blocking clinical-language flag as Notes — a flagged message still sends, just marked "flagged for review" on both sides.</div>
        </div>
      </section>

      <section class="block coach-section" id="coach-privacy">
        <div class="block-head"><span class="block-num">09</span><h2>What you can never see</h2></div>
        <div class="card">
          <p>Regardless of what a Vrotégé shares, these are never visible to any coach, ever: illness symptoms, reflux symptoms, and any private free-text notes from a Vrotégé's own check-ins or recording sessions. This is a code-level omission, not a togglable setting.</p>
        </div>
      </section>

      <!-- ============ ADMIN ============ -->
      <div class="role-head admin">
        <div class="rh-mark">A</div>
        <h1>For admins</h1>
      </div>
      <p class="role-dek">Operational access, not a coach-style sharing relationship — an admin can act on any account without that user's consent. In exchange, every state-changing action is written to an append-only audit log before it takes effect.</p>

      <section class="block admin-section" id="bootstrap">
        <div class="block-head"><span class="block-num">01</span><h2>Granting the first admin</h2></div>
        <p class="block-note">No button for this, on purpose — a one-time manual step against the production database.</p>
        <div class="card">
          <p>Connect with the Session pooler string from <code class="path">TECHNICAL_GUIDE.md</code> §8, then:</p>
          <pre><code>UPDATE users SET is_admin = true WHERE email = '&lt;your account's email&gt;';</code></pre>
          <p>No restart, no redeploy — the next request that account makes is treated as an admin. Log in normally, then go to <code class="path">/admin</code> directly (there's no nav link to it).</p>
          <div class="callout warn"><b>No self-serve or API path to grant admin, ever, by design.</b> A second admin later is this same manual step — see <a href="#roles">Roles</a> for how every admin after the first is granted through the UI instead.</div>
        </div>
      </section>

      <section class="block admin-section" id="search">
        <div class="block-head"><span class="block-num">02</span><h2>Finding an account</h2></div>
        <div class="card">
          <div class="endpoint"><span class="chip get">GET</span><span class="path">/api/v1/admin/users?query=</span></div>
          <p>Type any substring of an email into the search box on <code class="path">/admin</code> — capped at the 100 most recent signups; blank + search lists recent signups. Click a result to open <code class="path">/admin/users/{id}</code>, with account type, onboarding completeness, and three activity fields:</p>
          <table class="ref">
            <tr><th>Field</th><th>What it actually is</th></tr>
            <tr><td class="code-cell">last_session_at</td><td>Real last-login, from the <code class="path">login_events</code> table — written only by a password-based login, never signup or a token refresh.</td></tr>
            <tr><td class="code-cell">last_checkin_date</td><td>Most recent Daily Check-In date.</td></tr>
            <tr><td class="code-cell">last_recording_at</td><td>Most recent uploaded recording's timestamp.</td></tr>
          </table>
        </div>
      </section>

      <section class="block admin-section" id="lifecycle">
        <div class="block-head"><span class="block-num">03</span><h2>Deactivate / reactivate</h2></div>
        <p class="block-note">Soft, instant, fully reversible — the everyday lever for a locked-out or reported account.</p>
        <div class="card">
          <div class="lifecycle">
            <span class="lc-state active">active</span>
            <span class="lc-arrow">— Deactivate →</span>
            <span class="lc-state inactive">deactivated</span>
            <span class="lc-arrow">← Reactivate —</span>
            <span class="lc-state active">active</span>
          </div>
          <ol class="steps">
            <li>On the account's detail page, select <span class="ui-btn outline">Deactivate</span>. Every refresh token is revoked immediately and <code>is_active</code> flips to false.</li>
            <li>The account is locked out from that instant — an existing session gets <code>401</code> on its next request; logging back in fails the same way, even with the correct password.</li>
            <li><span class="ui-btn outline">Reactivate</span> reverses it — the account signs in normally again right away.</li>
          </ol>
          <div class="callout info">Nothing about deactivation touches the account's data — recordings, history, and settings come right back on reactivation. A lock on the door, not a demolition.</div>
          <p><b>Bulk deactivate / reactivate</b>: check the boxes next to multiple rows in the search results — a bar appears with <span class="ui-btn outline">Deactivate selected</span> / <span class="ui-btn outline">Reactivate selected</span>, confirming the exact list of emails before it fires. Deliberately the only two bulk actions in the whole admin surface — hard-delete and granting admin both stay single-account, on purpose, so a misclick can't do either at scale. One audit-log row is still written per account, not one for the whole batch.</p>
        </div>
      </section>

      <section class="block admin-section" id="roles">
        <div class="block-head"><span class="block-num">04</span><h2>Roles & dual-role accounts</h2></div>
        <div class="card">
          <p>On any account's detail page, the <b>Roles</b> section grants or revokes:</p>
          <table class="ref">
            <tr><th>Action</th><th>Endpoint</th></tr>
            <tr><td>Grant / revoke admin</td><td class="code-cell">POST /api/v1/admin/users/{id}/set-admin</td></tr>
            <tr><td>Make / remove coach</td><td class="code-cell">POST /api/v1/admin/users/{id}/set-coach</td></tr>
          </table>
          <p>An admin can't target their own account with either (self-lockout prevention). <b>Make coach</b> attaches a coach profile to any existing account — including an already-onboarded Vrotégé, producing a genuine dual-role account that sees the full Vrotégé dashboard plus a Coach Portal quick-link.</p>
          <div class="callout warn"><b>Removing coach status deletes that coach's profile</b>, which cascades to any custom exercise they authored. The UI confirms this explicitly before you can proceed.</div>
          <p><b>Admin tiers</b>: granting admin now also sets a tier, shown as a dropdown once an account is an admin. <b>Full</b> is everything on this page. <b>Support</b> can search accounts, view reports and detail pages, deactivate/reactivate (including in bulk), and send password resets — never hard-delete, grant/revoke admin, make/remove coach, set a password directly, impersonate, export the contact list, or touch site settings. Revoking admin entirely clears the tier.</p>
        </div>
      </section>

      <section class="block admin-section" id="impersonate">
        <div class="block-head"><span class="block-num">05</span><h2>Viewing as a user</h2></div>
        <p class="block-note">Full admins only. Read-only, and deliberately shows nothing about voice health.</p>
        <div class="card">
          <div class="endpoint"><span class="chip post">POST</span><span class="path">/api/v1/admin/users/{id}/impersonate</span></div>
          <ol class="steps">
            <li>On the account's detail page, select <span class="ui-btn outline">View as this user</span>.</li>
            <li>A banner reading "Viewing as ... as an admin" stays on screen the whole time, with an <span class="ui-btn outline">Exit impersonation</span> control.</li>
            <li>The page shows account-setup and engagement facts only — practice frequency, musical style, and a 7-day check-in count. No recovery score, no check-in wellness values, nothing that reads as a health or medical status, on purpose.</li>
          </ol>
          <div class="callout warn"><b>Read-only, enforced by the backend, not just the UI</b> — the token this issues can only make GET requests; any attempt to change data 403s with <code class="mono">impersonation_read_only</code>, regardless of which endpoint it hits. It also expires automatically (same window as a normal login) and is never usable to reach back into anything admin-only, since it authenticates as the target account, not the admin's own.</div>
          <p>Every session writes its own audit rows — <code class="mono">impersonate_start</code> when it begins, <code class="mono">impersonate_end</code> when you exit — separate from a normal admin login, so both are independently searchable in the audit trail.</p>
        </div>
      </section>

      <section class="block admin-section" id="reset">
        <div class="block-head"><span class="block-num">06</span><h2>Sending a password reset</h2></div>
        <div class="card">
          <div class="endpoint"><span class="chip post">POST</span><span class="path">/api/v1/admin/users/{id}/send-password-reset</span></div>
          <p>Select <span class="ui-btn outline">Send password reset</span> on the account's detail page — the same reset-token + email flow as the user's own "forgot password," triggered on their behalf and audit-logged. Works whether the account is active or deactivated.</p>
        </div>
      </section>

      <section class="block admin-section" id="delete">
        <div class="block-head"><span class="block-num">07</span><h2>Permanently deleting an account</h2></div>
        <p class="block-note">Irreversible. Requires the account to already be deactivated — not a bug if the button looks disabled.</p>
        <div class="card">
          <div class="lifecycle">
            <span class="lc-state active">active</span>
            <span class="lc-arrow">Delete →</span>
            <span class="lc-state inactive" style="opacity:.5">409 must_deactivate_first</span>
          </div>
          <div class="lifecycle">
            <span class="lc-state inactive">deactivated</span>
            <span class="lc-arrow">Delete →</span>
            <span class="lc-state gone">gone</span>
          </div>
          <ol class="steps">
            <li><b>Deactivate first</b> — the delete button stays disabled until you do.</li>
            <li>Once deactivated, select <span class="ui-btn danger">Delete this account</span>, then type <code class="mono">DELETE</code> to confirm.</li>
            <li>Deletes every recording's actual audio file, then the account itself, cascading through every other table scoped to it — the same routine a user's own "Delete my account" uses.</li>
          </ol>
          <div class="callout warn">No undo. The audit log entry survives (it captures the account's email before the row is gone), but the account itself does not.</div>
        </div>
      </section>

      <section class="block admin-section" id="orgs">
        <div class="block-head"><span class="block-num">08</span><h2>Organizations & Coach Pro</h2></div>
        <p class="block-note">Every coach belongs to one Organization — this is where you turn their access on.</p>
        <div class="card">
          <ol class="steps">
            <li>Go to <code class="path">/admin</code> → <b>Organizations</b>.</li>
            <li>Search by org name, coach email, or coach name (blank search lists the 100 most recent).</li>
            <li>Click into the org, then <span class="ui-btn outline">Activate Coach Pro</span>.</li>
          </ol>
          <p>Sets a 12-month period from that moment and unblocks the coach's portal immediately — no redeploy, no re-login needed on their end. <span class="ui-btn outline">Deactivate Coach Pro</span> reverses it, locking them out again without touching any of their data or their Vrotégés' data.</p>
          <p>The same page shows invites used this period vs. the 50 included — going over doesn't block anything, it accrues as billable overage.</p>
          <div class="callout note">There's no automatic payment signal (billing isn't card-based on the coach side) — activation is always a manual step, done once payment is confirmed outside the app.</div>
        </div>
      </section>

      <section class="block admin-section" id="reports">
        <div class="block-head"><span class="block-num">09</span><h2>Reports</h2></div>
        <div class="card">
          <div class="endpoint"><span class="chip get">GET</span><span class="path">/api/v1/admin/reports/summary</span></div>
          <p><code class="path">/admin/reports</code> is read-only aggregate SQL over existing tables:</p>
          <div class="stat-grid">
            <div class="stat"><div class="k">Total users</div><div class="v">Vrotégé + coach</div></div>
            <div class="stat"><div class="k">Active / deactivated</div><div class="v">is_active split</div></div>
            <div class="stat"><div class="k">Onboarding completion</div><div class="v">has profile</div></div>
            <div class="stat"><div class="k">Signups, 7d / 90d</div><div class="v">rolling windows</div></div>
            <div class="stat"><div class="k">DAU / WAU</div><div class="v">engagement metric</div></div>
          </div>
          <p>Below the top stats, a <b>filterable query</b> lets you combine any of: email substring, account type, active/admin/onboarding-complete flags, and signup date range — every filter is AND-ed together, capped at 200 rows.</p>
          <div class="callout note"><b>DAU/WAU count product engagement, not raw logins</b> — distinct accounts with a check-in or recording in the last 1/7 days. A real <code class="path">login_events</code> table exists now (see "Finding an account" above for per-account last-login), but DAU/WAU deliberately keeps this definition — someone using the app all day on one login would undercount on a pure-login metric.</div>
          <p><b>Export contact list (CSV)</b>, full admins only: the same filters as the query above, uncapped, downloaded as email-addresses-only — this app keeps no other contact PII, so there's nothing else to export. The one action on this whole page that hands raw data out of the system as a file, so it's logged with hard-delete-level rigor: the filters used, never the emails themselves.</p>
        </div>
      </section>

      <section class="block admin-section" id="site-settings">
        <div class="block-head"><span class="block-num">10</span><h2>Site settings</h2></div>
        <div class="card">
          <p>At the top of <code class="path">/admin</code>:</p>
          <ul>
            <li><b>Signup lockdown</b> — turns off the public <code class="path">/signup</code> and <code class="path">/coach-signup</code> forms (both return "signups disabled"). Admin-created accounts still work — this gates the public forms only, not you deliberately creating an account.</li>
            <li><b>Beta NDA gate</b> — whether every user must accept the beta confidentiality notice before using the app. Turn off once the beta period ends.</li>
            <li><b>Data retention</b> — how many days raw recording audio, the most sensitive check-in free-text fields (illness/reflux/notes), and login history are kept before the daily purge job removes them (90, 30, and 365 by default). Editing any of the three takes effect on the job's next run, no redeploy needed.</li>
          </ul>
        </div>
      </section>

      <section class="block admin-section" id="audit">
        <div class="block-head"><span class="block-num">11</span><h2>The audit trail</h2></div>
        <div class="card">
          <p>Every deactivate, reactivate, delete, role change, password-reset, impersonation, and contact-list export writes one row to <code class="path">admin_audit_log</code> before the action commits — including one row per account for a bulk deactivate/reactivate, never one row for the whole batch. No UI for this yet — query it directly:</p>
          <pre><code>SELECT admin_user_id, action, target_user_id, details, created_at
FROM admin_audit_log
ORDER BY created_at DESC
LIMIT 50;</code></pre>
          <p><code>details</code> captures the target account's email at the time of the action — so even after a hard delete sets <code>target_user_id</code> to null, the row still says whose account it was.</p>
        </div>
      </section>

      <section class="block admin-section" id="gaps" style="margin-bottom: 0;">
        <div class="block-head"><span class="block-num">12</span><h2>Known gaps (not built yet)</h2></div>
        <div class="card">
          <p>Deliberately deferred:</p>
          <ul>
            <li>QuickBooks Online sync for Coach Pro invoicing — overage is tracked but not yet auto-invoiced</li>
          </ul>
        </div>
      </section>
    </main>
  </div>
</div>

<footer>
  <div class="shell">
    Admin access is itself access to user data — see <code class="path">PRIVACY.md</code> §4 for
    how this reconciles with the app's own privacy commitments. This guide documents VepAIr as of
    2026-08-26; if the app has drifted from what's described here, the running product is the
    source of truth, not this page.
  </div>
</footer>

</html>`;
