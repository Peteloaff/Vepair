"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { ExerciseRunner, type LoggedResult } from "@/components/ExerciseRunner";
import { useAuth } from "@/lib/auth-context";
import { todayLocalDate } from "@/lib/date";
import type { AssignedExercises, BaselineSummary, ExerciseSessionRecord } from "@/lib/types";

type Phase = "loading" | "runner" | "complete" | "error";

function AssignedFlow() {
  const { apiFetch } = useAuth();
  const [phase, setPhase] = useState<Phase>("loading");
  const [assigned, setAssigned] = useState<AssignedExercises | null>(null);
  const [session, setSession] = useState<ExerciseSessionRecord | null>(null);
  const [logged, setLogged] = useState<LoggedResult[]>([]);
  const [baseline, setBaseline] = useState<BaselineSummary | null>(null);
  // Guards against dev Strict Mode's mount-effect double-invoke, which would otherwise POST two
  // exercise sessions and leave one orphaned and never completed.
  const startedRef = useRef(false);

  useEffect(() => {
    apiFetch<BaselineSummary>("/api/v1/baseline")
      .then(setBaseline)
      .catch(() => {
        // Live range coaching just won't have a personal baseline to check against yet.
      });

    if (startedRef.current) return;
    startedRef.current = true;

    async function start() {
      try {
        const fetched = await apiFetch<AssignedExercises>("/api/v1/assigned-exercises", {
          searchParams: { date: todayLocalDate() },
        });
        setAssigned(fetched);
        if (fetched.items.length === 0) {
          setPhase("complete");
          return;
        }
        const createdSession = await apiFetch<ExerciseSessionRecord>(
          "/api/v1/exercise-sessions",
          { method: "POST", body: { session_type: "assigned" } }
        );
        setSession(createdSession);
        setPhase("runner");
      } catch {
        setPhase("error");
      }
    }
    void start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFinished(finishedLogged: LoggedResult[]) {
    setLogged(finishedLogged);
    setPhase("complete");
  }

  if (phase === "loading") {
    return <p className="text-sm text-text-faint">Loading your assigned exercises...</p>;
  }

  if (phase === "error") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <p className="mb-4 rounded-lg bg-danger-faint px-3 py-2 text-danger">
          Could not load your assigned exercises. Please try again.
        </p>
        <Link
          href="/"
          className="inline-block rounded-lg border border-border-strong px-4 py-2 hover:bg-surface-2"
        >
          Back to dashboard
        </Link>
      </div>
    );
  }

  if (phase === "runner" && assigned && session) {
    return (
      <ExerciseRunner
        items={assigned.items}
        session={session}
        safetyMessage={assigned.safety_message}
        intensityCap={assigned.intensity_cap}
        reasons={assigned.reasons}
        exerciseToneTargets={assigned.exercise_tone_targets}
        baseline={baseline}
        feedbackFrequency="normal"
        onFinished={handleFinished}
      />
    );
  }

  // phase === "complete"
  const completedCount = logged.filter((l) => l.completed).length;
  const nothingAssigned = assigned !== null && !assigned.has_assignment;
  return (
    <div className="mx-auto w-full max-w-lg text-center">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        {logged.length > 0 ? "Assigned exercises complete" : "Assigned exercises"}
      </h1>
      <p className="mb-6 text-sm text-text-dim">
        {logged.length > 0
          ? `${completedCount} of ${logged.length} exercise${logged.length === 1 ? "" : "s"} completed.`
          : nothingAssigned
            ? "Your coach hasn't assigned anything right now."
            : "Nothing assigned is safe to run today. Rest up, and check back tomorrow."}
      </p>
      <Link
        href="/"
        className="inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
      >
        Back to dashboard
      </Link>
    </div>
  );
}

export default function AssignedPage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <AssignedFlow />
      </main>
    </RequireAuth>
  );
}
