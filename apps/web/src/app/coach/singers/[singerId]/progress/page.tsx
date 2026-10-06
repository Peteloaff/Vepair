"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
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
import type { CoachSingerHistory } from "@/lib/types";

function NotShared({ label }: { label: string }) {
  return <p className="text-sm text-text-faint">Not shared: {label}.</p>;
}

function SingerProgressContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ singerId: string }>();
  const [rangeDays, setRangeDays] = useState<number | "all">(30);
  const [history, setHistory] = useState<CoachSingerHistory | null>(null);
  const [error, setError] = useState<string | null>(null);

  const today = todayLocalDate();
  const fromDate = rangeDays === "all" ? ALL_TIME_FROM_DATE : daysAgoLocalDate(rangeDays - 1);

  useEffect(() => {
    apiFetch<CoachSingerHistory>(`/api/v1/coach/singers/${params.singerId}/history`, {
      searchParams: { from_date: fromDate, to_date: today },
    })
      .then((data) => {
        setHistory(data);
        setError(null);
      })
      .catch(() => setError("Could not load this Vrotégé's progress."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.singerId, rangeDays]);

  const granted = useMemo(() => new Set(history?.granted_categories ?? []), [history]);

  const dates = useMemo(
    () =>
      history?.training_consistency?.days.map((d) => d.for_date) ??
      history?.score_history?.map((p) => p.score_date) ??
      [],
    [history]
  );

  const scorePoints: TrendPoint[] = useMemo(() => {
    if (!history?.score_history) return [];
    const byDate = new Map(history.score_history.map((p) => [p.score_date, p]));
    return dates.map((date) => ({ date, value: byDate.get(date)?.score_value ?? null }));
  }, [history, dates]);

  const sortedTrends = useMemo(
    () => sortTrends(history?.exercise_trends ?? []),
    [history]
  );

  if (error) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (history === null) {
    return <p className="text-sm text-text-faint">Loading...</p>;
  }

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Progress</h1>
          <p className="mt-1 text-sm text-text-dim">
            Long-range trends, compared only against this Vrotégé&apos;s own history.
          </p>
        </div>
        <Link
          href={`/coach/singers/${params.singerId}`}
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

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">VepAIr Score</h2>
        {granted.has("recovery_trends") && history.score_history ? (
          <TrendChart
            title="VepAIr Score"
            color="var(--color-accent)"
            points={scorePoints}
            yMin={0}
            yMax={100}
            yTicks={[0, 50, 100]}
          />
        ) : (
          <NotShared label="recovery score & trends" />
        )}
      </section>

      <section className="mt-6">
        <h2 className="mb-4 text-lg font-medium tracking-tight">Daily check-in trends</h2>
        {granted.has("recovery_trends") && history.checkins ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TrendChart
              title="Voice quality"
              color="var(--color-accent)"
              points={buildSeries(history.checkins, dates, "voice_quality")}
              yMin={1}
              yMax={10}
              yTicks={[1, 5, 10]}
            />
            <TrendChart
              title="Fatigue"
              color="var(--color-warning)"
              points={buildSeries(history.checkins, dates, "fatigue")}
              yMin={1}
              yMax={10}
              yTicks={[1, 5, 10]}
            />
            <TrendChart
              title="Throat discomfort"
              color="var(--color-danger)"
              points={buildSeries(history.checkins, dates, "throat_discomfort")}
              yMin={0}
              yMax={10}
              yTicks={[0, 5, 10]}
            />
            <TrendChart
              title="Sleep (hours)"
              color="var(--color-blue)"
              points={buildSeries(history.checkins, dates, "sleep_hours")}
              yMin={0}
              yMax={12}
              yTicks={[0, 6, 12]}
            />
          </div>
        ) : (
          <NotShared label="recovery score & trends" />
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">Training consistency</h2>
        {granted.has("exercise_history") && history.training_consistency ? (
          <>
            <div className="mb-4 grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-3xl font-bold text-text">
                  {history.training_consistency.current_streak_days}
                </p>
                <p className="mt-1 text-xs text-text-faint">Current streak (days)</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-text">
                  {history.training_consistency.longest_streak_days}
                </p>
                <p className="mt-1 text-xs text-text-faint">Longest streak (days)</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-text">
                  {history.training_consistency.total_sessions_in_range}
                </p>
                <p className="mt-1 text-xs text-text-faint">Sessions in range</p>
              </div>
            </div>
            <ConsistencyGrid consistency={history.training_consistency} />
          </>
        ) : (
          <NotShared label="exercise routine & completion history" />
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-border bg-surface/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-text">Exercise trends</h2>
        {granted.has("exercise_history") && history.exercise_trends ? (
          sortedTrends.length === 0 ? (
            <p className="text-sm text-text-faint">Not enough data yet.</p>
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
          )
        ) : (
          <NotShared label="exercise routine & completion history" />
        )}
      </section>

      <p className="mt-6 text-xs text-text-faint">
        Every trend here is compared only against this Vrotégé&apos;s own history, never a
        population norm — see MEDICAL_SAFETY.md.
      </p>
    </div>
  );
}

export default function CoachSingerProgressPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-6 py-10">
          <SingerProgressContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
