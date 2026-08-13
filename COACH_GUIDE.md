# VepAIr Coach Guide

A guide to VepAIr Coach — what it gives you as a vocal coach, teacher, or studio, and how each
piece actually helps your teaching. For the technical reference, see
[`ARCHITECTURE.md`](ARCHITECTURE.md); for what VepAIr looks like from a singer's side, see
[`USER_GUIDE.md`](USER_GUIDE.md).

VepAIr Coach is **not** a medical or clinical tool, and it never asks you to be one. It's a way
to see the same objective, longitudinal data your students already have about their own
voice — and to stay connected to their practice between lessons — without ever asking you to
diagnose anything or make a medical call. See [`MEDICAL_SAFETY.md`](MEDICAL_SAFETY.md) for the
rules that hold everywhere in the app, including here.

## Why this exists

Right now, most of what happens between lessons is invisible to you. A student practices (or
doesn't), their voice has a good day or a bad day, they show up to the next session and you're
reconstructing the last week from memory and how they sound in the room. VepAIr Coach closes
that gap: real measurements, real practice history, and a way to guide what happens between
sessions — all built on the same data your student already sees on their own dashboard, never a
separate or lesser copy of it.

## Getting started

### A coach account is its own thing

You sign up separately from a singer account, at `/coach-signup` — name, optional studio name,
email, and password. This isn't a toggle on top of a regular account: a coach account is a coach
account from the moment it's created, which is also what keeps the boundary clean between "my
own voice data" and "a student's voice data I've been given access to."

### Invite a student — they choose to accept

You invite a singer by their email from your dashboard. Nothing happens automatically: the
invite sits pending until they explicitly accept it. This isn't just a technical formality — it
means every student on your roster chose to be there, and chose what to share with you. That's
worth knowing when a student's data looks different from what you'd expect: you're seeing
exactly what they decided to show you, honestly, not a default "share everything" dump.

### They choose exactly what you see

When a student accepts your invite, they pick from four independent categories — nothing is
shared by default:

| Category | What you'd see |
|---|---|
| **Recovery trends** | Their daily VepAIr Score and score history |
| **Vocal range** | Comfortable low/high range, historical best, recent change |
| **Exercise history** | Routine completion, per-exercise trends, training streaks |
| **Recordings** | Their uploaded practice/session recordings, playable |

A student can turn any one of these on or off at any time without fully disconnecting from you —
so if your dashboard is missing something you'd expect (like recordings), that's a real signal
about what they're comfortable sharing right now, not a bug.

## What you get, feature by feature

### A real dashboard per student — not a summary, the actual data

Once a student shares a category with you, you see the exact same numbers and charts they see on
their own dashboard: their VepAIr Score and trend, comfortable vocal range, per-exercise
improving/declining/stable classification, training streaks, and today's adaptive routine. This
is deliberately built to be the *same* underlying calculation as the singer's own view, not a
simplified or separate coach-facing summary — so what you're discussing in a lesson always
matches what your student is looking at on their phone.

**Why it helps you**: you walk into every lesson already knowing whether a student's voice has
been stable or under strain, whether they've actually been practicing, and where their range has
moved — instead of starting from "so, how's it been going?"

### Listen to their practice recordings

If a student shares recordings with you, you can play back their actual guided-session audio
directly from their dashboard — a live link to their own recording, not a copy handed to you.
VepAIr never makes or stores a separate copy of a student's voice for you to keep: there's
exactly one copy of any recording, ever, and it stays theirs. If they turn off the recordings
category or disconnect from you, that link stops working immediately, same as everything else.

**Why it helps you**: you can hear technique between lessons, not just take their word for how
practice went, and catch something worth addressing before it becomes a habit — without your
student having to worry about their voice ending up somewhere outside their own account.

### Assign training that's automatically safety-checked

You can assign specific exercises for a student's next routine, with an optional note explaining
why. Here's the part that matters: an assignment can never push a student past what VepAIr's own
safety system already thinks is appropriate for them that day. If a student reports high
discomfort or their recent data looks strained, the app will still hold back an assigned
exercise exactly the way it would for its own adaptive routine — and it tells the student plainly
when that's happened, never silently.

**Why it helps you**: you can direct a student's between-lesson practice without having to
personally track whether today happens to be a bad day for them — the system already does that,
and it can't be talked out of it, including by you.

### Write notes your student actually sees

You can leave notes tied to a specific student — visible to them, plain and simple. Notes are
capped at 2,000 characters, can't be silently edited after the fact (a correction is a new note,
and a mistake can be withdrawn), and the system gently flags clinical-sounding language before
it saves (it still saves — this is a nudge toward "have them see a doctor" phrasing, not a
blocker).

**Why it helps you**: continuity. A note like "great breath support today, keep favoring the
lower larynx position we worked on" is something your student can come back to on their own time,
not something that only existed in the room for 45 minutes.

### One roster, one place

Your dashboard lists every student who's accepted your invite, plus any invites still pending, so
you always know where things stand without having to ask.

### Honest about what revoke means

A student can turn off a category, or disconnect from you entirely, at any time — and if they
do, your access to *new* data stops immediately. What already rendered in your browser before
that point isn't retroactively hidden (there's no way to unshow something you've already seen),
and the app's own copy says so plainly rather than pretending otherwise. Notes you've written
stay visible to the student even after a disconnect — that part of the relationship doesn't
disappear.

## What VepAIr Coach deliberately never gives you

- **No diagnosis, ever** — not from VepAIr's own numbers, and the system actively discourages you
  from writing one in a note.
- **No override of safety limits** — an assignment that would push a student too hard on a given
  day simply doesn't apply that day, full stop.
- **No access without consent** — not by default, not automatically because you know a student,
  and never retroactive.
- **No hidden fields** — journal entries about illness, reflux, or private notes a student wrote
  for themselves are never visible to you, regardless of what they've shared. That's not a
  setting you can turn on; it's built to never be readable by a coach account at all.

## Where this stands today

VepAIr Coach just launched as an early, invite-based pilot — you're among the first coaches using
it, which also means the feature set above is genuinely everything that exists right now, not a
trimmed-down preview of something bigger already live elsewhere. Training assignment, notes, and
per-category sharing are all real and working today, not roadmap items.

## Getting started, concretely

1. Go to `/coach-signup` and create your coach account.
2. From your dashboard, invite a student by the email they use for their own VepAIr account.
3. Once they accept, their shared data appears on your dashboard automatically — no further setup.
4. Assign training or leave a note any time from their individual page.
