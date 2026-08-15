"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { ReferenceTonePlayer } from "@/components/ReferenceTonePlayer";
import { coachingProfileForCategory, type FeedbackContext } from "@/lib/feedbackEngine";
import {
  LiveCoachSession,
  MicrophonePermissionDeniedError,
  type LiveCoachSummary,
} from "@/lib/liveCoach";
import { useAuth } from "@/lib/auth-context";
import { todayLocalDate } from "@/lib/date";
import {
  ROUTINE_LENGTHS_MINUTES,
  type BaselineSummary,
  type Exercise,
  type ExerciseSessionRecord,
  type ExerciseTrend,
  type RestCheck,
  type Routine,
  type RoutineLengthMinutes,
} from "@/lib/types";

type Phase = "choose-length" | "loading" | "safety" | "exercise" | "complete" | "error";
type FeedbackFrequency = "frequent" | "normal" | "minimal";
type MicStatus = "unknown" | "granted" | "denied" | "unavailable";

interface LoggedResult {
  exercise: Exercise;
  completed: boolean;
  self_reported_difficulty: number | null;
  voicedRatio: number | null;
}

const INTENSITY_LABEL: Record<Routine["intensity_cap"], string> = {
  low: "Gentle",
  moderate: "Moderate",
  high: "Full",
};

// "Configurable feedback frequency" from the product brief, expressed as the minimum time
// between any two live-coaching messages — see feedbackEngine.ts's minIntervalMs.
const FEEDBACK_INTERVALS_MS: Record<FeedbackFrequency, number> = {
  frequent: 2500,
  normal: 5000,
  minimal: 9000,
};

const LIVE_FEEDBACK_DISPLAY_MS = 4000;

