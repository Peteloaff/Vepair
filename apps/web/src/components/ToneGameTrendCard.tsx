"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { TrendChart, type TrendPoint } from "@/components/TrendChart";
import { useAuth } from "@/lib/auth-context";
import { lastNDates, toLocalIsoDate } from "@/lib/date";
import type { ToneGameSession } from "@/lib/types";

const TREND_RANGE_DAYS = 30;
// Below this many completed games there's nothing meaningful to trend yet -- see the
// founder's own scoping decision for this card.
const MIN_SESSIONS_TO_SHOW = 2;

/** Home-page-only trend of the singer's own best 5-Tone Challenge score per day (personal
 * only -- no coach sharing, per the founder's decision). Renders nothing at all below
 * MIN_SESSIONS_TO_SHOW completed games. */
export function ToneGameTrendCard() {
  const { apiFetch } = useAuth();
  const [sessions, setSessions] = useState<ToneGameSession[] | null>(null);

  useEffect(() => {
    apiFetch<ToneGameSession[]>("/api/v1/tone-game/sessions")
      .then(setSessions)
      .catch(() => setSessions([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dates = useMemo(() => lastNDates(TREND_RANGE_DAYS), []);

  const bestScoreByDate = useMemo(() => {
    const byDate = new Map<string, number>();
    for (const session of sessions ?? []) {
      const day = toLocalIsoDate(new Date(session.played_at));
      const current = byDate.get(day);
      if (current === undefined || session.total_score > current) {
        byDate.set(day, session.total_score);
      }
    }
    return byDate;
  }, [sessions]);

  const points: TrendPoint[] = useMemo(
    () => dates.map((date) => ({ date, value: bestScoreByDate.get(date) ?? null })),
    [dates, bestScoreByDate]
  );

  if (sessions === null || sessions.length < MIN_SESSIONS_TO_SHOW) return null;

  return (
    <section className="mt-6">
      <TrendChart
        title="5-Tone Challenge (best score/day)"
        color="#a78bfa"
        points={points}
        yMin={0}
        yMax={500}
        yTicks={[0, 250, 500]}
      />
      <p className="mt-3 text-xs text-neutral-500">
        <Link href="/tone-match" className="text-emerald-400 hover:text-emerald-300">
          Play another round
        </Link>
      </p>
    </section>
  );
}
