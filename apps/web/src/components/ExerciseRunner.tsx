"use client";

import { useEffect, useRef, useState } from "react";
import { ReferenceTonePlayer } from "@/components/ReferenceTonePlayer";
import { coachingProfileForCategory, type FeedbackContext } from "@/lib/feedbackEngine";
import {
  LiveCoachSession,
  MicrophonePermissionDeniedError,
  type LiveCoachSummary,
} from "@/lib/liveCoach";
import { useAuth } from "@/lib/auth-context";
import type { BaselineSummary, Exercise, ExerciseSessionRecord } from "@/lib/types";

export type FeedbackFrequency = "frequent" | "normal" | "minimal";
type MicStatus = "unknown" | "granted" | "denied" | "unavailable";
type Phase = "safety" | "exercise";

export interface LoggedResult {
  exercise: Exercise;
  completed: boolean;
  self_reported_difficulty: number | null;
  voicedRatio: number | null;
}

const INTENSITY_LABEL: Record<string, string> = {
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

function needsEquipment(exercise: Exercise): boolean {
  return (exercise.equipment?.length ?? 0) > 0;
}

/**
 * The step-through engine shared by the daily adaptive routine (exercises/page.tsx) and the
 * standalone quick-routine flow (quick-routine/[kind]/page.tsx): timer, live-coaching wiring,
 * per-exercise result logging, and session completion. Deliberately does NOT render a "complete"
 * screen -- the two callers want different ones (the adaptive routine shows trends + a Share My
 * Progress link; a quick routine's is meant to stay lightweight) -- so this fires `onFinished`
 * once the last exercise is logged and the session is marked complete, and the caller takes it
 * from there.
 */
export function ExerciseRunner({
  items,
  session,
  safetyMessage,
  intensityCap,
  reasons = [],
  exerciseToneTargets = {},
  baseline,
  feedbackFrequency,
  onFinished,
}: {
  items: Exercise[];
  session: ExerciseSessionRecord;
  safetyMessage: string | null;
  intensityCap?: string;
  reasons?: string[];
  exerciseToneTargets?: Record<string, string>;
  baseline: BaselineSummary | null;
  feedbackFrequency: FeedbackFrequency;
  onFinished: (logged: LoggedResult[]) => void;
}) {
  const { apiFetch } = useAuth();
  const [phase, setPhase] = useState<Phase>(safetyMessage ? "safety" : "exercise");
  const [stepIndex, setStepIndex] = useState(0);
  const [logged, setLogged] = useState<LoggedResult[]>([]);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [liveFeedback, setLiveFeedback] = useState<string | null>(null);
  const [micStatus, setMicStatus] = useState<MicStatus>("unknown");
  const [submitting, setSubmitting] = useState(false);
  // True once the singer has tapped Next on the current exercise's "get what you need" screen.
  // Reset on every step; irrelevant for exercises that don't need anything.
  const [gearReady, setGearReady] = useState(false);

  const timerRef = useRef<number | null>(null);
  const feedbackClearRef = useRef<number | null>(null);
  const coachRef = useRef<LiveCoachSession | null>(null);
  const coachingRef = useRef(false);
  // Guards the exercise-phase mount effect below from re-firing the first exercise's timer/
  // coaching a second time in dev's Strict Mode double-invoke.
  const startedRef = useRef(false);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      if (feedbackClearRef.current !== null) window.clearTimeout(feedbackClearRef.current);
      coachRef.current?.release();
    };
  }, []);

  useEffect(() => {
    if (phase !== "exercise" || startedRef.current || items.length === 0) return;
    startedRef.current = true;
    // An exercise that needs equipment waits on its "get ready" screen -- the timer and mic
    // only start once the singer taps Next (confirmGearReady).
    if (needsEquipment(items[0])) return;
    startTimer(items[0].duration_seconds);
    void startCoachingFor(items[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

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

  function beginAfterSafetyNotice() {
    setPhase("exercise");
  }

  async function logCurrentExercise(completed: boolean, difficulty: number | null) {
    if (submitting) return;
    setSubmitting(true);
    const exercise = items[stepIndex];
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
    const nextLogged = [
      ...logged,
      {
        exercise,
        completed,
        self_reported_difficulty: difficulty,
        voicedRatio: summary?.voicedRatio ?? null,
      },
    ];
    setLogged(nextLogged);

    const nextIndex = stepIndex + 1;
    if (nextIndex < items.length) {
      setStepIndex(nextIndex);
      setGearReady(false);
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      if (!needsEquipment(items[nextIndex])) {
        startTimer(items[nextIndex].duration_seconds);
        void startCoachingFor(items[nextIndex]);
      }
    } else {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      coachRef.current?.release();
      try {
        await apiFetch(`/api/v1/exercise-sessions/${session.id}/complete`, { method: "PATCH" });
      } catch {
        // Non-critical: the session still happened even if marking it complete fails.
      }
      onFinished(nextLogged);
    }
    setSubmitting(false);
  }

  if (phase === "safety") {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-4 text-xl font-semibold">Before you start</h1>
        <div className="mb-6 rounded-lg bg-danger-faint px-4 py-3 text-sm text-danger">
          {safetyMessage}
        </div>
        <p className="mb-6 text-sm text-text-dim">
          Today&apos;s routine has been kept to the gentlest exercises only.
        </p>
        <button
          type="button"
          onClick={beginAfterSafetyNotice}
          className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
        >
          Continue
        </button>
      </div>
    );
  }

  const exercise = items[stepIndex];
  if (!exercise) return null;
  const profile = coachingProfileForCategory(exercise.category);

  function confirmGearReady() {
    if (gearReady) return;
    setGearReady(true);
    startTimer(exercise.duration_seconds);
    void startCoachingFor(exercise);
  }

  if (needsEquipment(exercise) && !gearReady) {
    return (
      <div className="mx-auto w-full max-w-lg">
        <p className="mb-1 text-xs text-text-faint">
          Exercise {stepIndex + 1} of {items.length}
        </p>
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Get what you need</h1>
        <p className="mb-4 text-sm text-text-dim">
          <span className="text-text">{exercise.name}</span> needs{" "}
          {exercise.equipment!.length === 1 ? "one thing" : "a couple of things"}. Go grab{" "}
          {exercise.equipment!.length === 1 ? "it" : "them"}, then tap Next — your timer
          won&apos;t start until you do.
        </p>

        <ul className="mb-6 space-y-3">
          {exercise.equipment!.map((item) => (
            <li key={item.name} className="rounded-lg border border-border bg-surface/60 p-4 text-sm">
              <p className="mb-2 font-medium text-text">{item.name}</p>
              <p className="mb-1 text-xs uppercase tracking-wide text-text-faint">What it is</p>
              <p className="mb-3 text-text-dim">{item.description}</p>
              <p className="mb-1 text-xs uppercase tracking-wide text-text-faint">How to use it</p>
              <p className="text-text-dim">{item.how_to_use}</p>
            </li>
          ))}
        </ul>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => logCurrentExercise(false, null)}
            disabled={submitting}
            className="flex-1 rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Skip this exercise
          </button>
          <button
            type="button"
            onClick={confirmGearReady}
            className="flex-1 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
          >
            Next
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-lg">
      <p className="mb-1 text-xs text-text-faint">
        Exercise {stepIndex + 1} of {items.length}
        {intensityCap && ` · ${INTENSITY_LABEL[intensityCap] ?? intensityCap} routine`}
      </p>
      {stepIndex === 0 && reasons.length > 0 && (
        <details className="mb-3 text-xs text-text-faint">
          <summary className="cursor-pointer hover:text-text-dim">Why this routine?</summary>
          <ul className="mt-1 list-disc space-y-1 pl-4">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </details>
      )}
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">{exercise.name}</h1>
      <p className="mb-4 text-sm text-text-dim">{exercise.purpose}</p>

      <div className="mb-4 rounded-lg border border-border bg-surface/60 p-4 text-sm text-text">
        {exercise.instructions}
      </div>

      {exercise.contraindications && (
        <div className="mb-4 rounded-lg bg-warning-faint px-3 py-2 text-xs text-warning">
          {exercise.contraindications}
        </div>
      )}

      {exerciseToneTargets[exercise.id] && (
        <div className="mb-4 rounded-lg bg-accent-faint px-3 py-2 text-xs text-accent">
          Your coach&apos;s target for this exercise: {exerciseToneTargets[exercise.id]}
        </div>
      )}

      {profile !== "none" && <ReferenceTonePlayer />}

      <p className="mb-2 text-center font-mono text-3xl tabular-nums text-text">
        {Math.floor(remainingSeconds / 60)}:{String(remainingSeconds % 60).padStart(2, "0")}
      </p>

      <div className="mb-4 flex min-h-10 items-center justify-center">
        {liveFeedback ? (
          <p className="rounded-lg bg-accent-faint px-3 py-1.5 text-center text-sm text-accent">
            {liveFeedback}
          </p>
        ) : profile !== "none" && micStatus !== "denied" && micStatus !== "unavailable" ? (
          <p className="text-center text-xs text-text-faint">Live coaching listening...</p>
        ) : profile !== "none" ? (
          <p className="text-center text-xs text-text-faint">
            Live coaching unavailable (microphone access{" "}
            {micStatus === "denied" ? "denied" : "not available"}) — continue at your own pace.
          </p>
        ) : null}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => logCurrentExercise(false, null)}
          disabled={submitting}
          className="flex-1 rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Skip
        </button>
        <button
          type="button"
          onClick={() => logCurrentExercise(true, null)}
          disabled={submitting}
          className="flex-1 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Mark done"}
        </button>
      </div>
    </div>
  );
}
