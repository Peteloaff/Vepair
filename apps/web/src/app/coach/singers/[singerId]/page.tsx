"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { RecoveryScoreCard } from "@/components/RecoveryScoreCard";
import { useAuth } from "@/lib/auth-context";
import { todayLocalDate } from "@/lib/date";
import type { CoachSingerSummary } from "@/lib/types";

function NotShared({ label }: { label: string }) {
  return <p className="text-sm text-neutral-500">Not shared: {label}.</p>;
}

function SingerDashboardContent() {
  const { apiFetch } = useAuth();
  const router = useRouter();
  const params = useParams<{ singerId: string }>();
  const [summary, setSummary] = useState<CoachSingerSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);

  useEffect(() => {
    apiFetch<CoachSingerSummary>(`/api/v1/coach/singers/${params.singerId}/summary`, {
      searchParams: { date: todayLocalDate(), length_minutes: "10" },
    })
      .then(setSummary)
      .catch(() => setError("Could not load this singer's dashboard."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.singerId]);

  async function removeSinger() {
    if (
      !window.confirm(
        "Remove this singer from your roster? You'll lose access to their data immediately. This does not delete their VepAIr account or any of their own data — they keep everything, and can invite you again later if they choose to."
      )
    ) {
      return;
    }
    setRemoving(true);
    try {
      await apiFetch(`/api/v1/coach/singers/${params.singerId}`, { method: "DELETE" });
      router.replace("/coach");
    } catch {
      setError("Could not remove this singer. Please try again.");
      setRemoving(false);
    }
  }

  if (error) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (summary === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  const granted = new Set(summary.granted_categories);

  return (
    <div className="mx-auto w-full max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Singer dashboard</h1>
        <div className="flex gap-2 text-sm">
          <Link
            href={`/coach/singers/${params.singerId}/recordings`}
            className="rounded-lg border border-neutral-700 px-3 py-1.5 hover:bg-neutral-800"
          >
            Recordings
          </Link>
          <Link
            href={`/coach/singers/${params.singerId}/assign`}
            className="rounded-lg border border-neutral-700 px-3 py-1.5 hover:bg-neutral-800"
          >
            Assign training
          </Link>
          <Link
            href={`/coach/singers/${params.singerId}/notes`}
            className="rounded-lg border border-neutral-700 px-3 py-1.5 hover:bg-neutral-800"
          >
            Notes
          </Link>
          <button
            type="button"
            onClick={removeSinger}
            disabled={removing}
            className="rounded-lg border border-red-900 px-3 py-1.5 text-red-300 hover:bg-red-950/40 disabled:opacity-50"
          >
            {removing ? "Removing..." : "Remove from roster"}
          </button>
        </div>
      </div>

      <section className="mb-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">VepAIr Score</h2>
        {granted.has("recovery_trends") ? (
          <RecoveryScoreCard score={summary.recovery_score} />
        ) : (
          <NotShared label="recovery score & trends" />
        )}
      </section>

      <section className="mb-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">Vocal range</h2>
        {granted.has("vocal_range") && summary.vocal_range ? (
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-xs text-neutral-500">Current low</dt>
              <dd className="text-neutral-200">
                {summary.vocal_range.current_low_note ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-neutral-500">Current high</dt>
              <dd className="text-neutral-200">
                {summary.vocal_range.current_high_note ?? "—"}
              </dd>
            </div>
          </dl>
        ) : (
          <NotShared label="vocal range history" />
        )}
      </section>

      <section className="mb-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">Exercise trends</h2>
        {granted.has("exercise_history") && summary.exercise_trends ? (
          summary.exercise_trends.length === 0 ? (
            <p className="text-sm text-neutral-500">Not enough data yet.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {summary.exercise_trends.map((t) => (
                <li key={t.exercise_id} className="flex justify-between text-neutral-300">
                  <span>{t.exercise_name}</span>
                  <span className="text-neutral-500">{t.direction}</span>
                </li>
              ))}
            </ul>
          )
        ) : (
          <NotShared label="exercise routine & completion history" />
        )}
      </section>

      <section className="mb-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">Training consistency</h2>
        {granted.has("exercise_history") && summary.training_consistency ? (
          <dl className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <dt className="text-xs text-neutral-500">Current streak</dt>
              <dd className="text-neutral-200">
                {summary.training_consistency.current_streak_days}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-neutral-500">Longest streak</dt>
              <dd className="text-neutral-200">
                {summary.training_consistency.longest_streak_days}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-neutral-500">Sessions</dt>
              <dd className="text-neutral-200">
                {summary.training_consistency.total_sessions_in_range}
              </dd>
            </div>
          </dl>
        ) : (
          <NotShared label="exercise routine & completion history" />
        )}
      </section>

      <section className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-4 text-sm font-medium text-neutral-200">Today&apos;s routine</h2>
        {granted.has("exercise_history") && summary.todays_routine ? (
          <ul className="space-y-1 text-sm">
            {summary.todays_routine.items.map((item) => (
              <li key={item.id} className="flex items-center gap-2 text-neutral-300">
                {item.name}
                {summary.todays_routine!.assigned_exercise_ids.includes(item.id) && (
                  <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-300">
                    assigned
                  </span>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <NotShared label="exercise routine & completion history" />
        )}
      </section>

      <div className="mt-8">
        <Link href="/coach" className="text-xs text-neutral-500 hover:text-neutral-300">
          &larr; Back to your singers
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
