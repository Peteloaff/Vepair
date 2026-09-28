"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { CheckInForm } from "@/components/CheckInForm";
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

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-10">
      <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">VepAIr</h1>
          <p className="mt-1 text-sm text-text-dim">Today&apos;s Vocal Check-In</p>
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <Link
            href="/progress"
            className="rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
          >
            Progress
          </Link>
          <Link
            href="/vocal-plan"
            className="rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
          >
            Vocal plan
          </Link>
          <Link
            href="/vocal-range"
            className="rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
          >
            Vocal range
          </Link>
          <Link
            href="/exercises"
            className="rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
          >
            Voice exercises
          </Link>
          <Link
            href="/quick-routine/warm_up"
            className="rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
          >
            Warm Up
          </Link>
          <Link
            href="/quick-routine/cool_down"
            className="rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
          >
            Cool Down
          </Link>
          <Link
            href="/tone-match"
            className="rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
          >
            Tone Match
          </Link>
          <Link
            href="/recordings"
            className="rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
          >
            Recordings
          </Link>
          {showCoachPortalLink && (
            <Link
              href="/coach"
              className="rounded-lg border border-violet-800 px-4 py-2 text-sm font-medium text-violet-300 hover:bg-violet-950/40"
            >
              Coach Portal
            </Link>
          )}
          {(pendingInviteCount > 0 || hasCoachConnection) && (
            <Link
              href="/coach-access"
              className="relative rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
            >
              Coach Access
              {pendingInviteCount + unreadMessageCount > 0 && (
                <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-xs font-semibold text-accent-ink">
                  {pendingInviteCount + unreadMessageCount}
                </span>
              )}
            </Link>
          )}
          <Link
            href="/record"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
          >
            Record voice sample
          </Link>
        </div>
      </div>

      {profileMissing && (
        <Link
          href="/onboarding"
          className="mt-4 block rounded-xl border border-accent bg-accent-faint px-4 py-3 text-sm text-accent hover:bg-accent-faint"
        >
          Finish setting up your profile &rarr;
        </Link>
      )}

      {restCheck?.rest_day_recommended && (
        <div className="mt-4 rounded-xl bg-danger-faint px-4 py-3 text-sm text-danger">
          {restCheck.rest_day_reason}
        </div>
      )}

      {loadError && (
        <p className="mt-4 rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">
          {loadError}
        </p>
      )}

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">VepAIr Score</h2>
        {recoveryScoreError ? (
          <p className="text-sm text-text-faint">Could not load today&apos;s score.</p>
        ) : (
          <RecoveryScoreCard score={recoveryScore} />
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">Your Plan</h2>
        {planError ? (
          <p className="text-sm text-text-faint">Could not load your vocal plan.</p>
        ) : planView === null ? (
          <p className="text-sm text-text-faint">Loading...</p>
        ) : planView.plan ? (
          <div>
            <p className="text-sm text-text-dim">
              {TRACK_LABEL[planView.plan.track] ?? planView.plan.track} &middot;{" "}
              {planView.plan.target_milestones.description}
            </p>
            <p className="mt-1 text-xs text-text-faint">
              {daysRemaining(planView.plan.target_end_date)} days left in this 90-day plan
            </p>
            <Link
              href="/exercises"
              className="mt-3 inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
            >
              Start today&apos;s routine &rarr;
            </Link>
          </div>
        ) : (
          <p className="text-sm text-text-faint">
            Complete your profile and record a voice sample plus a{" "}
            <Link href="/vocal-range" className="text-accent hover:text-accent">
              vocal range test
            </Link>{" "}
            to get your custom 90-day plan.{" "}
            <Link href="/onboarding" className="text-accent hover:text-accent">
              Get started &rarr;
            </Link>
          </p>
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        {history === null ? (
          <p className="text-sm text-text-faint">Loading...</p>
        ) : todaysCheckIn && !editingToday ? (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-text">
                You&apos;ve checked in today
              </h2>
              <button
                type="button"
                onClick={() => setEditingToday(true)}
                className="text-xs text-accent hover:text-accent"
              >
                Edit
              </button>
            </div>
            <dl className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <dt className="text-xs text-text-faint">Voice quality</dt>
                <dd className="text-text">{todaysCheckIn.voice_quality ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-text-faint">Fatigue</dt>
                <dd className="text-text">{todaysCheckIn.fatigue ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-text-faint">Throat discomfort</dt>
                <dd className="text-text">{todaysCheckIn.throat_discomfort ?? "—"}</dd>
              </div>
            </dl>
          </div>
        ) : (
          <>
            <h2 className="mb-4 text-sm font-medium text-text">
              {todaysCheckIn ? "Edit today's check-in" : "How's your voice today?"}
            </h2>
            <CheckInForm
              initial={todaysCheckIn}
              onSubmit={todaysCheckIn ? handleUpdate : handleCreate}
              submitLabel={todaysCheckIn ? "Save changes" : "Save today's check-in"}
            />
          </>
        )}
      </section>

      <section className="mt-10 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">Your vocal baseline</h2>
        {baselineError ? (
          <p className="text-sm text-text-faint">Could not load your vocal baseline.</p>
        ) : (
          <VocalBaseline summary={baseline} />
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">Your target range</h2>
        {goalError ? (
          <p className="text-sm text-text-faint">Could not load your target tones.</p>
        ) : (
          <GoalTonesCard goal={goal} />
        )}
      </section>

      <section className="mt-10">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-medium tracking-tight">Trend</h2>
          <div className="flex gap-1 rounded-lg border border-border p-1 text-xs">
            {RANGE_OPTIONS.map((opt) => (
              <button
                key={opt.days}
                type="button"
                onClick={() => setRangeDays(opt.days)}
                className={`rounded-md px-2.5 py-1 ${
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
          color="#34d399"
          points={buildSeries(filteredHistory, dates, "voice_quality")}
          yMin={1}
          yMax={10}
          yTicks={[1, 5, 10]}
        />
        <p className="mt-3 text-xs text-text-faint">
          Fatigue, throat discomfort, sleep, and longer ranges live on{" "}
          <Link href="/progress" className="text-accent hover:text-accent">
            Progress
          </Link>
          .
        </p>
      </section>

      <ToneGameTrendCard />
    </main>
  );
}

function LandingChooser() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-2xl text-center">
        <Image
          src="/brand/vepair-logo.png"
          alt=""
          width={64}
          height={64}
          className="mx-auto mb-6"
          priority
        />
        <h1 className="text-3xl font-semibold tracking-tight">Welcome to VepAIr</h1>
        <p className="mt-2 text-sm text-text-dim">
          AI-assisted vocal recovery, conditioning, and performance &mdash; for Vrotégés and the
          coaches who train them.
        </p>

        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Link
            href="/signup"
            className="group rounded-2xl border border-border bg-surface/60 p-8 text-left transition hover:border-accent hover:bg-surface"
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
            className="group rounded-2xl border border-border bg-surface/60 p-8 text-left transition hover:border-accent hover:bg-surface"
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
