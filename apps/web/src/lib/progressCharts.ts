// Shared between the singer's own /progress page and the coach's per-singer Progress tab
// (coach/singers/[singerId]/progress) -- both chart the exact same shape of data, just scoped
// to a different user_id server-side. Kept here rather than duplicated in each page.

import type { CheckIn, ExerciseTrend } from "./types";
import type { TrendPoint } from "@/components/TrendChart";

export function buildSeries(history: CheckIn[], dates: string[], metric: keyof CheckIn): TrendPoint[] {
  const byDate = new Map(history.map((c) => [c.checkin_date, c]));
  return dates.map((date) => {
    const c = byDate.get(date);
    const raw = c ? c[metric] : null;
    return { date, value: typeof raw === "number" ? raw : null };
  });
}

export const RANGE_OPTIONS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
  { label: "180 days", days: 180 },
  { label: "1 year", days: 365 },
] as const;

// The app didn't exist before this date — a simple, honest stand-in for "all-time" without
// needing to know the user's actual account-creation date.
export const ALL_TIME_FROM_DATE = "2020-01-01";

export const TREND_DIRECTION_ORDER: Record<ExerciseTrend["direction"], number> = {
  improving: 0,
  stable: 1,
  declining: 2,
  insufficient_data: 3,
};

export const TREND_LABEL: Record<ExerciseTrend["direction"], string> = {
  improving: "Improving",
  declining: "Declining",
  stable: "Stable",
  insufficient_data: "Not enough data yet",
};

export const TREND_COLOR: Record<ExerciseTrend["direction"], string> = {
  improving: "text-emerald-400",
  declining: "text-amber-400",
  stable: "text-neutral-400",
  insufficient_data: "text-neutral-600",
};

export function sortTrends(trends: ExerciseTrend[]): ExerciseTrend[] {
  return [...trends].sort(
    (a, b) => TREND_DIRECTION_ORDER[a.direction] - TREND_DIRECTION_ORDER[b.direction]
  );
}
