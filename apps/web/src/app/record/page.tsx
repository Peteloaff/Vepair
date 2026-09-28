"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { Waveform, type WaveformHandle } from "@/components/Waveform";
import { useAuth } from "@/lib/auth-context";
import {
  AudioRecorder,
  MicrophonePermissionDeniedError,
  MicrophoneUnavailableError,
  type RecordingResult,
} from "@/lib/recorder";
import { RECORDING_SEQUENCE } from "@/lib/recordingSequence";
import type { Recording, VoiceSession } from "@/lib/types";

type Phase =
  | "intro"
  | "requesting-permission"
  | "permission-denied"
  | "no-microphone"
  | "ready"
  | "recording"
  | "reviewing"
  | "uploading"
  | "complete";

const APP_VERSION = "0.1.0";

function detectDeviceType(): string {
  return /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) ? "mobile" : "desktop";
}

function RecordingFlow() {
  const { apiFetch } = useAuth();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const [phase, setPhase] = useState<Phase>("intro");
  const [stepIndex, setStepIndex] = useState(0);
  const [session, setSession] = useState<VoiceSession | null>(null);
  const [uploaded, setUploaded] = useState<Recording[]>([]);
  const [lastResult, setLastResult] = useState<RecordingResult | null>(null);
  const [playbackUrl, setPlaybackUrl] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const waveformRef = useRef<WaveformHandle>(null);
  const timerStartRef = useRef<number>(0);
  const timerIntervalRef = useRef<number | null>(null);

  const step = RECORDING_SEQUENCE[stepIndex];
  const isLastStep = stepIndex === RECORDING_SEQUENCE.length - 1;

  useEffect(() => {
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
      const created = await apiFetch<VoiceSession>("/api/v1/voice-sessions", {
        method: "POST",
        body: {
          device_type: detectDeviceType(),
          microphone_name: recorder.getMicrophoneLabel() || undefined,
          os_info: navigator.userAgent,
          app_version: APP_VERSION,
        },
      });
      setSession(created);
      setPhase("ready");
    } catch {
      setError("Could not start a recording session. Please try again.");
      setPhase("intro");
    }
  }

  function beginRecording() {
    const recorder = recorderRef.current;
    if (!recorder) return;
    waveformRef.current?.reset();
    recorder.onChunk = (chunk) => waveformRef.current?.pushChunk(chunk);
    recorder.start();
    timerStartRef.current = performance.now();
    setElapsedMs(0);
    setPhase("recording");

    // setInterval rather than requestAnimationFrame: rAF is fully paused in a backgrounded
    // tab, which would freeze the visible timer even though the actual audio capture (on
    // the Web Audio graph, not the render loop) correctly keeps recording regardless of
    // tab visibility. setInterval degrades to ~1/sec in the background instead of stopping
    // outright, so the timer stays roughly honest if the user switches away mid-recording.
    timerIntervalRef.current = window.setInterval(() => {
      setElapsedMs(performance.now() - timerStartRef.current);
    }, 100);
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (!recorder) return;
    if (timerIntervalRef.current !== null) window.clearInterval(timerIntervalRef.current);
    setElapsedMs(performance.now() - timerStartRef.current);

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

  async function acceptAndUpload() {
    if (!session || !lastResult) return;
    setPhase("uploading");
    setError(null);
    try {
      const form = new FormData();
      form.append("sample_type", step.type);
      form.append("file", new Blob([lastResult.wavBytes], { type: "audio/wav" }), "recording.wav");

      const recording = await apiFetch<Recording>(
        `/api/v1/voice-sessions/${session.id}/recordings`,
        { method: "POST", body: form }
      );
      setUploaded((prev) => [...prev, recording]);
      setLastResult(null);
      if (playbackUrl) URL.revokeObjectURL(playbackUrl);
      setPlaybackUrl(null);

      if (isLastStep) {
        await apiFetch(`/api/v1/voice-sessions/${session.id}/complete`, { method: "PATCH" });
        setPhase("complete");
      } else {
        setStepIndex((i) => i + 1);
        setElapsedMs(0);
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
      setPhase("complete");
    } else {
      setStepIndex((i) => i + 1);
      setPhase("ready");
    }
  }

  if (phase === "intro") {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Voice Recording Lab</h1>
        <p className="mb-6 text-sm text-text-dim">
          A guided session capturing a few short voice samples. Takes about 3-5 minutes.
        </p>

        <div className="mb-6 space-y-3 rounded-2xl border border-border bg-surface/60 p-5 text-sm">
          <p className="text-text-dim">Before you start:</p>
          <ul className="list-disc space-y-1.5 pl-5 text-text-dim">
            <li>Move to a reasonably quiet room</li>
            <li>Hold your device at a consistent distance from your mouth</li>
            <li>Avoid touching the microphone during recording</li>
            <li>Use the same microphone each time when possible, for consistency</li>
          </ul>
        </div>

        {error && (
          <p className="mb-4 rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
        )}

        <button
          type="button"
          onClick={startSession}
          className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
        >
          Start session
        </button>

        {next && (
          <Link
            href={next}
            className="mt-3 block text-center text-xs text-text-faint hover:text-text-dim"
          >
            Skip for now &rarr;
          </Link>
        )}
      </div>
    );
  }

  if (phase === "requesting-permission") {
    return <p className="text-sm text-text-faint">Requesting microphone access...</p>;
  }

  if (phase === "permission-denied") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <h1 className="mb-2 text-xl font-semibold">Microphone access needed</h1>
        <p className="mb-4 text-text-dim">
          VepAIr needs microphone access to record voice samples. You denied (or previously
          denied) permission. Check your browser&apos;s site settings for this page and allow
          the microphone, then try again.
        </p>
        <button
          type="button"
          onClick={startSession}
          className="rounded-lg border border-border-strong px-4 py-2 hover:bg-surface-2"
        >
          Try again
        </button>
      </div>
    );
  }

  if (phase === "no-microphone") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <h1 className="mb-2 text-xl font-semibold">No microphone found</h1>
        <p className="mb-4 text-text-dim">
          VepAIr couldn&apos;t find a microphone on this device. Connect one and try again.
        </p>
        <button
          type="button"
          onClick={startSession}
          className="rounded-lg border border-border-strong px-4 py-2 hover:bg-surface-2"
        >
          Try again
        </button>
      </div>
    );
  }

  if (phase === "complete") {
    const scoreColor = (label: string) =>
      label === "excellent" || label === "good"
        ? "text-accent"
        : label === "fair"
          ? "text-warning"
          : "text-danger";

    return (
      <div className="mx-auto w-full max-w-lg text-center">
        <h1 className="mb-2 text-2xl font-semibold tracking-tight">Session complete</h1>
        <p className="mb-6 text-sm text-text-dim">
          {uploaded.length} recording{uploaded.length === 1 ? "" : "s"} saved.
        </p>
        <ul className="mb-6 space-y-2 text-left text-sm">
          {uploaded.map((r) => {
            const score = r.quality_flags?.quality_score;
            const m = r.measurement;
            return (
              <li
                key={r.id}
                className="rounded-lg border border-border bg-surface/60 px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-text-dim">{r.sample_type}</span>
                  {score && (
                    <span className={scoreColor(score.label)}>
                      {score.label} ({score.score})
                    </span>
                  )}
                </div>
                {m && (
                  <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-faint">
                    {m.f0_mean_hz !== null && (
                      <div>
                        F0 <span className="text-text-dim">{m.f0_mean_hz.toFixed(0)}Hz</span>
                      </div>
                    )}
                    {m.jitter_percent !== null && (
                      <div>
                        Jitter{" "}
                        <span className="text-text-dim">{m.jitter_percent.toFixed(2)}%</span>
                      </div>
                    )}
                    {m.shimmer_percent !== null && (
                      <div>
                        Shimmer{" "}
                        <span className="text-text-dim">
                          {m.shimmer_percent.toFixed(2)}%
                        </span>
                      </div>
                    )}
                    {m.hnr_db !== null && (
                      <div>
                        HNR <span className="text-text-dim">{m.hnr_db.toFixed(1)}dB</span>
                      </div>
                    )}
                  </dl>
                )}
                {r.anomalies.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {r.anomalies.map((a) => (
                      <li
                        key={a.metric_name}
                        className="rounded-md bg-warning-faint px-2 py-1 text-xs text-warning"
                      >
                        {a.message}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
        <p className="mb-6 text-xs text-text-faint">
          These are raw acoustic measurements, not a diagnosis — see
          docs/acoustic-measurements.md for what each one means and its limitations.
        </p>
        <Link
          href={next ?? "/"}
          className="inline-block rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
        >
          {next ? "Continue to vocal range test →" : "Back to dashboard"}
        </Link>
      </div>
    );
  }

  // ready / recording / reviewing / uploading
  return (
    <div className="mx-auto w-full max-w-lg">
      <p className="mb-1 text-xs text-text-faint">
        Step {stepIndex + 1} of {RECORDING_SEQUENCE.length}
      </p>
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">{step.title}</h1>
      <p className="mb-4 text-sm text-text-dim">{step.instructions}</p>
      {step.prompt && (
        <blockquote className="mb-4 rounded-lg border border-border bg-surface/60 px-4 py-3 text-sm italic text-text">
          {step.prompt}
        </blockquote>
      )}

      <Waveform ref={waveformRef} active={phase === "recording"} />

      <p className="my-3 text-center font-mono text-2xl tabular-nums text-text">
        {(elapsedMs / 1000).toFixed(1)}s
      </p>

      {phase === "ready" && (
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={beginRecording}
            className="w-full rounded-lg bg-danger px-4 py-3 text-sm font-medium text-accent-ink hover:bg-danger"
          >
            Record
          </button>
          {step.optional && (
            <button
              type="button"
              onClick={skipOptionalStep}
              className="w-full rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2"
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
          className="w-full rounded-lg bg-surface-2 px-4 py-3 text-sm font-medium text-text hover:bg-surface"
        >
          Stop
        </button>
      )}

      {phase === "reviewing" && lastResult && (
        <div className="space-y-3">
          {playbackUrl && (
             
            <audio controls src={playbackUrl} className="w-full" />
          )}

          {(lastResult.quality.clipping ||
            lastResult.quality.tooQuiet ||
            lastResult.quality.tooShort) && (
            <div className="rounded-lg bg-warning-faint px-3 py-2 text-xs text-warning">
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
            <p className="rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
          )}

          <div className="flex gap-2">
            <button
              type="button"
              onClick={retake}
              className="flex-1 rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2"
            >
              Retake
            </button>
            <button
              type="button"
              onClick={acceptAndUpload}
              className="flex-1 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
            >
              Use this take
            </button>
          </div>
        </div>
      )}

      {phase === "uploading" && (
        <p className="text-center text-sm text-text-faint">Uploading...</p>
      )}
    </div>
  );
}

export default function RecordPage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <Suspense fallback={null}>
          <RecordingFlow />
        </Suspense>
      </main>
    </RequireAuth>
  );
}
