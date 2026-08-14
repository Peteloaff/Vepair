"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { TrendChart, type TrendPoint } from "@/components/TrendChart";
import { useAuth } from "@/lib/auth-context";
import { daysAgoLocalDate, todayLocalDate } from "@/lib/date";
import type { CheckIn, ExerciseTrend, ScoreHistoryPoint, TrainingConsistency } from "@/lib/types";

function buildSeries(history: CheckIn[], dates: string[], metric: keyof CheckIn): TrendPoint[] {
  const byDate = new Map(history.map((c) => [c.checkin_date, c]));
  return dates.map((date) => {
    const c = byDate.get(date);
    const raw = c ? c[metric] : null;
    return { date, value: typeof raw === "number" ? raw : null };
  });
}

const RANGE_OPTIONS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
  { label: "180 days", days: 180 },
  { label: "1 year", days: 365 },
] as const;

// The app didn't exist before this date — a simple, honest stand-in for "all-time" without
// needing to know the user's actual account-creation date.
const ALL_TIME_FROM_DATE = "2020-01-01";

const TREND_DIRECTION_ORDER: Record<ExerciseTrend["direction"], number> = {
  improving: 0,
  stable: 1,
  declining: 2,
  insufficient_data: 3,
};

const TREND_LABEL: Record<ExerciseTrend["direction"], string> = {
  improving: "Improving",
  declining: "Declining",
  stable: "Stable",
  insufficient_data: "Not enough data yet",
};

const TREND_COLOR: Record<ExerciseTrend["direction"], string> = {
  improving: "text-emerald-400",
  declining: "text-amber-400",
  stable: "text-neutral-400",
  insufficient_data: "text-neutral-600",
};

function ConsistencyGrid({ consistency }: { consistency: TrainingConsistency }) {
  return (
    <div className="flex flex-wrap gap-1">
      {consistency.days.map((d) => (
        <div
          key={d.for_date}
          title={`${d.for_date}: ${d.sessions_completed} session${d.sessions_completed === 1 ? "" : "s"}`}
          className={`h-3 w-3 rounded-sm ${
            d.sessions_completed > 0 ? "bg-emerald-500" : "bg-neutral-800"
          }`}
        />
      ))}
    </div>
  );
}

