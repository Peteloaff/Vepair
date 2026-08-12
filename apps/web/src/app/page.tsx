"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { CheckInForm } from "@/components/CheckInForm";
import { RecoveryScoreCard } from "@/components/RecoveryScoreCard";
import { TrendChart, type TrendPoint } from "@/components/TrendChart";
import { VocalBaseline } from "@/components/VocalBaseline";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/apiClient";
import { daysAgoLocalDate, lastNDates, todayLocalDate } from "@/lib/date";
import type {
  BaselineSummary,
  CheckIn,
  CheckInInput,
  Profile,
  RecoveryScore as RecoveryScoreData,
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

function Dashboard() {
  const { apiFetch } = useAuth();
  const [history, setHistory] = useState<CheckIn[] | null>(null);
  const [baseline, setBaseline] = useState<BaselineSummary | null>(null);
  const [baselineError, setBaselineError] = useState(false);
  const [recoveryScore, setRecoveryScore] = useState<RecoveryScoreData | null>(null);
  const [recoveryScoreError, setRecoveryScoreError] = useState(false);
  const [planView, setPlanView] = useState<VocalPlanView | null>(null);
  const [planError, setPlanError] = useState(false);
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

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-10">
      <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">VepAIr</h1>
          <p className="mt-1 text-sm text-neutral-400">Today&apos;s Vocal Check-In</p>
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <Link
            href="/progress"
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-800"
          >
            Progress
          </Link>
          <Link
            href="/vocal-plan"
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-800"
          >
            Vocal plan
          </Link>
          <Link
            href="/vocal-range"
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-800"
          >
            Vocal range
          </Link>
          <Link
            href="/exercises"
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-800"
          >
            Voice exercises
          </Link>
          <Link
            href="/record"
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
          >
            Record voice sample
          </Link>
        </div>
      </div>

      {profileMissing && (
        <Link
          href="/onboarding"
          className="mt-4 block rounded-xl border border-emerald-800 bg-emerald-950/30 px-4 py-3 text-sm text-emerald-200 hover:bg-emerald-950/50"
        >
          Finish setting up your profile &rarr;
        </Link>
      )}

      {loadError && (
        <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">
          {loadError}
        </p>
      )}

      <section className="mt-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">VepAIr Score</h2>
        {recoveryScoreError ? (
          <p className="text-sm text-neutral-500">Could not load today&apos;s score.</p>
        ) : (
          <RecoveryScoreCard score={recoveryScore} />
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">Your Plan</h2>
        {planError ? (
          <p className="text-sm text-neutral-500">Could not load your vocal plan.</p>
        ) : planView === null ? (
          <p className="text-sm text-neutral-500">Loading...</p>
        ) : planView.plan ? (
          <div>
            <p className="text-sm text-neutral-300">
              {TRACK_LABEL[planView.plan.track] ?? planView.plan.track} &middot;{" "}
              {planView.plan.target_milestones.description}
            </p>
            <p className="mt-1 text-xs text-neutral-500">
              {daysRemaining(planView.plan.target_end_date)} days left in this 90-day plan
            </p>
            <Link
              href="/exercises"
              className="mt-3 inline-block rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
            >
              Start today&apos;s routine &rarr;
            </Link>
          </div>
        ) : (
          <p className="text-sm text-neutral-500">
            Complete your profile and record a voice sample plus a{" "}
            <Link href="/vocal-range" className="text-emerald-400 hover:text-emerald-300">
              vocal range test
            </Link>{" "}
            to get your custom 90-day plan.{" "}
            <Link href="/onboarding" className="text-emerald-400 hover:text-emerald-300">
              Get started &rarr;
            </Link>
          </p>
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        {history === null ? (
          <p className="text-sm text-neutral-500">Loading...</p>
        ) : todaysCheckIn && !editingToday ? (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-neutral-200">
                You&apos;ve checked in today
              </h2>
              <button
                type="button"
                onClick={() => setEditingToday(true)}
                className="text-xs text-emerald-400 hover:text-emerald-300"
              >
                Edit
              </button>
            </div>
            <dl className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <dt className="text-xs text-neutral-500">Voice quality</dt>
                <dd className="text-neutral-200">{todaysCheckIn.voice_quality ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-neutral-500">Fatigue</dt>
                <dd className="text-neutral-200">{todaysCheckIn.fatigue ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-neutral-500">Throat discomfort</dt>
                <dd className="text-neutral-200">{todaysCheckIn.throat_discomfort ?? "—"}</dd>
              </div>
            </dl>
          </div>
        ) : (
          <>
            <h2 className="mb-4 text-sm font-medium text-neutral-200">
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

      <section className="mt-10 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">Your vocal baseline</h2>
        {baselineError ? (
          <p className="text-sm text-neutral-500">Could not load your vocal baseline.</p>
        ) : (
          <VocalBaseline summary={baseline} />
        )}
      </section>

      <section className="mt-10">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-medium tracking-tight">Trends</h2>
          <div className="flex gap-1 rounded-lg border border-neutral-800 p-1 text-xs">
            {RANGE_OPTIONS.map((opt) => (
              <button
                key={opt.days}
                type="button"
                onClick={() => setRangeDays(opt.days)}
                className={`rounded-md px-2.5 py-1 ${
                  rangeDays === opt.days
                    ? "bg-emerald-500 text-neutral-950"
                    : "text-neutral-400 hover:bg-neutral-800"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TrendChart
            title="Voice quality"
            color="#34d399"
            points={buildSeries(filteredHistory, dates, "voice_quality")}
            yMin={1}
            yMax={10}
            yTicks={[1, 5, 10]}
          />
          <TrendChart
            title="Fatigue"
            color="#fbbf24"
            points={buildSeries(filteredHistory, dates, "fatigue")}
            yMin={1}
            yMax={10}
            yTicks={[1, 5, 10]}
          />
          <TrendChart
            title="Throat discomfort"
            color="#f87171"
            points={buildSeries(filteredHistory, dates, "throat_discomfort")}
            yMin={0}
            yMax={10}
            yTicks={[0, 5, 10]}
          />
          <TrendChart
            title="Sleep (hours)"
            color="#38bdf8"
            points={buildSeries(filteredHistory, dates, "sleep_hours")}
            yMin={0}
            yMax={12}
            yTicks={[0, 6, 12]}
          />
        </div>
      </section>
    </main>
  );
}

export default function Home() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}
