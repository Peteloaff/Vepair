"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { ExerciseRunner, type FeedbackFrequency, type LoggedResult } from "@/components/ExerciseRunner";
import { useAuth } from "@/lib/auth-context";
import { todayLocalDate } from "@/lib/date";
import {
  ROUTINE_LENGTHS_MINUTES,
  type BaselineSummary,
  type ExerciseSessionRecord,
  type ExerciseTrend,
  type RestCheck,
  type Routine,
  type RoutineLengthMinutes,
} from "@/lib/types";

type Phase = "choose-length" | "loading" | "runner" | "complete" | "error";

const LENGTH_STORAGE_KEY = "vepair.routineLength";
const DEFAULT_LENGTH: RoutineLengthMinutes = 10;

// Opened right after the daily check-in with ?start=1: skip the length picker and build the
// routine at the length the singer last chose (10 minutes the first time).
function rememberedLength(): RoutineLengthMinutes {
  try {
    const saved = Number(window.localStorage.getItem(LENGTH_STORAGE_KEY));
    return ROUTINE_LENGTHS_MINUTES.find((m) => m === saved) ?? DEFAULT_LENGTH;
  } catch {
    return DEFAULT_LENGTH;
  }
}

function rememberLength(minutes: RoutineLengthMinutes) {
  try {
    window.localStorage.setItem(LENGTH_STORAGE_KEY, String(minutes));
  } catch {
    // Private mode or blocked storage: the picker just won't remember it.
  }
}