function ProgressDashboard() {
  const { apiFetch } = useAuth();
  const [rangeDays, setRangeDays] = useState<number | "all">(30);
  const [scoreHistory, setScoreHistory] = useState<ScoreHistoryPoint[] | null>(null);
  const [consistency, setConsistency] = useState<TrainingConsistency | null>(null);
  const [exerciseTrends, setExerciseTrends] = useState<ExerciseTrend[] | null>(null);
  const [checkins, setCheckins] = useState<CheckIn[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const today = todayLocalDate();
  const fromDate = rangeDays === "all" ? ALL_TIME_FROM_DATE : daysAgoLocalDate(rangeDays - 1);

  useEffect(() => {
    Promise.all([
      apiFetch<ScoreHistoryPoint[]>("/api/v1/recovery-score/history", {
        searchParams: { from_date: fromDate, to_date: today },
      }),
      apiFetch<TrainingConsistency>("/api/v1/training-consistency", {
        searchParams: { from_date: fromDate, to_date: today, as_of: today },
      }),
      apiFetch<CheckIn[]>("/api/v1/checkins", {
        searchParams: { from_date: fromDate, to_date: today },
      }),
    ])
      .then(([score, consistencyData, checkinData]) => {
        setScoreHistory(score);
        setConsistency(consistencyData);
        setCheckins(checkinData);
        setError(null);
      })
      .catch(() => setError("Could not load your progress data."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rangeDays]);

  useEffect(() => {
    apiFetch<ExerciseTrend[]>("/api/v1/exercise-trends")
      .then(setExerciseTrends)
      .catch(() => setExerciseTrends([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dates = useMemo(
    () => consistency?.days.map((d) => d.for_date) ?? scoreHistory?.map((p) => p.score_date) ?? [],
    [consistency, scoreHistory]
  );

  const scorePoints: TrendPoint[] = useMemo(() => {
    if (!scoreHistory) return [];
    const byDate = new Map(scoreHistory.map((p) => [p.score_date, p]));
    return dates.map((date) => ({ date, value: byDate.get(date)?.score_value ?? null }));
  }, [scoreHistory, dates]);

  const sortedTrends = useMemo(() => {
    if (!exerciseTrends) return [];
    return [...exerciseTrends].sort(
      (a, b) => TREND_DIRECTION_ORDER[a.direction] - TREND_DIRECTION_ORDER[b.direction]
    );
  }, [exerciseTrends]);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Your Progress</h1>
          <p className="mt-1 text-sm text-neutral-400">
            Long-range trends across everything VepAIr tracks about your voice.
          </p>
        </div>
        <Link
          href="/"
          className="shrink-0 rounded-lg border border-neutral-700 px-4 py-2 text-sm font-medium hover:bg-neutral-800"
        >
          Back to dashboard
        </Link>
      </div>

      <div className="mt-6 flex flex-wrap gap-1 rounded-lg border border-neutral-800 p-1 text-xs">
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
        <button
          type="button"
          onClick={() => setRangeDays("all")}
          className={`rounded-md px-2.5 py-1 ${
            rangeDays === "all"
              ? "bg-emerald-500 text-neutral-950"
              : "text-neutral-400 hover:bg-neutral-800"
          }`}
        >
          All-time
        </button>
      </div>

      {error && (
        <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
      )}

      <section className="mt-6">
        {scoreHistory === null ? (
          <p className="text-sm text-neutral-500">Loading...</p>
        ) : (
          <TrendChart
            title="VepAIr Score"
            color="#34d399"
            points={scorePoints}
            yMin={0}
            yMax={100}
            yTicks={[0, 50, 100]}
          />
        )}
      </section>

      <section className="mt-6">
        <h2 className="mb-4 text-lg font-medium tracking-tight">Daily check-in trends</h2>
        {checkins === null ? (
          <p className="text-sm text-neutral-500">Loading...</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TrendChart
              title="Voice quality"
              color="#34d399"
              points={buildSeries(checkins, dates, "voice_quality")}
              yMin={1}
              yMax={10}
              yTicks={[1, 5, 10]}
            />
            <TrendChart
              title="Fatigue"
              color="#fbbf24"
              points={buildSeries(checkins, dates, "fatigue")}
              yMin={1}
              yMax={10}
              yTicks={[1, 5, 10]}
            />
            <TrendChart
              title="Throat discomfort"
              color="#f87171"
              points={buildSeries(checkins, dates, "throat_discomfort")}
              yMin={0}
              yMax={10}
              yTicks={[0, 5, 10]}
            />
            <TrendChart
              title="Sleep (hours)"
              color="#38bdf8"
              points={buildSeries(checkins, dates, "sleep_hours")}
              yMin={0}
              yMax={12}
              yTicks={[0, 6, 12]}
            />
          </div>
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">Training consistency</h2>
        {consistency === null ? (
          <p className="text-sm text-neutral-500">Loading...</p>
        ) : (
          <>
            <div className="mb-4 grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-3xl font-bold text-neutral-50">
                  {consistency.current_streak_days}
                </p>
                <p className="mt-1 text-xs text-neutral-500">Current streak (days)</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-neutral-50">
                  {consistency.longest_streak_days}
                </p>
                <p className="mt-1 text-xs text-neutral-500">Longest streak (days)</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-neutral-50">
                  {consistency.total_sessions_in_range}
                </p>
                <p className="mt-1 text-xs text-neutral-500">Sessions in range</p>
              </div>
            </div>
            <ConsistencyGrid consistency={consistency} />
          </>
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">Exercise trends</h2>
        {exerciseTrends === null ? (
          <p className="text-sm text-neutral-500">Loading...</p>
        ) : sortedTrends.length === 0 ? (
          <p className="text-sm text-neutral-500">
            Complete a few exercise sessions to start seeing per-exercise trends here.
          </p>
        ) : (
          <ul className="space-y-2 text-sm">
            {sortedTrends.map((t) => (
              <li
                key={t.exercise_id}
                className="flex items-center justify-between rounded-lg border border-neutral-800 px-3 py-2"
              >
                <span className="text-neutral-300">{t.exercise_name}</span>
                <span className={`text-xs font-medium ${TREND_COLOR[t.direction]}`}>
                  {TREND_LABEL[t.direction]}
                  {t.direction !== "insufficient_data" && ` · ${t.attempt_count} attempts`}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="mt-6 text-xs text-neutral-600">
        Every trend here is compared only against your own history, never a population norm —
        see MEDICAL_SAFETY.md.
      </p>
    </main>
  );
}

export default function ProgressPage() {
  return (
    <RequireAuth>
      <ProgressDashboard />
    </RequireAuth>
  );
}
