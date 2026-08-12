"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { PianoRange } from "@/components/PianoRange";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth-context";
import {
  AudioRecorder,
  MicrophonePermissionDeniedError,
  MicrophoneUnavailableError,
  type RecordingResult,
} from "@/lib/recorder";
import type { Recording, VocalRangeSummary, VoiceSession } from "@/lib/types";

type Phase =
  | "loading"
  | "intro"
  | "requesting-permission"
  | "permission-denied"
  | "no-microphone"
  | "ready"
  | "recording"
  | "reviewing"
  | "uploading"
  | "submitting"
  | "summary";

interface RangeStep {
  type: "range_low" | "range_high" | "range_falsetto";
  title: string;
  instructions: string;
  optional: boolean;
}

const RANGE_SEQUENCE: RangeStep[] = [
  {
    type: "range_low",
    title: "Comfortable low note",
    instructions:
      "Sing or hum the lowest note you can comfortably sustain for a couple of seconds — no straining, just your easy low end.",
    optional: false,
  },
  {
    type: "range_high",
    title: "Comfortable high note",
    instructions:
      "Sing or hum the highest note you can comfortably sustain — stay well within what feels easy, never force it.",
    optional: false,
  },
  {
    type: "range_falsetto",
    title: "Falsetto / head voice (optional)",
    instructions:
      "If it's part of your voice, sing or hum a comfortable falsetto/head-voice note. Skip if not.",
    optional: true,
  },
];