function ExercisesFlow() {
  const { apiFetch } = useAuth();
  // useSearchParams, not window.location: during a client-side navigation (the check-in's
  // router.push) the address bar still shows the previous URL when this first renders.
  const wantsAutoStart = useSearchParams().get("start") === "1";
  const [phase, setPhase] = useState<Phase>(wantsAutoStart ? "loading" : "choose-length");
  // Guards the auto-start against dev Strict Mode's double-invoked mount effect, which would
  // otherwise create two exercise sessions.
  const autoStartRef = useRef(wantsAutoStart);
  const [routine, setRoutine] = useState<Routine | null>(null);
  const [session, setSession] = useState<ExerciseSessionRecord | null>(null);
  const [logged, setLogged] = useState<LoggedResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [feedbackFrequency, setFeedbackFrequency] = useState<FeedbackFrequency>("normal");
  const [baseline, setBaseline] = useState<BaselineSummary | null>(null);
  const [trends, setTrends] = useState<ExerciseTrend[]>([]);
  const [restCheck, setRestCheck] = useState<RestCheck | null>(null);

  useEffect(() => {
    apiFetch<BaselineSummary>("/api/v1/baseline")
      .then(setBaseline)
      .catch(() => {
        // Live range coaching just won't have a personal baseline to check against yet.
      });
    apiFetch<RestCheck>("/api/v1/routine/rest-check", {
      searchParams: { date: todayLocalDate() },
    })
      .then((rest) => {
        setRestCheck(rest);
        if (!autoStartRef.current) return;
        autoStartRef.current = false;
        // On a recommended rest day the singer sees the warning and picks for themselves.
        if (rest.rest_day_recommended) setPhase("choose-length");
        else void chooseLength(rememberedLength());
      })
      .catch(() => {
        // Best-effort — the length-picker screen still works without this banner, and an
        // unknown rest status must not stop the routine the singer just checked in for.
        if (!autoStartRef.current) return;
        autoStartRef.current = false;
        void chooseLength(rememberedLength());
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function chooseLength(lengthMinutes: RoutineLengthMinutes) {
    rememberLength(lengthMinutes);
    setPhase("loading");
    setError(null);
    try {
      const fetchedRoutine = await apiFetch<Routine>("/api/v1/routine", {
        searchParams: { length_minutes: String(lengthMinutes), date: todayLocalDate() },
      });
      setRoutine(fetchedRoutine);
      const createdSession = await apiFetch<ExerciseSessionRecord>("/api/v1/exercise-sessions", {
        method: "POST",
        body: { routine_length_minutes: lengthMinutes, session_type: "adaptive" },
      });
      setSession(createdSession);
      setLogged([]);
      if (fetchedRoutine.items.length > 0) {
        setPhase("runner");
      } else {
        setPhase("complete");
      }
    } catch {
      setError("Could not build today's routine. Please try again.");
      setPhase("error");
    }
  }

  async function handleFinished(finishedLogged: LoggedResult[]) {
    setLogged(finishedLogged);
    try {
      setTrends(await apiFetch<ExerciseTrend[]>("/api/v1/exercise-trends"));
    } catch {
      // Trends are a nice-to-have on the summary screen, not required to finish the routine.
    }
    setPhase("complete");
  }

  if (phase === "choose-length") {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Voice Exercises</h1>
        <p className="mb-6 text-sm text-text-dim">
          A routine built from today&apos;s check-in, recent recordings, and recovery status —
          never the same every day.
        </p>
        {error && (
          <p className="mb-4 rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
        )}
        {restCheck?.rest_day_recommended && (
          <div className="mb-4 rounded-lg bg-danger-faint px-4 py-3 text-sm text-danger">
            {restCheck.rest_day_reason}
          </div>
        )}
        <p className="mb-3 text-sm text-text-dim">How much time do you have?</p>
        <div className="mb-6 grid grid-cols-2 gap-3">
          {ROUTINE_LENGTHS_MINUTES.map((minutes) => (
            <button
              key={minutes}
              type="button"
              onClick={() => chooseLength(minutes)}
              className="rounded-lg border border-border-strong px-4 py-3 text-sm hover:border-accent hover:bg-surface-2"
            >
              {minutes} minutes
            </button>
          ))}
        </div>

        <p className="mb-2 text-xs text-text-faint">
          Live coaching feedback frequency (while you exercise)
        </p>
        <div className="flex gap-1 rounded-lg border border-border p-1 text-xs">
          {(["frequent", "normal", "minimal"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFeedbackFrequency(f)}
              className={`flex-1 rounded-md px-2.5 py-1.5 capitalize ${
                feedbackFrequency === f
                  ? "bg-accent text-accent-ink"
                  : "text-text-dim hover:bg-surface-2"
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="mt-6 flex justify-center gap-2 text-sm">
          <Link
            href="/quick-routine/warm_up"
            className="rounded-lg border border-border-strong px-3 py-1.5 hover:bg-surface-2"
          >
            Just need a warm up?
          </Link>
          <Link
            href="/quick-routine/cool_down"
            className="rounded-lg border border-border-strong px-3 py-1.5 hover:bg-surface-2"
          >
            Just need a cool down?
          </Link>
        </div>
      </div>
    );
  }

  if (phase === "loading") {
    return <p className="text-sm text-text-faint">Building today&apos;s routine...</p>;
  }

  if (phase === "error") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <p className="mb-4 rounded-lg bg-danger-faint px-3 py-2 text-danger">{error}</p>
        <button
          type="button"
          onClick={() => setPhase("choose-length")}
          className="rounded-lg border border-border-strong px-4 py-2 hover:bg-surface-2"
        >
          Try again
        </button>
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
        exerciseToneTargets={routine.exercise_tone_targets}
        baseline={baseline}
        feedbackFrequency={feedbackFrequency}
        onFinished={handleFinished}
      />
    );
  }

  if (phase === "complete") {
    const completedCount = logged.filter((l) => l.completed).length;
    const trendFor = (exerciseId: string) => trends.find((t) => t.exercise_id === exerciseId);
    return (
      <div className="mx-auto w-full max-w-lg text-center">
        <h1 className="mb-2 text-2xl font-semibold tracking-tight">Routine complete</h1>
        <p className="mb-6 text-sm text-text-dim">
          {completedCount} of {logged.length} exercise{logged.length === 1 ? "" : "s"} completed.
        </p>
        <ul className="mb-6 space-y-2 text-left text-sm">
          {logged.map((l) => {
            const trend = trendFor(l.exercise.id);
            return (
              <li
                key={l.exercise.id}
                className="rounded-lg border border-border bg-surface/60 px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-text-dim">{l.exercise.name}</span>
                  <span className={l.completed ? "text-accent" : "text-text-faint"}>
                    {l.completed ? "Done" : "Skipped"}
                  </span>
                </div>
                {trend && (trend.direction === "improving" || trend.direction === "declining") && (
                  <p
                    className={`mt-1 text-xs ${
                      trend.direction === "improving" ? "text-accent" : "text-warning"
                    }`}
                  >
                    {trend.direction === "improving" ? "Trending better" : "Trending down"} over
                    your last {trend.attempt_count} attempts
                  </p>
                )}
              </li>
            );
          })}
        </ul>
        <div className="flex justify-center gap-2">
          <Link
            href="/share"
            className="inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
          >
            Share My Progress
          </Link>
          <Link
            href="/"
            className="inline-block rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  return null;
}

export default function ExercisesPage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <Suspense fallback={null}>
          <ExercisesFlow />
        </Suspense>
      </main>
    </RequireAuth>
  );
}
