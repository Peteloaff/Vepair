"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { ConsistencyGrid } from "@/components/ConsistencyGrid";
import { TrendChart, type TrendPoint } from "@/components/TrendChart";
import { useAuth } from "@/lib/auth-context";
import { daysAgoLocalDate, todayLocalDate } from "@/lib/date";
import {
  ALL_TIME_FROM_DATE,
  RANGE_OPTIONS,
  TREND_COLOR,
  TREND_LABEL,
  buildSeries,
  sortTrends,
} from "@/lib/progressCharts";
import type { CheckIn, ExerciseTrend, ScoreHistoryPoint, TrainingConsistency } from "@/lib/types";

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

  const sortedTrends = useMemo(() => sortTrends(exerciseTrends ?? []), [exerciseTrends]);

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Your Progress</h1>
          <p className="mt-1 text-sm text-text-dim">
            Long-range trends across everything VepAIr tracks about your voice.
          </p>
        </div>
        <Link
          href="/"
          className="shrink-0 rounded-lg border border-border-strong px-4 py-2 text-sm font-medium hover:bg-surface-2"
        >
          Back to dashboard
        </Link>
      </div>

      <div className="mt-6 flex flex-wrap gap-1 rounded-lg border border-border p-1 text-xs">
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
        <button
          type="button"
          onClick={() => setRangeDays("all")}
          className={`rounded-md px-2.5 py-1 ${
            rangeDays === "all"
              ? "bg-accent text-accent-ink"
              : "text-text-dim hover:bg-surface-2"
          }`}
        >
          All-time
        </button>
      </div>

      {error && (
        <p className="mt-4 rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
      )}

      <section className="mt-6">
        {scoreHistory === null ? (
          <p className="text-sm text-text-faint">Loading...</p>
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
          <p className="text-sm text-text-faint">Loading...</p>
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

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">Training consistency</h2>
        {consistency === null ? (
          <p className="text-sm text-text-faint">Loading...</p>
        ) : (
          <>
            <div className="mb-4 grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-3xl font-bold text-text">
                  {consistency.current_streak_days}
                </p>
                <p className="mt-1 text-xs text-text-faint">Current streak (days)</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-text">
                  {consistency.longest_streak_days}
                </p>
                <p className="mt-1 text-xs text-text-faint">Longest streak (days)</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-text">
                  {consistency.total_sessions_in_range}
                </p>
                <p className="mt-1 text-xs text-text-faint">Sessions in range</p>
              </div>
            </div>
            <ConsistencyGrid consistency={consistency} />
          </>
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">Exercise trends</h2>
        {exerciseTrends === null ? (
          <p className="text-sm text-text-faint">Loading...</p>
        ) : sortedTrends.length === 0 ? (
          <p className="text-sm text-text-faint">
            Complete a few exercise sessions to start seeing per-exercise trends here.
          </p>
        ) : (
          <ul className="space-y-2 text-sm">
            {sortedTrends.map((t) => (
              <li
                key={t.exercise_id}
                className="flex items-center justify-between rounded-lg border border-border px-3 py-2"
              >
                <span className="text-text-dim">{t.exercise_name}</span>
                <span className={`text-xs font-medium ${TREND_COLOR[t.direction]}`}>
                  {TREND_LABEL[t.direction]}
                  {t.direction !== "insufficient_data" && ` · ${t.attempt_count} attempts`}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="mt-6 text-xs text-text-faint">
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
