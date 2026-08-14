"use client";

import { useEffect, useRef, useState } from "react";
import {
  AudioRecorder,
  MicrophonePermissionDeniedError,
  MicrophoneUnavailableError,
} from "@/lib/recorder";
import { frequencyToMidi, midiToFrequency, midiToNoteName, noteNameToMidi } from "@/lib/notes";
import { detectPitch } from "@/lib/pitchDetector";
import { useAuth } from "@/lib/auth-context";
import { PitchMeter } from "@/components/PitchMeter";
import type { Recording, VocalGoal, VoiceSession } from "@/lib/types";

type Phase = "idle" | "requesting" | "recording" | "uploading" | "result" | "error";

export function AveragePitchRecorder() {
  const { apiFetch } = useAuth();
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<Recording | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingGoal, setSavingGoal] = useState(false);
  const [goalSaved, setGoalSaved] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [goalHz, setGoalHz] = useState<number | null>(null);
  const [liveHz, setLiveHz] = useState<number | null>(null);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    apiFetch<VocalGoal>("/api/v1/vocal-goals")
      .then((goal) => {
        setGoalHz(goal.target_avg_note ? midiToFrequency(noteNameToMidi(goal.target_avg_note)) : null);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      recorderRef.current?.release();
      if (intervalRef.current !== null) window.clearInterval(intervalRef.current);
    };
  }, []);

  async function start() {
    setPhase("requesting");
    setError(null);
    setResult(null);
    setGoalSaved(false);
    const recorder = new AudioRecorder();
    try {
      await recorder.requestPermissionAndPrepare();
    } catch (err) {
      if (err instanceof MicrophonePermissionDeniedError) {
        setError("Microphone access was denied. Allow it in your browser's site settings.");
      } else if (err instanceof MicrophoneUnavailableError) {
        setError("No microphone was found.");
      } else {
        setError("Could not access the microphone. Please try again.");
      }
      setPhase("error");
      return;
    }
    recorderRef.current = recorder;
    setLiveHz(null);
    recorder.onChunk = (chunk) => {
      const sampleRate = recorder.getSampleRate();
      if (!sampleRate) return;
      const pitch = detectPitch(chunk, sampleRate);
      setLiveHz(pitch?.frequencyHz ?? null);
    };
    recorder.start();
    setPhase("recording");
    setElapsedSeconds(0);
    intervalRef.current = window.setInterval(() => {
      setElapsedSeconds((s) => s + 1);
    }, 1000);
  }

  async function stop() {
    if (intervalRef.current !== null) window.clearInterval(intervalRef.current);
    const recorder = recorderRef.current;
    if (!recorder) return;
    recorder.onChunk = null;
    const recording = recorder.stop();
    setLiveHz(null);
    setPhase("uploading");
    try {
      const session = await apiFetch<VoiceSession>("/api/v1/voice-sessions", {
        method: "POST",
        body: {},
      });
      const form = new FormData();
      form.append("sample_type", "tone_baseline");
      form.append(
        "file",
        new Blob([recording.wavBytes], { type: "audio/wav" }),
        "recording.wav"
      );
      const uploaded = await apiFetch<Recording>(
        `/api/v1/voice-sessions/${session.id}/recordings`,
        { method: "POST", body: form }
      );
      setResult(uploaded);
      setPhase("result");
    } catch {
      setError("Could not save your recording. Please try again.");
      setPhase("error");
    }
  }

  async function useAsAvgGoal() {
    const hz = result?.measurement?.f0_mean_hz;
    if (hz == null) return;
    const note = midiToNoteName(frequencyToMidi(hz));
    setSavingGoal(true);
    try {
      const current = await apiFetch<VocalGoal>("/api/v1/vocal-goals");
      await apiFetch("/api/v1/vocal-goals", {
        method: "PUT",
        body: {
          target_low_note: current.target_low_note,
          target_avg_note: note,
          target_high_note: current.target_high_note,
        },
      });
      setGoalSaved(true);
    } catch {
      setError("Could not save this as your Avg goal tone. Please try again.");
    } finally {
      setSavingGoal(false);
    }
  }

  const hz = result?.measurement?.f0_mean_hz;
  const noteName = hz != null ? midiToNoteName(frequencyToMidi(hz)) : null;

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
      <h2 className="mb-1 text-sm font-medium text-neutral-200">Find your average pitch</h2>
      <p className="mb-4 text-xs text-neutral-500">
        Speak or sing naturally for as long as you like, then stop — we&apos;ll show the average
        pitch across the whole recording. This also counts toward your personal baseline.
      </p>

      {(phase === "idle" || phase === "error") && (
        <>
          {error && (
            <p className="mb-3 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">
              {error}
            </p>
          )}
          <button
            type="button"
            onClick={start}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
          >
            Start recording
          </button>
        </>
      )}

      {phase === "requesting" && (
        <p className="text-sm text-neutral-500">Requesting microphone access...</p>
      )}

      {phase === "recording" && (
        <div>
          <p className="mb-1 font-mono text-sm tabular-nums text-neutral-500">
            {Math.floor(elapsedSeconds / 60)}:{String(elapsedSeconds % 60).padStart(2, "0")}
          </p>
          <div className="mb-4">
            <PitchMeter liveHz={liveHz} goalHz={goalHz} />
          </div>
          <button
            type="button"
            onClick={stop}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500"
          >
            Stop
          </button>
        </div>
      )}

      {phase === "uploading" && <p className="text-sm text-neutral-500">Analyzing...</p>}

      {phase === "result" && result && (
        <div>
          {hz != null ? (
            <>
              <p className="mb-1 text-3xl font-semibold tracking-tight text-neutral-100">
                {noteName}
              </p>
              <p className="mb-4 text-xs text-neutral-500">Average: {hz.toFixed(1)} Hz</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={useAsAvgGoal}
                  disabled={savingGoal || goalSaved}
                  className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
                >
                  {goalSaved
                    ? "Saved as your Avg goal tone"
                    : savingGoal
                      ? "Saving..."
                      : "Use as my Avg goal tone"}
                </button>
                <button
                  type="button"
                  onClick={start}
                  className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
                >
                  Record again
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-neutral-500">
              Could not measure a clear pitch from that recording — try again with a longer or
              clearer sample.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
