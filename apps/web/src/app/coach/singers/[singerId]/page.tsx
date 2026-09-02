"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ExerciseInfoButton } from "@/components/ExerciseInfoButton";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { TrendChart, type TrendPoint } from "@/components/TrendChart";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/apiClient";
import { daysAgoLocalDate, lastNDates, todayLocalDate } from "@/lib/date";
import { ALL_TIME_FROM_DATE, RANGE_OPTIONS } from "@/lib/progressCharts";
import type { CoachSingerHistory, CoachSingerListItem, CoachSingerSummary } from "@/lib/types";

const HISTORY_WINDOW_DAYS = 30;

/** Formats a plain yyyy-mm-dd date string (no time component, e.g. next_reassessment_date) for
 * display. Deliberately does NOT go through `new Date(iso)` -- that parses a bare date as UTC
 * midnight, which `toLocaleDateString` then renders in the browser's local timezone, silently
 * shifting the displayed day backward for anyone west of UTC (the same off-by-one class of bug
 * `lib/date.ts`'s todayLocalDate/daysAgoLocalDate exist to avoid). Parsing the components
 * directly and constructing a local Date sidesteps that entirely. */
function formatLocalDate(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

type Direction = "up" | "down" | "flat";

interface TileDisplay {
  headline: string;
  direction?: Direction;
  sub?: string;
}

function average(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function directionOf(delta: number): Direction {
  if (delta > 0) return "up";
  if (delta < 0) return "down";
  return "flat";
}

const ARROW: Record<Direction, string> = { up: "↑", down: "↓", flat: "→" };

function StatTile({
  label,
  granted,
  display,
}: {
  label: string;
  granted: boolean;
  display: TileDisplay | null;
}) {
  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-4">
      <p className="text-xs text-neutral-500">{label}</p>
      {!granted ? (
        <p className="mt-2 text-sm text-neutral-600">Not shared</p>
      ) : display === null ? (
        <p className="mt-2 text-sm text-neutral-600">Not enough data yet</p>
      ) : (
        <>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-neutral-100">
            {display.direction && <span className="mr-1 text-neutral-500">{ARROW[display.direction]}</span>}
            {display.headline}
          </p>
          {display.sub && <p className="mt-0.5 text-xs text-neutral-500">{display.sub}</p>}
        </>
      )}
    </div>
  );
}

function ActionButton({
  label,
  onClick,
  href,
  badgeCount,
}: {
  label: string;
  onClick?: () => void;
  href?: string;
  badgeCount?: number;
}) {
  const className =
    "relative flex items-center justify-center rounded-xl border border-neutral-800 bg-neutral-900/60 px-4 py-3 text-center text-sm font-medium text-neutral-200 hover:bg-neutral-800";
  const badge = badgeCount != null && badgeCount > 0 && (
    <span className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-emerald-500 px-1 text-xs font-semibold text-neutral-950">
      {badgeCount}
    </span>
  );
  if (href) {
    return (
      <Link href={href} className={className}>
        {label}
        {badge}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} className={className}>
      {label}
      {badge}
    </button>
  );
}

function SingerDashboardContent() {
  const { apiFetch } = useAuth();
  const router = useRouter();
  const params = useParams<{ singerId: string }>();
  const [summary, setSummary] = useState<CoachSingerSummary | null>(null);
  const [history, setHistory] = useState<CoachSingerHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const [unreadMessageCount, setUnreadMessageCount] = useState(0);

  const [showAssigned, setShowAssigned] = useState(false);
  const [showReassessment, setShowReassessment] = useState(false);
  const [reassessmentInput, setReassessmentInput] = useState("");
  const [savingReassessment, setSavingReassessment] = useState(false);
  const [reassessmentError, setReassessmentError] = useState<string | null>(null);

  // A separate, independently-ranged fetch from the fixed 30-day `history` above -- that one
  // feeds the "Today" tiles' fixed week-over-week comparisons, this one feeds the trend chart's
  // own 7-day-to-all-time range picker, so changing one never disturbs the other.
  const [trendRangeDays, setTrendRangeDays] = useState<number | "all">(30);
  const [trendHistory, setTrendHistory] = useState<CoachSingerHistory | null>(null);
  const [trendError, setTrendError] = useState<string | null>(null);

  const today = todayLocalDate();

  function load() {
    Promise.all([
      apiFetch<CoachSingerSummary>(`/api/v1/coach/singers/${params.singerId}/summary`, {
        searchParams: { date: today, length_minutes: "10" },
      }),
      apiFetch<CoachSingerHistory>(`/api/v1/coach/singers/${params.singerId}/history`, {
        searchParams: {
          from_date: daysAgoLocalDate(HISTORY_WINDOW_DAYS - 1),
          to_date: today,
        },
      }),
    ])
      .then(([summaryData, historyData]) => {
        setSummary(summaryData);
        setHistory(historyData);
        setReassessmentInput(summaryData.next_reassessment_date ?? "");
        setError(null);
      })
      .catch(() => setError("Could not load this Vrotégé's dashboard."));
  }

  useEffect(() => {
    load();
    // Best-effort, same pattern as the home page's pendingInviteCount badge -- silently
    // ignored if it fails, since the roster call already covers this singer's full-page load
    // and this is only feeding the "Messages" action button's unread badge.
    apiFetch<CoachSingerListItem[]>("/api/v1/coach/singers")
      .then((rows) => {
        const row = rows.find((r) => r.singer_user_id === params.singerId);
        setUnreadMessageCount(row?.unread_message_count ?? 0);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.singerId]);

  useEffect(() => {
    const fromDate = trendRangeDays === "all" ? ALL_TIME_FROM_DATE : daysAgoLocalDate(trendRangeDays - 1);
    apiFetch<CoachSingerHistory>(`/api/v1/coach/singers/${params.singerId}/history`, {
      searchParams: { from_date: fromDate, to_date: today },
    })
      .then((data) => {
        setTrendHistory(data);
        setTrendError(null);
      })
      .catch(() => setTrendError("Could not load this Vrotégé's progress trend."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.singerId, trendRangeDays]);

  async function removeSinger() {
    if (
      !window.confirm(
        "Remove this Vrotégé from your roster? You'll lose access to their data immediately. This does not delete their VepAIr account or any of their own data — they keep everything, and can invite you again later if they choose to."
      )
    ) {
      return;
    }
    setRemoving(true);
    try {
      await apiFetch(`/api/v1/coach/singers/${params.singerId}`, { method: "DELETE" });
      router.replace("/coach");
    } catch {
      setError("Could not remove this Vrotégé. Please try again.");
      setRemoving(false);
    }
  }

  async function saveReassessment(nextDate: string | null) {
    setSavingReassessment(true);
    setReassessmentError(null);
    try {
      const result = await apiFetch<{ next_reassessment_date: string | null }>(
        `/api/v1/coach/singers/${params.singerId}/reassessment`,
        { method: "PATCH", body: { next_reassessment_date: nextDate } }
      );
      setSummary((prev) => (prev ? { ...prev, next_reassessment_date: result.next_reassessment_date } : prev));
      setReassessmentInput(result.next_reassessment_date ?? "");
    } catch (err) {
      setReassessmentError(
        err instanceof ApiError ? err.message : "Could not save this date. Please try again."
      );
    } finally {
      setSavingReassessment(false);
    }
  }

  const granted = useMemo(() => new Set(summary?.granted_categories ?? []), [summary]);

  const tiles = useMemo(() => {
    const last7 = lastNDates(7);
    const prior7 = Array.from({ length: 7 }, (_, i) => daysAgoLocalDate(13 - i));
    const last30 = lastNDates(HISTORY_WINDOW_DAYS);

    const scoreByDate = new Map((history?.score_history ?? []).map((p) => [p.score_date, p]));
    const checkinByDate = new Map((history?.checkins ?? []).map((c) => [c.checkin_date, c]));
    const consistencyByDate = new Map(
      (history?.training_consistency?.days ?? []).map((d) => [d.for_date, d])
    );

    const stabilityWindow = (dates: string[]) =>
      average(
        dates
          .map((d) => scoreByDate.get(d)?.acoustic_stability_score)
          .filter((v): v is number => typeof v === "number")
      );
    const fatigueWindow = (dates: string[]) =>
      average(
        dates
          .map((d) => checkinByDate.get(d)?.fatigue)
          .filter((v): v is number => typeof v === "number")
      );

    // Range: 30-day change in the singer's comfortable high note, already computed server-side.
    let range: TileDisplay | null = null;
    const rangeSemitones = summary?.vocal_range?.change_30d_high?.semitones ?? null;
    if (rangeSemitones !== null) {
      const rounded = Math.round(rangeSemitones * 10) / 10;
      range = {
        // A signed delta ("+4"/"−2") is the idiomatic way to express a semitone shift -- unlike
        // a percentage, it doesn't read as a double negative alongside the arrow.
        headline: `${rounded > 0 ? "+" : rounded < 0 ? "−" : ""}${Math.abs(rounded)} semitones`,
        direction: directionOf(rounded),
        sub: "vs. 30 days ago",
      };
    }

    // Stability: this week's average "how typical vs. your baseline" score vs. the week before.
    let stability: TileDisplay | null = null;
    const stabilityNow = stabilityWindow(last7);
    const stabilityPrior = stabilityWindow(prior7);
    if (stabilityNow !== null && stabilityPrior !== null) {
      const delta = Math.round(stabilityNow - stabilityPrior);
      stability = { headline: `${Math.abs(delta)}%`, direction: directionOf(delta), sub: "vs. last week" };
    }

    // Fatigue: self-reported average, this week vs. last week, as a relative % change.
    let fatigue: TileDisplay | null = null;
    const fatigueNow = fatigueWindow(last7);
    const fatiguePrior = fatigueWindow(prior7);
    if (fatigueNow !== null && fatiguePrior !== null && fatiguePrior !== 0) {
      const rawDelta = fatigueNow - fatiguePrior;
      const pct = Math.round((rawDelta / fatiguePrior) * 100);
      fatigue = { headline: `${Math.abs(pct)}%`, direction: directionOf(rawDelta), sub: "vs. last week" };
    }

    // Compliance: % of the last 30 days with at least one completed exercise session.
    let compliance: TileDisplay | null = null;
    if (consistencyByDate.size > 0) {
      const completed = last30.filter((d) => (consistencyByDate.get(d)?.sessions_completed ?? 0) > 0).length;
      compliance = { headline: `${Math.round((completed / last30.length) * 100)}%`, sub: "last 30 days" };
    }

    // High-load days: self-reported speaking/singing load of "high", last 7 days.
    let highLoadDays: TileDisplay | null = null;
    if (checkinByDate.size > 0) {
      const count = last7.filter((d) => {
        const c = checkinByDate.get(d);
        return c && (c.speaking_load === "high" || c.singing_load === "high");
      }).length;
      highLoadDays = { headline: `${count}`, sub: "last 7 days" };
    }

    // Sessions completed: days with a completed session, last 7 days.
    let sessionsCompleted: TileDisplay | null = null;
    if (consistencyByDate.size > 0) {
      const count = last7.filter((d) => (consistencyByDate.get(d)?.sessions_completed ?? 0) > 0).length;
      sessionsCompleted = { headline: `${count}/${last7.length}`, sub: "last 7 days" };
    }

    return { range, stability, fatigue, compliance, highLoadDays, sessionsCompleted };
  }, [summary, history]);

  const trendDates = useMemo(
    () =>
      trendHistory?.training_consistency?.days.map((d) => d.for_date) ??
      trendHistory?.score_history?.map((p) => p.score_date) ??
      [],
    [trendHistory]
  );

  const trendPoints: TrendPoint[] = useMemo(() => {
    if (!trendHistory?.score_history) return [];
    const byDate = new Map(trendHistory.score_history.map((p) => [p.score_date, p]));
    return trendDates.map((date) => ({ date, value: byDate.get(date)?.score_value ?? null }));
  }, [trendHistory, trendDates]);

  if (error) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (summary === null || history === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  const isOverdue =
    summary.next_reassessment_date !== null && summary.next_reassessment_date < today;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-neutral-500">Vrotégé dashboard</p>
          <h1 className="text-2xl font-semibold tracking-tight">{summary.singer_email}</h1>
        </div>
        <div className="flex gap-3 text-xs text-neutral-500">
          <Link href={`/coach/singers/${params.singerId}/progress`} className="hover:text-neutral-300">
            Full trends
          </Link>
          <button
            type="button"
            onClick={removeSinger}
            disabled={removing}
            className="hover:text-red-300 disabled:opacity-50"
          >
            {removing ? "Removing..." : "Remove from roster"}
          </button>
        </div>
      </div>

      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">Today</p>
      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatTile label="Range" granted={granted.has("vocal_range")} display={tiles.range} />
        <StatTile label="Stability" granted={granted.has("recovery_trends")} display={tiles.stability} />
        <StatTile label="Fatigue" granted={granted.has("recovery_trends")} display={tiles.fatigue} />
        <StatTile label="Compliance" granted={granted.has("exercise_history")} display={tiles.compliance} />
        <StatTile
          label="High-load days"
          granted={granted.has("recovery_trends")}
          display={tiles.highLoadDays}
        />
        <StatTile
          label="Sessions completed"
          granted={granted.has("exercise_history")}
          display={tiles.sessionsCompleted}
        />
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <ActionButton label="Assigned exercises" onClick={() => setShowAssigned((s) => !s)} />
        <ActionButton label="Modify program" href={`/coach/singers/${params.singerId}/assign`} />
        <ActionButton label="Review recordings" href={`/coach/singers/${params.singerId}/recordings`} />
        <ActionButton label="Add note" href={`/coach/singers/${params.singerId}/notes`} />
        <ActionButton
          label="Messages"
          href={`/coach/singers/${params.singerId}/messages`}
          badgeCount={unreadMessageCount}
        />
      </div>

      {showAssigned && (
        <div className="mb-4 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
          <h2 className="mb-3 text-sm font-medium text-neutral-200">Assigned exercises</h2>
          {granted.has("exercise_history") && summary.todays_routine ? (
            summary.todays_routine.items.length === 0 ? (
              <p className="text-sm text-neutral-500">Nothing in today&apos;s routine.</p>
            ) : (
              <ul className="space-y-1.5 text-sm">
                {summary.todays_routine.items.map((item) => (
                  <li key={item.id} className="flex items-center gap-2 text-neutral-300">
                    {item.name}
                    <ExerciseInfoButton
                      purpose={item.purpose}
                      instructions={item.instructions}
                      contraindications={item.contraindications}
                    />
                    {summary.todays_routine!.assigned_exercise_ids.includes(item.id) && (
                      <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">
                        assigned
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )
          ) : (
            <p className="text-sm text-neutral-500">Not shared: exercise routine & completion history.</p>
          )}
        </div>
      )}

      <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-medium text-neutral-200">Schedule reassessment</h2>
            <p className="mt-1 text-xs text-neutral-500">
              {summary.next_reassessment_date ? (
                <>
                  Next due{" "}
                  <span className={isOverdue ? "text-amber-400" : "text-neutral-300"}>
                    {formatLocalDate(summary.next_reassessment_date)}
                  </span>
                  {isOverdue && " (overdue)"}
                </>
              ) : (
                "Not scheduled"
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowReassessment((s) => !s)}
            className="rounded-lg border border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-800"
          >
            {showReassessment ? "Close" : summary.next_reassessment_date ? "Change date" : "Schedule"}
          </button>
        </div>

        {showReassessment && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <input
              type="date"
              value={reassessmentInput}
              onChange={(e) => setReassessmentInput(e.target.value)}
              className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm text-neutral-200 outline-none focus:border-neutral-500"
            />
            <button
              type="button"
              onClick={() => saveReassessment(reassessmentInput || null)}
              disabled={savingReassessment || !reassessmentInput}
              className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
            >
              {savingReassessment ? "Saving..." : "Save"}
            </button>
            {summary.next_reassessment_date && (
              <button
                type="button"
                onClick={() => saveReassessment(null)}
                disabled={savingReassessment}
                className="rounded-lg border border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-800 disabled:opacity-50"
              >
                Clear
              </button>
            )}
          </div>
        )}
        {reassessmentError && <p className="mt-3 text-xs text-red-300">{reassessmentError}</p>}
      </div>

      <section className="mt-8">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xs font-medium uppercase tracking-wide text-neutral-500">Progress</h2>
          <div className="flex gap-1 rounded-lg border border-neutral-800 p-1 text-xs">
            {RANGE_OPTIONS.map((opt) => (
              <button
                key={opt.days}
                type="button"
                onClick={() => setTrendRangeDays(opt.days)}
                className={`rounded-md px-2.5 py-1 ${
                  trendRangeDays === opt.days
                    ? "bg-emerald-500 text-neutral-950"
                    : "text-neutral-400 hover:bg-neutral-800"
                }`}
              >
                {opt.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setTrendRangeDays("all")}
              className={`rounded-md px-2.5 py-1 ${
                trendRangeDays === "all"
                  ? "bg-emerald-500 text-neutral-950"
                  : "text-neutral-400 hover:bg-neutral-800"
              }`}
            >
              All-time
            </button>
          </div>
        </div>

        {!granted.has("recovery_trends") ? (
          <p className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5 text-sm text-neutral-500">
            Not shared: recovery score & trends.
          </p>
        ) : trendError ? (
          <p className="text-sm text-red-300">{trendError}</p>
        ) : trendHistory === null ? (
          <p className="text-sm text-neutral-500">Loading...</p>
        ) : (
          <TrendChart
            title="VepAIr Score"
            color="#34d399"
            points={trendPoints}
            yMin={0}
            yMax={100}
            yTicks={[0, 50, 100]}
          />
        )}

        <Link
          href={`/coach/singers/${params.singerId}/progress`}
          className="mt-4 inline-block rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
        >
          See all progress &rarr;
        </Link>
      </section>

      <div className="mt-8">
        <Link href="/coach" className="text-xs text-neutral-500 hover:text-neutral-300">
          &larr; Back to your Vrotégés
        </Link>
      </div>
    </div>
  );
}

export default function CoachSingerDashboardPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-6 py-10">
          <SingerDashboardContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
