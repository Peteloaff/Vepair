"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { Card, StatTile } from "@/components/Card";
import { ConsistencyGrid } from "@/components/ConsistencyGrid";
import { Icon } from "@/components/icons";
import { TrendChart, type TrendPoint } from "@/components/TrendChart";
import { useAuth } from "@/lib/auth-context";
import { daysAgoLocalDate, todayLocalDate } from "@/lib/date";
import {
  ALL_TIME_FROM_DATE,
  RANGE_OPTIONS,
  TREND_CHIP,
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

  const scoreValues = scorePoints.map((p) => p.value).filter((v): v is number => v !== null);
  const averageScore =
    scoreValues.length > 0
      ? Math.round(scoreValues.reduce((sum, v) => sum + v, 0) / scoreValues.length)
      : null;
  const practiceDays = consistency?.days.filter((d) => d.sessions_completed > 0).length ?? 0;
  const rangeButtonClass = (active: boolean) =>
    `rounded-lg px-3 py-1.5 font-semibold ${
      active ? "bg-accent text-accent-ink" : "text-text-dim hover:bg-surface-2"
    }`;

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-normal tracking-tight sm:text-4xl">Your progress</h1>
          <p className="mt-1 text-sm text-text-dim">
            Compared only with your own earlier sessions.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1 rounded-xl border border-border bg-surface p-1 text-xs">
            {RANGE_OPTIONS.map((opt) => (
              <button
                key={opt.days}
                type="button"
                onClick={() => setRangeDays(opt.days)}
                className={rangeButtonClass(rangeDays === opt.days)}
              >
                {opt.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setRangeDays("all")}
              className={rangeButtonClass(rangeDays === "all")}
            >
              All-time
            </button>
          </div>
          <Link
            href="/share"
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-ink"
          >
            <Icon name="share" className="h-4 w-4" />
            Share my progress
          </Link>
        </div>
      </div>

      {error && (
        <p className="mb-4 rounded-xl bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
      )}

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Average score" value={averageScore ?? "—"} />
        <StatTile
          label="Practice days"
          value={consistency ? practiceDays : "—"}
          unit={consistency ? `/ ${consistency.days.length}` : undefined}
        />
        <StatTile
          label="Current streak"
          value={consistency?.current_streak_days ?? "—"}
          unit="days"
        />
        <StatTile
          label="Longest streak"
          value={consistency?.longest_streak_days ?? "—"}
          unit="days"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card title="VepAIr Score" className="lg:col-span-12">
          {scoreHistory === null ? (
            <p className="text-sm text-text-faint">Loading...</p>
          ) : (
            <TrendChart
              title="Daily score"
              variant="bare"
              gradient
              height={260}
              color="var(--color-accent)"
              points={scorePoints}
              yMin={0}
              yMax={100}
              yTicks={[0, 25, 50, 75, 100]}
            />
          )}
        </Card>

        <Card title="Daily check-in trends" className="lg:col-span-7">
          {checkins === null ? (
            <p className="text-sm text-text-faint">Loading...</p>
          ) : (
            <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
              <TrendChart
                title="Voice quality"
                variant="inset"
                color="var(--color-accent)"
                points={buildSeries(checkins, dates, "voice_quality")}
                yMin={1}
                yMax={10}
                yTicks={[1, 5, 10]}
              />
              <TrendChart
                title="Fatigue"
                variant="inset"
                color="var(--color-warning)"
                points={buildSeries(checkins, dates, "fatigue")}
                yMin={1}
                yMax={10}
                yTicks={[1, 5, 10]}
              />
              <TrendChart
                title="Throat discomfort"
                variant="inset"
                color="var(--color-danger)"
                points={buildSeries(checkins, dates, "throat_discomfort")}
                yMin={0}
                yMax={10}
                yTicks={[0, 5, 10]}
              />
              <TrendChart
                title="Sleep (hours)"
                variant="inset"
                color="var(--color-blue)"
                points={buildSeries(checkins, dates, "sleep_hours")}
                yMin={0}
                yMax={12}
                yTicks={[0, 6, 12]}
              />
            </div>
          )}
        </Card>

        <Card title="Training consistency" className="lg:col-span-5">
          {consistency === null ? (
            <p className="text-sm text-text-faint">Loading...</p>
          ) : (
            <>
              <div className="mb-5 flex flex-wrap gap-x-8 gap-y-3">
                <div>
                  <p className="font-display flex items-center gap-2 text-3xl leading-tight tabular-nums">
                    <Icon name="flame" className="h-6 w-6 text-warning" />
                    {consistency.current_streak_days}
                  </p>
                  <p className="text-xs text-text-faint">Current streak (days)</p>
                </div>
                <div>
                  <p className="font-display text-3xl leading-tight tabular-nums">
                    {consistency.longest_streak_days}
                  </p>
                  <p className="text-xs text-text-faint">Longest streak (days)</p>
                </div>
                <div>
                  <p className="font-display text-3xl leading-tight tabular-nums">
                    {consistency.total_sessions_in_range}
                  </p>
                  <p className="text-xs text-text-faint">Sessions in range</p>
                </div>
              </div>
              <ConsistencyGrid consistency={consistency} />
            </>
          )}
        </Card>

        <Card title="Exercise trends" meta="From your recent attempts" className="lg:col-span-12">
          {exerciseTrends === null ? (
            <p className="text-sm text-text-faint">Loading...</p>
          ) : sortedTrends.length === 0 ? (
            <p className="text-sm text-text-faint">
              Complete a few exercise sessions to start seeing per-exercise trends here.
            </p>
          ) : (
            <ul className="divide-y divide-border text-sm">
              {sortedTrends.map((t) => (
                <li
                  key={t.exercise_id}
                  className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <span className="font-medium">{t.exercise_name}</span>
                  <span className="flex items-center gap-2">
                    {t.direction !== "insufficient_data" && (
                      <span className="hidden text-xs text-text-faint sm:inline">
                        {t.attempt_count} attempts
                      </span>
                    )}
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${TREND_CHIP[t.direction]}`}
                    >
                      {TREND_LABEL[t.direction]}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

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
