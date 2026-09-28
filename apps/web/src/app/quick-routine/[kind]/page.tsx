"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { ExerciseRunner, type LoggedResult } from "@/components/ExerciseRunner";
import { useAuth } from "@/lib/auth-context";
import { todayLocalDate } from "@/lib/date";
import type { BaselineSummary, ExerciseSessionRecord, QuickRoutine, QuickRoutineKind } from "@/lib/types";

type Phase = "loading" | "runner" | "complete" | "error";

const COPY: Record<QuickRoutineKind, { title: string; blurb: string; doneTitle: string }> = {
  warm_up: {
    title: "Warm Up",
    blurb: "A short, gentle sequence to ease your voice in before rehearsal or a performance.",
    doneTitle: "Warm up complete",
  },
  cool_down: {
    title: "Cool Down",
    blurb: "A brief, relaxed routine to bring your voice back to rest after singing.",
    doneTitle: "Cool down complete",
  },
};

function isQuickRoutineKind(value: string): value is QuickRoutineKind {
  return value === "warm_up" || value === "cool_down";
}

function QuickRoutineFlow({ kind }: { kind: QuickRoutineKind }) {
  const { apiFetch } = useAuth();
  const [phase, setPhase] = useState<Phase>("loading");
  const [routine, setRoutine] = useState<QuickRoutine | null>(null);
  const [session, setSession] = useState<ExerciseSessionRecord | null>(null);
  const [logged, setLogged] = useState<LoggedResult[]>([]);
  const [baseline, setBaseline] = useState<BaselineSummary | null>(null);
  // Guards against dev Strict Mode's mount-effect double-invoke -- without this, a fast
  // remount would fetch the routine and POST /exercise-sessions twice, leaving one orphaned,
  // never-completed session behind for every page load.
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
        const fetchedRoutine = await apiFetch<QuickRoutine>("/api/v1/quick-routine", {
          searchParams: { kind, date: todayLocalDate() },
        });
        setRoutine(fetchedRoutine);
        const createdSession = await apiFetch<ExerciseSessionRecord>(
          "/api/v1/exercise-sessions",
          { method: "POST", body: { session_type: kind } }
        );
        setSession(createdSession);
        setPhase(fetchedRoutine.items.length > 0 ? "runner" : "complete");
      } catch {
        setPhase("error");
      }
    }
    void start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind]);

  function handleFinished(finishedLogged: LoggedResult[]) {
    setLogged(finishedLogged);
    setPhase("complete");
  }

  const copy = COPY[kind];

  if (phase === "loading") {
    return <p className="text-sm text-text-faint">Building your {copy.title.toLowerCase()}...</p>;
  }

  if (phase === "error") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <p className="mb-4 rounded-lg bg-danger-faint px-3 py-2 text-danger">
          Could not build a {copy.title.toLowerCase()} routine. Please try again.
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

  if (phase === "runner" && routine && session) {
    return (
      <ExerciseRunner
        items={routine.items}
        session={session}
        safetyMessage={routine.safety_message}
        intensityCap={routine.intensity_cap}
        reasons={routine.reasons}
        baseline={baseline}
        feedbackFrequency="normal"
        onFinished={handleFinished}
      />
    );
  }

  // phase === "complete"
  const completedCount = logged.filter((l) => l.completed).length;
  return (
    <div className="mx-auto w-full max-w-lg text-center">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">{copy.doneTitle}</h1>
      <p className="mb-6 text-sm text-text-dim">
        {logged.length > 0
          ? `${completedCount} of ${logged.length} exercise${logged.length === 1 ? "" : "s"} completed.`
          : "Nothing to do today — no exercises fit here right now."}
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

export default function QuickRoutinePage() {
  const params = useParams<{ kind: string }>();
  const kind = params.kind;

  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        {isQuickRoutineKind(kind) ? (
          <QuickRoutineFlow kind={kind} />
        ) : (
          <div className="mx-auto w-full max-w-lg text-sm">
            <p className="mb-4 text-text-dim">That&apos;s not a routine VepAIr knows about.</p>
            <Link
              href="/"
              className="inline-block rounded-lg border border-border-strong px-4 py-2 hover:bg-surface-2"
            >
              Back to dashboard
            </Link>
          </div>
        )}
      </main>
    </RequireAuth>
  );
}