function RangeMappingFlow() {
  const { apiFetch } = useAuth();
  const [phase, setPhase] = useState<Phase>("loading");
  const [stepIndex, setStepIndex] = useState(0);
  const [session, setSession] = useState<VoiceSession | null>(null);
  const [recordingIds, setRecordingIds] = useState<Partial<Record<RangeStep["type"], string>>>(
    {}
  );
  const [lastResult, setLastResult] = useState<RecordingResult | null>(null);
  const [playbackUrl, setPlaybackUrl] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<VocalRangeSummary | null>(null);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const timerStartRef = useRef<number>(0);
  const timerIntervalRef = useRef<number | null>(null);

  const step = RANGE_SEQUENCE[stepIndex];
  const isLastStep = stepIndex === RANGE_SEQUENCE.length - 1;

  useEffect(() => {
    apiFetch<VocalRangeSummary>("/api/v1/vocal-range/summary")
      .then((fetchedSummary) => {
        const hasData = fetchedSummary.current_low_note || fetchedSummary.current_high_note;
        if (hasData) {
          setSummary(fetchedSummary);
          setPhase("summary");
        } else {
          setPhase("intro");
        }
      })
      .catch(() => setPhase("intro"));
    return () => {
      recorderRef.current?.release();
      if (timerIntervalRef.current !== null) window.clearInterval(timerIntervalRef.current);
      if (playbackUrl) URL.revokeObjectURL(playbackUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function startSession() {
    setPhase("requesting-permission");
    setError(null);
    const recorder = new AudioRecorder();
    try {
      await recorder.requestPermissionAndPrepare();
    } catch (err) {
      if (err instanceof MicrophonePermissionDeniedError) {
        setPhase("permission-denied");
        return;
      }
      if (err instanceof MicrophoneUnavailableError) {
        setPhase("no-microphone");
        return;
      }
      setError("Could not access the microphone. Please try again.");
      setPhase("intro");
      return;
    }
    recorderRef.current = recorder;

    try {
      const created = await apiFetch<VoiceSession>("/api/v1/voice-sessions", { method: "POST" });
      setSession(created);
      setPhase("ready");
    } catch {
      setError("Could not start a session. Please try again.");
      setPhase("intro");
    }
  }

  function beginRecording() {
    const recorder = recorderRef.current;
    if (!recorder) return;
    recorder.start();
    timerStartRef.current = performance.now();
    setElapsedMs(0);
    setPhase("recording");
    timerIntervalRef.current = window.setInterval(() => {
      setElapsedMs(performance.now() - timerStartRef.current);
    }, 100);
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (!recorder) return;
    if (timerIntervalRef.current !== null) window.clearInterval(timerIntervalRef.current);

    const result = recorder.stop();
    setLastResult(result);
    if (playbackUrl) URL.revokeObjectURL(playbackUrl);
    setPlaybackUrl(URL.createObjectURL(new Blob([result.wavBytes], { type: "audio/wav" })));
    setPhase("reviewing");
  }

  function retake() {
    setLastResult(null);
    if (playbackUrl) URL.revokeObjectURL(playbackUrl);
    setPlaybackUrl(null);
    setPhase("ready");
  }

  async function finishAndSubmit(ids: Partial<Record<RangeStep["type"], string>>) {
    setPhase("submitting");
    try {
      await apiFetch("/api/v1/vocal-range", {
        method: "POST",
        body: {
          low_recording_id: ids.range_low ?? null,
          high_recording_id: ids.range_high ?? null,
          falsetto_recording_id: ids.range_falsetto ?? null,
        },
      });
      const fetchedSummary = await apiFetch<VocalRangeSummary>("/api/v1/vocal-range/summary");
      setSummary(fetchedSummary);
      setPhase("summary");
    } catch {
      setError("Could not save your range test. Please try again.");
      setPhase("summary");
    }
  }

  async function acceptAndUpload() {
    if (!session || !lastResult) return;
    setPhase("uploading");
    setError(null);
    try {
      const form = new FormData();
      form.append("sample_type", step.type);
      form.append(
        "file",
        new Blob([lastResult.wavBytes], { type: "audio/wav" }),
        "recording.wav"
      );
      const recording = await apiFetch<Recording>(
        `/api/v1/voice-sessions/${session.id}/recordings`,
        { method: "POST", body: form }
      );
      const updatedIds = { ...recordingIds, [step.type]: recording.id };
      setRecordingIds(updatedIds);
      setLastResult(null);
      if (playbackUrl) URL.revokeObjectURL(playbackUrl);
      setPlaybackUrl(null);

      if (isLastStep) {
        await apiFetch(`/api/v1/voice-sessions/${session.id}/complete`, { method: "PATCH" });
        await finishAndSubmit(updatedIds);
      } else {
        setStepIndex((i) => i + 1);
        setPhase("ready");
      }
    } catch {
      setError("Upload failed. You can try again.");
      setPhase("reviewing");
    }
  }

  async function skipOptionalStep() {
    if (!session) return;
    if (isLastStep) {
      await apiFetch(`/api/v1/voice-sessions/${session.id}/complete`, { method: "PATCH" });
      await finishAndSubmit(recordingIds);
    } else {
      setStepIndex((i) => i + 1);
      setPhase("ready");
    }
  }

  if (phase === "intro") {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Vocal Range Mapping</h1>
        <p className="mb-6 text-sm text-neutral-400">
          A quick, comfortable range test — your lowest and highest easy notes, tracked over
          time. Never force a note; stop the moment anything feels strained.
        </p>
        {error && (
          <p className="mb-4 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
        )}
        <button
          type="button"
          onClick={startSession}
          className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
        >
          Start range test
        </button>
      </div>
    );
  }

  if (phase === "loading") {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  if (phase === "requesting-permission") {
    return <p className="text-sm text-neutral-500">Requesting microphone access...</p>;
  }

  if (phase === "permission-denied" || phase === "no-microphone") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <h1 className="mb-2 text-xl font-semibold">
          {phase === "permission-denied" ? "Microphone access needed" : "No microphone found"}
        </h1>
        <p className="mb-4 text-neutral-400">
          {phase === "permission-denied"
            ? "VepAIr needs microphone access for the range test. Check your browser's site settings and allow the microphone, then try again."
            : "VepAIr couldn't find a microphone on this device. Connect one and try again."}
        </p>
        <button
          type="button"
          onClick={startSession}
          className="rounded-lg border border-neutral-700 px-4 py-2 hover:bg-neutral-800"
        >
          Try again
        </button>
      </div>
    );
  }

  if (phase === "submitting") {
    return <p className="text-sm text-neutral-500">Saving your range test...</p>;
  }

  if (phase === "summary") {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-4 text-2xl font-semibold tracking-tight">Your vocal range</h1>
        {error && (
          <p className="mb-4 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
        )}
        {summary && (
          <>
            <PianoRange
              currentLowNote={summary.current_low_note}
              currentHighNote={summary.current_high_note}
              historicalBestLowNote={summary.historical_best_low_note}
              historicalBestHighNote={summary.historical_best_high_note}
              stretchTargetNote={summary.stretch_target_note}
            />
            <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-xs text-neutral-500">Current comfortable range</dt>
                <dd className="text-neutral-200">
                  {summary.current_low_note ?? "—"} to {summary.current_high_note ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-neutral-500">Historical best</dt>
                <dd className="text-neutral-200">
                  {summary.historical_best_low_note ?? "—"} to{" "}
                  {summary.historical_best_high_note ?? "—"}
                </dd>
              </div>
              {summary.change_30d_high.semitones !== null && (
                <div>
                  <dt className="text-xs text-neutral-500">30-day change (high note)</dt>
                  <dd className="text-neutral-200">
                    {summary.change_30d_high.semitones >= 0 ? "+" : ""}
                    {summary.change_30d_high.semitones} semitones
                  </dd>
                </div>
              )}
              {summary.change_90d_high.semitones !== null && (
                <div>
                  <dt className="text-xs text-neutral-500">90-day change (high note)</dt>
                  <dd className="text-neutral-200">
                    {summary.change_90d_high.semitones >= 0 ? "+" : ""}
                    {summary.change_90d_high.semitones} semitones
                  </dd>
                </div>
              )}
              {summary.current_falsetto_note && (
                <div>
                  <dt className="text-xs text-neutral-500">Falsetto / head voice</dt>
                  <dd className="text-neutral-200">{summary.current_falsetto_note}</dd>
                </div>
              )}
            </dl>
            {summary.stretch_target_note && (
              <p className="mt-4 rounded-lg bg-emerald-950/30 px-3 py-2 text-xs text-emerald-300">
                {summary.stretch_target_reason}
              </p>
            )}
          </>
        )}
        <p className="mt-6 text-xs text-neutral-600">
          These numbers describe your own range over time — never a definitive classification of
          your voice type or register. See MEDICAL_SAFETY.md.
        </p>
        <div className="mt-6 flex gap-2">
          <button
            type="button"
            onClick={() => {
              setStepIndex(0);
              setRecordingIds({});
              setError(null);
              void startSession();
            }}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
          >
            Record a new range test
          </button>
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

  // ready / recording / reviewing / uploading
  return (
    <div className="mx-auto w-full max-w-lg">
      <p className="mb-1 text-xs text-neutral-500">
        Step {stepIndex + 1} of {RANGE_SEQUENCE.length}
      </p>
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">{step.title}</h1>
      <p className="mb-4 text-sm text-neutral-400">{step.instructions}</p>

      <p className="my-3 text-center font-mono text-2xl tabular-nums text-neutral-200">
        {(elapsedMs / 1000).toFixed(1)}s
      </p>

      {phase === "ready" && (
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={beginRecording}
            className="w-full rounded-lg bg-red-500 px-4 py-3 text-sm font-medium text-neutral-950 hover:bg-red-400"
          >
            Record
          </button>
          {step.optional && (
            <button
              type="button"
              onClick={skipOptionalStep}
              className="w-full rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
            >
              Skip this step
            </button>
          )}
        </div>
      )}

      {phase === "recording" && (
        <button
          type="button"
          onClick={stopRecording}
          className="w-full rounded-lg bg-neutral-100 px-4 py-3 text-sm font-medium text-neutral-950 hover:bg-white"
        >
          Stop
        </button>
      )}

      {phase === "reviewing" && lastResult && (
        <div className="space-y-3">
          {playbackUrl && <audio controls src={playbackUrl} className="w-full" />}

          {(lastResult.quality.clipping ||
            lastResult.quality.tooQuiet ||
            lastResult.quality.tooShort) && (
            <div className="rounded-lg bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
              This recording looks like it might have an issue:{" "}
              {[
                lastResult.quality.clipping && "clipping (too loud)",
                lastResult.quality.tooQuiet && "too quiet",
                lastResult.quality.tooShort && "too short",
              ]
                .filter(Boolean)
                .join(", ")}
              . You can retake it, or use it anyway.
            </div>
          )}

          {error && (
            <p className="rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={retake}
              className="flex-1 rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
            >
              Retake
            </button>
            <button
              type="button"
              onClick={acceptAndUpload}
              className="flex-1 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
            >
              Use this take
            </button>
          </div>
        </div>
      )}

      {phase === "uploading" && (
        <p className="text-center text-sm text-neutral-500">Uploading...</p>
      )}
    </div>
  );
}

export default function VocalRangePage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <RangeMappingFlow />
      </main>
    </RequireAuth>
  );
}
