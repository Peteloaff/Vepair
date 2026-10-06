"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/Card";
import { CheckInForm } from "@/components/CheckInForm";
import { Icon, IconTile, type IconName, type TileColor } from "@/components/icons";
import { GoalTonesCard } from "@/components/GoalTonesCard";
import { RecoveryScoreCard } from "@/components/RecoveryScoreCard";
import { ToneGameTrendCard } from "@/components/ToneGameTrendCard";
import { TrendChart, type TrendPoint } from "@/components/TrendChart";
import { VocalBaseline } from "@/components/VocalBaseline";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/apiClient";
import { daysAgoLocalDate, lastNDates, todayLocalDate } from "@/lib/date";
import type {
  BaselineSummary,
  CheckIn,
  CheckInInput,
  CoachConnection,
  Profile,
  RecoveryScore as RecoveryScoreData,
  RestCheck,
  SingerInvite,
  VocalGoal,
  VocalPlanView,
} from "@/lib/types";

const RANGE_OPTIONS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
] as const;

const TRACK_LABEL: Record<string, string> = {
  repair: "Vocal Repair",
  improvement: "Vocal Improvement",
};

function daysRemaining(targetEndDate: string): number {
  const ms = new Date(targetEndDate).getTime() - Date.now();
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
}

function buildSeries(history: CheckIn[], dates: string[], metric: keyof CheckIn): TrendPoint[] {
  const byDate = new Map(history.map((c) => [c.checkin_date, c]));
  return dates.map((date) => {
    const c = byDate.get(date);
    const raw = c ? c[metric] : null;
    return { date, value: typeof raw === "number" ? raw : null };
  });
}