function ExercisesFlow() {
  const { apiFetch } = useAuth();
  const [phase, setPhase] = useState<Phase>("choose-length");
  const [routine, setRoutine] = useState<Routine | null>(null);
  const [session, setSession] = useState<ExerciseSessionRecord | null>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [logged, setLogged] = useState<LoggedResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [feedbackFrequency, setFeedbackFrequency] = useState<FeedbackFrequency>("normal");
  const [liveFeedback, setLiveFeedback] = useState<string | null>(null);
  const [micStatus, setMicStatus] = useState<MicStatus>("unknown");
  const [baseline, setBaseline] = useState<BaselineSummary | null>(null);
  const [trends, setTrends] = useState<ExerciseTrend[]>([]);
  const [restCheck, setRestCheck] = useState<RestCheck | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const timerRef = useRef<number | null>(null);
  const feedbackClearRef = useRef<number | null>(null);
  const coachRef = useRef<LiveCoachSession | null>(null);
  const coachingRef = useRef(false); // whether the current exercise has an active coaching session

  useEffect(() => {
    apiFetch<BaselineSummary>("/api/v1/baseline")
      .then(setBaseline)
      .catch(() => {
        // Live range coaching just won't have a personal baseline to check against yet.
      });
    apiFetch<RestCheck>("/api/v1/routine/rest-check", {
      searchParams: { date: todayLocalDate() },
    })
      .then(setRestCheck)
      .catch(() => {
        // Best-effort — the length-picker screen still works without this banner.
      });
    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      if (feedbackClearRef.current !== null) window.clearTimeout(feedbackClearRef.current);
      coachRef.current?.release();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startTimer(durationSeconds: number) {
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    setRemainingSeconds(durationSeconds);
    timerRef.current = window.setInterval(() => {
      setRemainingSeconds((s) => (s > 0 ? s - 1 : 0));
    }, 1000);
  }

  function comfortableRangeFor(metricName: string): number | null {
    return baseline?.voice_baselines.find((b) => b.metric_name === metricName)?.median_value ?? null;
  }

  async function startCoachingFor(exercise: Exercise) {
    coachingRef.current = false;
    const profile = coachingProfileForCategory(exercise.category);
    if (profile === "none" || micStatus === "denied" || micStatus === "unavailable") return;

    if (!coachRef.current) coachRef.current = new LiveCoachSession();
    const coach = coachRef.current;

    if (micStatus !== "granted") {
      try {
        await coach.requestPermissionAndPrepare();
        setMicStatus("granted");
      } catch (err) {
        setMicStatus(err instanceof MicrophonePermissionDeniedError ? "denied" : "unavailable");
        return;
      }
    }

    const context: FeedbackContext = {
      profile,
      comfortableMinHz: comfortableRangeFor("f0_min_hz"),
      comfortableMaxHz: comfortableRangeFor("f0_max_hz"),
      minIntervalMs: FEEDBACK_INTERVALS_MS[feedbackFrequency],
    };
    coach.onFeedback = (message) => {
      setLiveFeedback(message.text);
      if (feedbackClearRef.current !== null) window.clearTimeout(feedbackClearRef.current);
      feedbackClearRef.current = window.setTimeout(
        () => setLiveFeedback(null),
        LIVE_FEEDBACK_DISPLAY_MS
      );
    };
    coach.start(context);
    coachingRef.current = true;
  }

  function stopCoaching(): LiveCoachSummary | null {
    setLiveFeedback(null);
    if (!coachingRef.current || !coachRef.current) return null;
    coachingRef.current = false;
    return coachRef.current.stop();
  }

  async function chooseLength(lengthMinutes: RoutineLengthMinutes) {
    setPhase("loading");
    setError(null);
    try {
      const fetchedRoutine = await apiFetch<Routine>("/api/v1/routine", {
        searchParams: { length_minutes: String(lengthMinutes), date: todayLocalDate() },
      });
      setRoutine(fetchedRoutine);
      const createdSession = await apiFetch<ExerciseSessionRecord>("/api/v1/exercise-sessions", {
        method: "POST",
        body: { routine_length_minutes: lengthMinutes },
      });
      setSession(createdSession);
      setStepIndex(0);
      setLogged([]);
      if (fetchedRoutine.safety_message) {
        setPhase("safety");
      } else if (fetchedRoutine.items.length > 0) {
        startTimer(fetchedRoutine.items[0].duration_seconds);
        setPhase("exercise");
        void startCoachingFor(fetchedRoutine.items[0]);
      } else {
        setPhase("complete");
      }
    } catch {
      setError("Could not build today's routine. Please try again.");
      setPhase("error");
    }
  }

  function beginAfterSafetyNotice() {
    if (!routine || routine.items.length === 0) {
      setPhase("complete");
      return;
    }
    startTimer(routine.items[0].duration_seconds);
    setPhase("exercise");
    void startCoachingFor(routine.items[0]);
  }

  async function logCurrentExercise(completed: boolean, difficulty: number | null) {
    if (!routine || !session || submitting) return;
    setSubmitting(true);
    const exercise = routine.items[stepIndex];
    let summary: LiveCoachSummary | null = null;
    try {
      summary = stopCoaching();
    } catch {
      // The recorder can throw if it was never fully started (e.g. mic permission still
      // resolving) -- losing the live-measured summary shouldn't block marking the step done.
    }
    try {
      const form = new FormData();
      form.append("exercise_id", exercise.id);
      form.append("order_index", String(stepIndex));
      form.append("completed", String(completed));
      if (difficulty !== null) form.append("self_reported_difficulty", String(difficulty));
      if (summary) {
        form.append(
          "live_measured_result",
          JSON.stringify({
            voiced_ratio: summary.voicedRatio,
            frame_count: summary.frameCount,
            average_analysis_latency_ms: summary.averageAnalysisLatencyMs,
          })
        );
        // Only uploaded for exercises with a target_measurement -- that's the one thing this
        // exercise is meant to move, and the only thing app/exercise_trends.py ever trends on.
        // Nothing is uploaded for exercises with no target (or when coaching never started).
        if (exercise.target_measurement) {
          form.append("audio", new Blob([summary.wavBytes], { type: "audio/wav" }), "attempt.wav");
        }
      }
      await apiFetch(`/api/v1/exercise-sessions/${session.id}/results`, {
        method: "POST",
        body: form,
      });
    } catch {
      // Logging a single result failing shouldn't block the user from finishing their routine.
    }
    setLogged((prev) => [
      ...prev,
      {
        exercise,
        completed,
        self_reported_difficulty: difficulty,
        voicedRatio: summary?.voicedRatio ?? null,
      },
    ]);

    const nextIndex = stepIndex + 1;
    if (nextIndex < routine.items.length) {
      setStepIndex(nextIndex);
      startTimer(routine.items[nextIndex].duration_seconds);
      void startCoachingFor(routine.items[nextIndex]);
    } else {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      coachRef.current?.release();
      try {
        await apiFetch(`/api/v1/exercise-sessions/${session.id}/complete`, { method: "PATCH" });
      } catch {
        // Non-critical: the session still happened even if marking it complete fails.
      }
      try {
        setTrends(await apiFetch<ExerciseTrend[]>("/api/v1/exercise-trends"));
      } catch {
        // Trends are a nice-to-have on the summary screen, not required to finish the routine.
      }
      setPhase("complete");
    }
    setSubmitting(false);
  }

  if (phase === "choose-length") {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Voice Exercises</h1>
        <p className="mb-6 text-sm text-neutral-400">
          A routine built from today&apos;s check-in, recent recordings, and recovery status —
          never the same every day.
        </p>
        {error && (
          <p className="mb-4 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
        )}
        {restCheck?.rest_day_recommended && (
          <div className="mb-4 rounded-lg bg-red-950/40 px-4 py-3 text-sm text-red-300">
            {restCheck.rest_day_reason}
          </div>
        )}
        <p className="mb-3 text-sm text-neutral-300">How much time do you have?</p>
        <div className="mb-6 grid grid-cols-2 gap-3">
          {ROUTINE_LENGTHS_MINUTES.map((minutes) => (
            <button
              key={minutes}
              type="button"
              onClick={() => chooseLength(minutes)}
              className="rounded-lg border border-neutral-700 px-4 py-3 text-sm hover:border-emerald-600 hover:bg-neutral-800"
            >
              {minutes} minutes
            </button>
          ))}
        </div>

        <p className="mb-2 text-xs text-neutral-500">
          Live coaching feedback frequency (while you exercise)
        </p>
        <div className="flex gap-1 rounded-lg border border-neutral-800 p-1 text-xs">
          {(["frequent", "normal", "minimal"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFeedbackFrequency(f)}
              className={`flex-1 rounded-md px-2.5 py-1.5 capitalize ${
                feedbackFrequency === f
                  ? "bg-emerald-500 text-neutral-950"
                  : "text-neutral-400 hover:bg-neutral-800"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (phase === "loading") {
    return <p className="text-sm text-neutral-500">Building today&apos;s routine...</p>;
  }

  if (phase === "error") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <p className="mb-4 rounded-lg bg-red-950/50 px-3 py-2 text-red-300">{error}</p>
        <button
          type="button"
          onClick={() => setPhase("choose-length")}
          className="rounded-lg border border-neutral-700 px-4 py-2 hover:bg-neutral-800"
        >
          Try again
        </button>
      </div>
    );
  }

  if (phase === "safety" && routine) {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-4 text-xl font-semibold">Before you start</h1>
        <div className="mb-6 rounded-lg bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {routine.safety_message}
        </div>
        <p className="mb-6 text-sm text-neutral-400">
          Today&apos;s routine has been kept to the gentlest exercises only.
        </p>
        <button
          type="button"
          onClick={beginAfterSafetyNotice}
          className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
        >
          Continue
        </button>
      </div>
    );
  }

  if (phase === "exercise" && routine) {
    const exercise = routine.items[stepIndex];
    const profile = coachingProfileForCategory(exercise.category);
    return (
      <div className="mx-auto w-full max-w-lg">
        <p className="mb-1 text-xs text-neutral-500">
          Exercise {stepIndex + 1} of {routine.items.length} &middot;{" "}
          {INTENSITY_LABEL[routine.intensity_cap]} routine
        </p>
        {stepIndex === 0 && routine.reasons.length > 0 && (
          <details className="mb-3 text-xs text-neutral-500">
            <summary className="cursor-pointer hover:text-neutral-300">
              Why this routine?
            </summary>
            <ul className="mt-1 list-disc space-y-1 pl-4">
              {routine.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </details>
        )}
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">{exercise.name}</h1>
        <p className="mb-4 text-sm text-neutral-400">{exercise.purpose}</p>

        <div className="mb-4 rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 text-sm text-neutral-200">
          {exercise.instructions}
        </div>

        {exercise.contraindications && (
          <div className="mb-4 rounded-lg bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
            {exercise.contraindications}
          </div>
        )}

        {routine.exercise_tone_targets[exercise.id] && (
          <div className="mb-4 rounded-lg bg-emerald-950/30 px-3 py-2 text-xs text-emerald-300">
            Your coach&apos;s target for this exercise:{" "}
            {routine.exercise_tone_targets[exercise.id]}
          </div>
        )}

        {profile !== "none" && <ReferenceTonePlayer />}

        <p className="mb-2 text-center font-mono text-3xl tabular-nums text-neutral-200">
          {Math.floor(remainingSeconds / 60)}:{String(remainingSeconds % 60).padStart(2, "0")}
        </p>

        <div className="mb-4 flex min-h-10 items-center justify-center">
          {liveFeedback ? (
            <p className="rounded-lg bg-emerald-950/40 px-3 py-1.5 text-center text-sm text-emerald-300">
              {liveFeedback}
            </p>
          ) : profile !== "none" && micStatus !== "denied" && micStatus !== "unavailable" ? (
            <p className="text-center text-xs text-neutral-600">Live coaching listening...</p>
          ) : profile !== "none" ? (
            <p className="text-center text-xs text-neutral-600">
              Live coaching unavailable (microphone access {micStatus === "denied" ? "denied" : "not available"}) — continue at your own pace.
            </p>
          ) : null}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => logCurrentExercise(false, null)}
            disabled={submitting}
            className="flex-1 rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Skip
          </button>
          <button
            type="button"
            onClick={() => logCurrentExercise(true, null)}
            disabled={submitting}
            className="flex-1 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Saving..." : "Mark done"}
          </button>
        </div>
      </div>
    );
  }

  if (phase === "complete") {
    const completedCount = logged.filter((l) => l.completed).length;
    const trendFor = (exerciseId: string) => trends.find((t) => t.exercise_id === exerciseId);
    return (
      <div className="mx-auto w-full max-w-lg text-center">
        <h1 className="mb-2 text-2xl font-semibold tracking-tight">Routine complete</h1>
        <p className="mb-6 text-sm text-neutral-400">
          {completedCount} of {logged.length} exercise{logged.length === 1 ? "" : "s"} completed.
        </p>
        <ul className="mb-6 space-y-2 text-left text-sm">
          {logged.map((l) => {
            const trend = trendFor(l.exercise.id);
            return (
              <li
                key={l.exercise.id}
                className="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-neutral-300">{l.exercise.name}</span>
                  <span className={l.completed ? "text-emerald-400" : "text-neutral-500"}>
                    {l.completed ? "Done" : "Skipped"}
                  </span>
                </div>
                {trend && (trend.direction === "improving" || trend.direction === "declining") && (
                  <p
                    className={`mt-1 text-xs ${
                      trend.direction === "improving" ? "text-emerald-400" : "text-amber-400"
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
            className="inline-block rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
          >
            Share My Progress
          </Link>
          <Link
            href="/"
            className="inline-block rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
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
        <ExercisesFlow />
      </main>
    </RequireAuth>
  );
}
