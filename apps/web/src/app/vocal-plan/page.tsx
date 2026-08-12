"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth-context";
import type { VocalPlanView } from "@/lib/types";

const TRACK_LABEL: Record<string, string> = {
  repair: "Vocal Repair",
  improvement: "Vocal Improvement",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function daysRemaining(targetEndDate: string): number {
  const ms = new Date(targetEndDate).getTime() - Date.now();
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
}

function PlanView() {
  const { apiFetch } = useAuth();
  const [view, setView] = useState<VocalPlanView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<VocalPlanView>("/api/v1/vocal-plan")
      .then(setView)
      .catch(() => setError("Could not load your vocal plan."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (view === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  if (view.plan === null) {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-2 text-2xl font-semibold tracking-tight">Your vocal plan</h1>
        <p className="mb-6 text-sm text-neutral-400">
          You don&apos;t have a plan yet. Choose a track on your{" "}
          <Link href="/onboarding" className="text-emerald-400 hover:text-emerald-300">
            profile
          </Link>{" "}
          and record a voice sample plus a{" "}
          <Link href="/vocal-range" className="text-emerald-400 hover:text-emerald-300">
            vocal range test
          </Link>{" "}
          — VepAIr builds your 90-day plan from that data as soon as it&apos;s available.
        </p>
      </div>
    );
  }

  const { plan, readiness, just_graduated } = view;

  return (
    <div className="mx-auto w-full max-w-lg">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Your vocal plan</h1>
      <p className="mb-6 text-sm text-neutral-400">
        {TRACK_LABEL[plan.track] ?? plan.track} &middot; started {formatDate(plan.start_date)}
      </p>

      {just_graduated && (
        <p className="mb-6 rounded-lg bg-emerald-950/40 px-3 py-3 text-sm text-emerald-300">
          Your recent data has been consistently stable, so you&apos;ve moved up to an
          Improvement plan — never a claim that you&apos;re &quot;healed,&quot; just that
          things look steady enough to start stretching a little further.
        </p>
      )}

      <section className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
        <h2 className="mb-2 text-sm font-medium text-neutral-200">
          {plan.target_milestones.goal === "stability" ? "Stability goal" : "Range goal"}
        </h2>
        <p className="text-sm text-neutral-300">{plan.target_milestones.description}</p>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-xs text-neutral-500">Target date</dt>
            <dd className="text-neutral-200">{formatDate(plan.target_end_date)}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500">Days remaining</dt>
            <dd className="text-neutral-200">{daysRemaining(plan.target_end_date)}</dd>
          </div>
        </dl>
      </section>

      {readiness && (
        <section className="mt-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
          <h2 className="mb-3 text-sm font-medium text-neutral-200">
            {readiness.ready
              ? "Ready to move to Improvement"
              : "Progress toward moving to Improvement"}
          </h2>
          <ul className="space-y-2 text-xs text-neutral-400">
            {readiness.reasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        </section>
      )}

      <p className="mt-6 text-xs text-neutral-600">
        This plan is a self-selected focus based on your own measured data, never a medical
        diagnosis or a guarantee — see MEDICAL_SAFETY.md.
      </p>

      <div className="mt-6">
        <Link
          href="/"
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
        >
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}

export default function VocalPlanPage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <PlanView />
      </main>
    </RequireAuth>
  );
}