function greetingFor(hour: number): string {
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function PlanRow({
  href,
  icon,
  color,
  title,
  subtitle,
  tag,
}: {
  href: string;
  icon: IconName;
  color: TileColor;
  title: string;
  subtitle: string;
  tag?: React.ReactNode;
}) {
  return (
    <li>
      <Link
        href={href}
        className="flex items-center gap-3.5 rounded-2xl border border-border bg-surface-2 px-3.5 py-3 transition-colors hover:border-border-strong"
      >
        <IconTile name={icon} color={color} />
        <span className="min-w-0 flex-1">
          <span className="block font-medium">{title}</span>
          <span className="block truncate text-xs text-text-faint">{subtitle}</span>
        </span>
        {tag}
        <Icon name="chev" className="h-5 w-5 text-text-faint" />
      </Link>
    </li>
  );
}

function ScoreSnapshot({
  label,
  score,
  tone,
}: {
  label: string;
  score: RecoveryScoreData | null;
  tone: "ok" | "warning";
}) {
  const factors = score?.factors.slice(0, 3) ?? [];
  return (
    <div className="rounded-2xl border border-border bg-surface-2 p-4">
      <p
        className={`text-xs font-semibold uppercase tracking-wider ${
          tone === "ok" ? "text-ok" : "text-warning"
        }`}
      >
        {label}
      </p>
      <p className="font-display mt-1 text-4xl leading-tight tracking-tight tabular-nums">
        {score?.score_value ?? "—"}
      </p>
      <p className="mb-3 text-xs text-text-faint">{score?.status_label ?? "No score"}</p>
      <ul className="space-y-2 text-sm text-text-dim">
        {factors.length === 0 && <li className="text-text-faint">Nothing to compare yet.</li>}
        {factors.map((f) => (
          <li key={f.text} className="flex items-start gap-2">
            <Icon
              name={f.direction === "positive" ? "check" : "alert"}
              className={`mt-0.5 h-4 w-4 ${
                f.direction === "positive" ? "text-ok" : "text-warning"
              }`}
            />
            <span>{f.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Dashboard({
  isCoachView = false,
  showCoachPortalLink = false,
}: {
  isCoachView?: boolean;
  showCoachPortalLink?: boolean;
}) {
  const { apiFetch, user } = useAuth();
  const [history, setHistory] = useState<CheckIn[] | null>(null);
  const [baseline, setBaseline] = useState<BaselineSummary | null>(null);
  const [baselineError, setBaselineError] = useState(false);
  const [recoveryScore, setRecoveryScore] = useState<RecoveryScoreData | null>(null);
  const [recoveryScoreError, setRecoveryScoreError] = useState(false);
  const [yesterdayScore, setYesterdayScore] = useState<RecoveryScoreData | null>(null);
  const [planView, setPlanView] = useState<VocalPlanView | null>(null);
  const [planError, setPlanError] = useState(false);
  const [goal, setGoal] = useState<VocalGoal | null>(null);
  const [goalError, setGoalError] = useState(false);
  const [restCheck, setRestCheck] = useState<RestCheck | null>(null);
  const [pendingInviteCount, setPendingInviteCount] = useState(0);
  const [hasCoachConnection, setHasCoachConnection] = useState(false);
  const [unreadMessageCount, setUnreadMessageCount] = useState(0);
  const [profileMissing, setProfileMissing] = useState(false);
  const [rangeDays, setRangeDays] = useState<number>(30);
  const [editingToday, setEditingToday] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const today = todayLocalDate();

  async function loadHistory() {
    try {
      const rows = await apiFetch<CheckIn[]>("/api/v1/checkins", {
        searchParams: { from_date: daysAgoLocalDate(90), to_date: today },
      });
      setHistory(rows);
    } catch {
      setLoadError("Could not load your check-in history.");
    }
  }

  async function loadRecoveryScore() {
    try {
      const score = await apiFetch<RecoveryScoreData>("/api/v1/recovery-score", {
        searchParams: { date: today },
      });
      setRecoveryScore(score);
      setRecoveryScoreError(false);
    } catch {
      setRecoveryScoreError(true);
    }
  }

  useEffect(() => {
    // A coach account has none of this singer-only data (no UserProfile, check-ins, baseline,
    // vocal plan, goal tones, or routine) -- every one of these calls would just fail for it,
    // so skip them entirely rather than showing a wall of "could not load" errors.
    if (isCoachView) return;
    // Data-fetch-on-mount: setHistory/setLoadError run after an awaited network call inside
    // loadHistory, not synchronously in this effect body — the intentional "fetch on mount"
    // pattern the set-state-in-effect rule can't see through a named async function call.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadHistory();
    loadRecoveryScore();
    apiFetch<RecoveryScoreData>("/api/v1/recovery-score", {
      searchParams: { date: daysAgoLocalDate(1) },
    })
      .then(setYesterdayScore)
      .catch(() => {
        // Best-effort -- the comparison card just shows today on its own.
      });
    apiFetch<Profile>("/api/v1/profile").catch((err) => {
      if (err instanceof ApiError && err.code === "profile_not_found") {
        setProfileMissing(true);
      }
    });
    apiFetch<BaselineSummary>("/api/v1/baseline")
      .then(setBaseline)
      .catch(() => setBaselineError(true));
    apiFetch<VocalPlanView>("/api/v1/vocal-plan")
      .then(setPlanView)
      .catch(() => setPlanError(true));
    apiFetch<VocalGoal>("/api/v1/vocal-goals")
      .then(setGoal)
      .catch(() => setGoalError(true));
    apiFetch<RestCheck>("/api/v1/routine/rest-check", { searchParams: { date: today } })
      .then(setRestCheck)
      .catch(() => {
        // Best-effort — the rest of the dashboard still works without this banner.
      });
    // Stage 12 Phase II (dev-only): a coach-sent invite is easy to miss, so a badge on the
    // nav link is worth the extra request — silently ignored if it fails, same as every
    // other best-effort fetch on this dashboard.
    apiFetch<SingerInvite[]>("/api/v1/invites")
      .then((invites) => setPendingInviteCount(invites.length))
      .catch(() => {});
    // A singer with no invite ever received and no existing coach connection has nothing to
    // do on /coach-access, so the nav link itself is confusing clutter -- only show it once
    // there's actually something there (a pending invite, from the fetch above, or a
    // connection, active or revoked, checked here).
    apiFetch<CoachConnection[]>("/api/v1/coach-connections")
      .then((connections) => {
        setHasCoachConnection(connections.length > 0);
        setUnreadMessageCount(
          connections.reduce((sum, c) => sum + c.unread_message_count, 0)
        );
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const todaysCheckIn = useMemo(
    () => history?.find((c) => c.checkin_date === today) ?? null,
    [history, today]
  );

  const dates = useMemo(() => lastNDates(rangeDays), [rangeDays]);
  const filteredHistory = useMemo(
    () => (history ?? []).filter((c) => dates.includes(c.checkin_date)),
    [history, dates]
  );

  async function handleCreate(values: Omit<CheckInInput, "checkin_date">) {
    await apiFetch<CheckIn>("/api/v1/checkins", {
      method: "POST",
      body: { checkin_date: today, ...values },
    });
    await Promise.all([loadHistory(), loadRecoveryScore()]);
  }

  async function handleUpdate(values: Omit<CheckInInput, "checkin_date">) {
    if (!todaysCheckIn) return;
    await apiFetch<CheckIn>(`/api/v1/checkins/${todaysCheckIn.id}`, {
      method: "PATCH",
      body: values,
    });
    setEditingToday(false);
    await Promise.all([loadHistory(), loadRecoveryScore()]);
  }

  if (isCoachView) {
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-10">
        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">VepAIr</h1>
            <p className="mt-1 text-sm text-text-dim">
              Signed in as a coach{user?.email ? ` (${user.email})` : ""}.
            </p>
          </div>
          <Link
            href="/coach"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
          >
            Go to Coach Portal &rarr;
          </Link>
        </div>

        <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
          <h2 className="mb-2 text-sm font-medium text-text">Coach Portal</h2>
          <p className="text-sm text-text-dim">
            Manage your Vrotégé roster, send invites, assign training, and write notes from your
            Coach Portal — a coach account doesn&apos;t have its own voice check-in or exercise
            data the way a Vrotégé account does.
          </p>
          <Link
            href="/coach"
            className="mt-4 inline-block rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2"
          >
            Go to Coach Portal &rarr;
          </Link>
        </section>
      </main>
    );
  }

  const now = new Date();
  const dateLabel = now.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  const coachAccessBadge = pendingInviteCount + unreadMessageCount;
  const tileLinkClass =
    "flex flex-col gap-3 rounded-[18px] border border-border bg-surface p-4 text-sm font-semibold transition-colors hover:border-border-strong hover:bg-surface-2";

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-normal tracking-tight sm:text-4xl">
            {greetingFor(now.getHours())}
            {user?.username ? `, ${user.username}` : ""}
          </h1>
          <p className="mt-1 text-sm text-text-dim">
            {dateLabel}
            {todaysCheckIn ? " · Check-in saved" : " · No check-in yet today"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/exercises"
            className="inline-flex items-center gap-2 rounded-xl border border-border-strong px-4 py-2.5 text-sm font-semibold hover:bg-surface-2"
          >
            <Icon name="wave" className="h-4 w-4" />
            Today&apos;s routine
          </Link>
          <Link
            href="/record"
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-ink"
          >
            <Icon name="mic" className="h-4 w-4" />
            Record voice sample
          </Link>
        </div>
      </div>

      {profileMissing && (
        <Link
          href="/onboarding"
          className="mb-4 block rounded-2xl border border-accent bg-accent-faint px-4 py-3 text-sm text-accent"
        >
          Finish setting up your profile &rarr;
        </Link>
      )}

      {restCheck?.rest_day_recommended && (
        <div className="mb-4 rounded-2xl bg-danger-faint px-4 py-3 text-sm text-danger">
          {restCheck.rest_day_reason}
        </div>
      )}

      {loadError && (
        <p className="mb-4 rounded-xl bg-danger-faint px-3 py-2 text-xs text-danger">{loadError}</p>
      )}

      <nav
        aria-label="Shortcuts"
        className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6"
      >
        {(
          [
            { href: "/progress", label: "Progress", icon: "chart", color: "blue" },
            { href: "/vocal-plan", label: "Vocal plan", icon: "plan", color: "violet" },
            { href: "/vocal-range", label: "Vocal range", icon: "range", color: "teal" },
            { href: "/tone-match", label: "Tone Match", icon: "game", color: "amber" },
            { href: "/recordings", label: "Recordings", icon: "rec", color: "cyan" },
          ] as { href: string; label: string; icon: IconName; color: TileColor }[]
        ).map((q) => (
          <Link key={q.href} href={q.href} className={tileLinkClass}>
            <IconTile name={q.icon} color={q.color} size="sm" />
            {q.label}
          </Link>
        ))}
        {showCoachPortalLink && (
          <Link href="/coach" className={tileLinkClass}>
            <IconTile name="users" color="violet" size="sm" />
            Coach Portal
          </Link>
        )}
        {(pendingInviteCount > 0 || hasCoachConnection) && (
          <Link href="/coach-access" className={`relative ${tileLinkClass}`}>
            <IconTile name="users" color="violet" size="sm" />
            Coach Access
            {coachAccessBadge > 0 && (
              <span className="absolute right-3 top-3 flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-xs font-semibold text-accent-ink">
                {coachAccessBadge}
              </span>
            )}
          </Link>
        )}
      </nav>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card title="VepAIr Score" className="lg:col-span-5">
          {recoveryScoreError ? (
            <p className="text-sm text-text-faint">Could not load today&apos;s score.</p>
          ) : (
            <RecoveryScoreCard score={recoveryScore} />
          )}
        </Card>

        <Card title="Yesterday and today" meta="vs. your own baseline" className="lg:col-span-7">
          <div className="grid gap-4 sm:grid-cols-2">
            <ScoreSnapshot label="Yesterday" score={yesterdayScore} tone="ok" />
            <ScoreSnapshot label="Today" score={recoveryScore} tone="warning" />
          </div>
        </Card>

        <Card title="Today's plan" className="lg:col-span-7">
          {planError ? (
            <p className="text-sm text-text-faint">Could not load your vocal plan.</p>
          ) : planView === null ? (
            <p className="text-sm text-text-faint">Loading...</p>
          ) : (
            <>
              {planView.plan ? (
                <p className="mb-4 text-sm text-text-dim">
                  {TRACK_LABEL[planView.plan.track] ?? planView.plan.track} &middot;{" "}
                  {planView.plan.target_milestones.description} &middot;{" "}
                  {daysRemaining(planView.plan.target_end_date)} days left in this 90-day plan
                </p>
              ) : (
                <p className="mb-4 text-sm text-text-faint">
                  Complete your profile and record a voice sample plus a{" "}
                  <Link href="/vocal-range" className="text-accent hover:text-accent-strong">
                    vocal range test
                  </Link>{" "}
                  to get your custom 90-day plan.{" "}
                  <Link href="/onboarding" className="text-accent hover:text-accent-strong">
                    Get started &rarr;
                  </Link>
                </p>
              )}
              <ul className="space-y-2.5">
                <PlanRow
                  href="/quick-routine/warm_up"
                  icon="wave"
                  color="cyan"
                  title="Warm Up"
                  subtitle="Breathing, humming and straw · about 4 min"
                  tag={
                    <span className="hidden items-center gap-1.5 rounded-full bg-accent-faint px-2.5 py-1 text-xs font-semibold text-accent sm:inline-flex">
                      <Icon name="straw" className="h-3.5 w-3.5" />
                      Needs a straw
                    </span>
                  }
                />
                <PlanRow
                  href="/exercises"
                  icon="mic"
                  color="violet"
                  title="Today's routine"
                  subtitle="Built from your check-in and recovery · 5 to 20 min"
                />
                <PlanRow
                  href="/vocal-range"
                  icon="note"
                  color="teal"
                  title="Vocal range check"
                  subtitle="Map today's comfortable notes"
                />
                <PlanRow
                  href="/quick-routine/cool_down"
                  icon="lotus"
                  color="amber"
                  title="Cool Down"
                  subtitle="An easy finish after singing · about 1 min"
                />
              </ul>
            </>
          )}
        </Card>

        <Card className="lg:col-span-5">
          {history === null ? (
            <p className="text-sm text-text-faint">Loading...</p>
          ) : todaysCheckIn && !editingToday ? (
            <div>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-medium tracking-tight">You&apos;ve checked in today</h2>
                <button
                  type="button"
                  onClick={() => setEditingToday(true)}
                  className="text-xs text-accent hover:text-accent-strong"
                >
                  Edit
                </button>
              </div>
              <dl className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <dt className="text-xs text-text-faint">Voice quality</dt>
                  <dd className="font-display text-2xl">{todaysCheckIn.voice_quality ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-text-faint">Fatigue</dt>
                  <dd className="font-display text-2xl">{todaysCheckIn.fatigue ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-text-faint">Throat discomfort</dt>
                  <dd className="font-display text-2xl">
                    {todaysCheckIn.throat_discomfort ?? "—"}
                  </dd>
                </div>
              </dl>
            </div>
          ) : (
            <>
              <h2 className="mb-4 text-lg font-medium tracking-tight">
                {todaysCheckIn ? "Edit today's check-in" : "How's your voice today?"}
              </h2>
              <CheckInForm
                initial={todaysCheckIn}
                onSubmit={todaysCheckIn ? handleUpdate : handleCreate}
                submitLabel={todaysCheckIn ? "Save changes" : "Save today's check-in"}
              />
            </>
          )}
        </Card>

        <Card title="Your vocal baseline" className="lg:col-span-6">
          {baselineError ? (
            <p className="text-sm text-text-faint">Could not load your vocal baseline.</p>
          ) : (
            <VocalBaseline summary={baseline} />
          )}
        </Card>

        <Card title="Your target range" className="lg:col-span-6">
          {goalError ? (
            <p className="text-sm text-text-faint">Could not load your target tones.</p>
          ) : (
            <GoalTonesCard goal={goal} />
          )}
        </Card>

        <Card className="lg:col-span-12">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-medium tracking-tight">Trend</h2>
            <div className="flex gap-1 rounded-xl border border-border p-1 text-xs">
              {RANGE_OPTIONS.map((opt) => (
                <button
                  key={opt.days}
                  type="button"
                  onClick={() => setRangeDays(opt.days)}
                  className={`rounded-lg px-3 py-1.5 font-semibold ${
                    rangeDays === opt.days
                      ? "bg-accent text-accent-ink"
                      : "text-text-dim hover:bg-surface-2"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <TrendChart
            title="Voice quality"
            variant="bare"
            color="var(--color-accent)"
            points={buildSeries(filteredHistory, dates, "voice_quality")}
            yMin={1}
            yMax={10}
            yTicks={[1, 5, 10]}
          />
          <p className="mt-3 text-xs text-text-faint">
            Fatigue, throat discomfort, sleep, and longer ranges live on{" "}
            <Link href="/progress" className="text-accent hover:text-accent-strong">
              Progress
            </Link>
            .
          </p>
        </Card>
      </div>

      <div className="mt-4">
        <ToneGameTrendCard />
      </div>
    </main>
  );
}


function LandingChooser() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-2xl text-center">
        <p className="font-display mb-4 text-6xl font-medium tracking-tight sm:text-7xl">
          Vep<span className="text-brand">AIr</span>
        </p>
        <h1 className="text-2xl font-normal tracking-tight sm:text-3xl">Welcome to VepAIr</h1>
        <p className="mt-2 text-sm text-text-dim">
          AI-assisted vocal recovery, conditioning, and performance &mdash; for Vrotégés and the
          coaches who train them.
        </p>

        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Link
            href="/signup"
            className="group rounded-[20px] border border-border bg-surface p-8 text-left shadow-card transition hover:border-accent"
          >
            <p className="text-lg font-semibold text-text">I&apos;m a Vrotégé</p>
            <p className="mt-2 text-sm text-text-dim">
              Track your voice, get personalized daily exercises, and train safely with VepAIr.
            </p>
            <span className="mt-4 inline-block text-sm font-medium text-accent group-hover:text-accent">
              Get started &rarr;
            </span>
          </Link>

          <Link
            href="/coach-signup"
            className="group rounded-[20px] border border-border bg-surface p-8 text-left shadow-card transition hover:border-accent"
          >
            <p className="text-lg font-semibold text-text">I&apos;m a Coach</p>
            <p className="mt-2 text-sm text-text-dim">
              Invite Vrotégés, assign custom training, and follow their progress in real time.
            </p>
            <span className="mt-4 inline-block text-sm font-medium text-accent group-hover:text-accent">
              Get started &rarr;
            </span>
          </Link>
        </div>

        <p className="mt-8 text-sm text-text-faint">
          Already have an account?{" "}
          <Link href="/login" className="text-accent hover:text-accent">
            Log in
          </Link>
        </p>
      </div>
    </main>
  );
}

export default function Home() {
  const { status, apiFetch } = useAuth();
  const [coachCheck, setCoachCheck] = useState<
    "pending" | "coach" | "coach-inactive" | "singer"
  >("pending");
  // Only meaningful once coachCheck === "coach" -- an admin can now attach a CoachProfile to
  // an existing singer account (POST /api/v1/admin/users/{id}/set-coach), so "has a
  // CoachProfile" no longer implies "has no singer data." null = not checked yet.
  const [hasSingerProfile, setHasSingerProfile] = useState<boolean | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    // Unlike before, this no longer redirects to /coach: the coach sees an adapted version of
    // this same page, with a link into the Coach Portal (see isCoachView on Dashboard) rather
    // than being bounced away from it.
    apiFetch("/api/v1/coach/profile")
      .then(() => setCoachCheck("coach"))
      .catch((err) => {
        // Post-Stage-12 Part 2: a real coach account whose Organization isn't coach_pro-active
        // yet 403s with "coach_pro_required" (see app.coach_auth.get_current_coach), not the
        // generic "not a coach" case -- that account has no singer data either, so it needs its
        // own pending-activation message rather than silently falling through to the singer
        // dashboard as if it were an ordinary singer account.
        setCoachCheck(
          err instanceof ApiError && err.code === "coach_pro_required" ? "coach-inactive" : "singer"
        );
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  useEffect(() => {
    if (coachCheck !== "coach") return;
    // A coach-signup-only account has no singer UserProfile at all, so the full dashboard
    // would just be a wall of empty states -- the compact panel is the right view for it.
    // A dual-role account (admin-granted coach status on top of an existing singer account)
    // does have one, and should see everything, plus a way into the Coach Portal.
    apiFetch("/api/v1/profile")
      .then(() => setHasSingerProfile(true))
      .catch(() => setHasSingerProfile(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coachCheck]);

  const stillResolvingCoachAccountKind = coachCheck === "coach" && hasSingerProfile === null;

  if (
    status === "loading" ||
    (status === "authenticated" && (coachCheck === "pending" || stillResolvingCoachAccountKind))
  ) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-text-faint">Loading...</p>
      </main>
    );
  }

  if (status === "unauthenticated") {
    return <LandingChooser />;
  }

  if (coachCheck === "coach-inactive") {
    return (
      <main className="flex flex-1 items-center justify-center px-6">
        <div className="max-w-sm text-center">
          <h1 className="mb-2 text-lg font-semibold text-text">
            Your account is pending activation
          </h1>
          <p className="text-sm text-text-dim">
            Your coach account has been created, but isn&apos;t active yet. Contact us to get
            started.
          </p>
        </div>
      </main>
    );
  }

  const isPureCoachView = coachCheck === "coach" && hasSingerProfile === false;
  return (
    <Dashboard isCoachView={isPureCoachView} showCoachPortalLink={coachCheck === "coach"} />
  );
}
