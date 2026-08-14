"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { toBlob } from "html-to-image";
import { RequireAuth } from "@/components/RequireAuth";
import { Waveform, type WaveformHandle } from "@/components/Waveform";
import { ToneMatchResultCard } from "@/components/ToneMatchResultCard";
import { GoalTonesEditor } from "@/components/GoalTonesEditor";
import { AveragePitchRecorder } from "@/components/AveragePitchRecorder";
import {
  AudioRecorder,
  MicrophonePermissionDeniedError,
  MicrophoneUnavailableError,
} from "@/lib/recorder";
import { detectPitch } from "@/lib/pitchDetector";
import { buildReferenceRange, playTone, type ReferenceNote } from "@/lib/notes";
import { gradeToneMatch, type ToneMatchResult } from "@/lib/pitchGrading";

type Phase =
  | "intro"
  | "requesting-permission"
  | "permission-denied"
  | "no-microphone"
  | "ready"
  | "tone-playing"
  | "listening"
  | "graded";

const NOTES = buildReferenceRange();
const TONE_DURATION_MS = 2000;
const LISTEN_DURATION_SECONDS = 7;
const CARD_WIDTH = 1080;
const CARD_HEIGHT = 1920;
const PREVIEW_WIDTH = 280;

function ToneMatchFlow() {
  const [phase, setPhase] = useState<Phase>("intro");
  const [selectedNote, setSelectedNote] = useState<ReferenceNote | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(LISTEN_DURATION_SECONDS);
  const [result, setResult] = useState<ToneMatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shareBusy, setShareBusy] = useState<string | null>(null);
  const [shareError, setShareError] = useState<string | null>(null);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const waveformRef = useRef<WaveformHandle>(null);
  const pitchSamplesRef = useRef<number[]>([]);
  const countdownIntervalRef = useRef<number | null>(null);
  const stopTimeoutRef = useRef<number | null>(null);
  const resultCardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    return () => {
      recorderRef.current?.release();
      if (countdownIntervalRef.current !== null) window.clearInterval(countdownIntervalRef.current);
      if (stopTimeoutRef.current !== null) window.clearTimeout(stopTimeoutRef.current);
    };
  }, []);

  async function startPracticing() {
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
    setPhase("ready");
  }

  async function attemptNote(note: ReferenceNote) {
    setSelectedNote(note);
    setResult(null);
    setShareError(null);
    setPhase("tone-playing");
    await playTone(note.frequencyHz, TONE_DURATION_MS);
    beginListening(note);
  }

  function beginListening(note: ReferenceNote) {
    const recorder = recorderRef.current;
    if (!recorder) return;

    pitchSamplesRef.current = [];
    waveformRef.current?.reset();
    recorder.onChunk = (chunk) => {
      waveformRef.current?.pushChunk(chunk);
      const sampleRate = recorder.getSampleRate();
      if (!sampleRate) return;
      const pitch = detectPitch(chunk, sampleRate);
      if (pitch) pitchSamplesRef.current.push(pitch.frequencyHz);
    };
    recorder.start();
    setPhase("listening");
    setRemainingSeconds(LISTEN_DURATION_SECONDS);

    countdownIntervalRef.current = window.setInterval(() => {
      setRemainingSeconds((s) => Math.max(0, s - 1));
    }, 1000);

    stopTimeoutRef.current = window.setTimeout(() => {
      finishListening(note);
    }, LISTEN_DURATION_SECONDS * 1000);
  }

  function finishListening(note: ReferenceNote) {
    if (countdownIntervalRef.current !== null) window.clearInterval(countdownIntervalRef.current);
    const recorder = recorderRef.current;
    // The recording itself is discarded — grading only needs the pitch samples already
    // collected via onChunk above, and nothing here is uploaded or saved (see the founder's
    // scoping decision: this is an ephemeral practice tool, not a tracked measurement).
    recorder?.stop();
    const graded = gradeToneMatch(note.frequencyHz, note.label, pitchSamplesRef.current);
    setResult(graded);
    setPhase("graded");
  }

  function pickAnotherNote() {
    setResult(null);
    setSelectedNote(null);
    setPhase("ready");
  }

  async function exportResultBlob(): Promise<Blob> {
    if (!resultCardRef.current) throw new Error("Nothing to export yet.");
    if (document.fonts?.ready) await document.fonts.ready;
    const blob = await toBlob(resultCardRef.current, {
      width: CARD_WIDTH,
      height: CARD_HEIGHT,
      pixelRatio: 1,
      backgroundColor: "#0a0a0a",
    });
    if (!blob) throw new Error("Could not generate image.");
    return blob;
  }

  function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleSave() {
    setShareError(null);
    setShareBusy("save");
    try {
      const blob = await exportResultBlob();
      downloadBlob(blob, "vepair-tone-match.png");
    } catch {
      setShareError("Could not save this image. Please try again.");
    } finally {
      setShareBusy(null);
    }
  }

  async function handleShare() {
    setShareError(null);
    setShareBusy("share");
    try {
      const blob = await exportResultBlob();
      const file = new File([blob], "vepair-tone-match.png", { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: "My VepAIr Tone Match" });
      } else {
        downloadBlob(blob, "vepair-tone-match.png");
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setShareError("Could not share this image. Please try Save instead.");
    } finally {
      setShareBusy(null);
    }
  }

  if (phase === "intro") {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Tone Match</h1>
        <p className="mb-6 text-sm text-neutral-400">
          Tap a note to hear it, then sing it back as closely as you can. A quick, ungraded-
          for-the-record practice tool — nothing here is saved or tracked over time.
        </p>

        {error && (
          <p className="mb-4 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
        )}

        <button
          type="button"
          onClick={startPracticing}
          className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
        >
          Start practicing
        </button>
      </div>
    );
  }

  if (phase === "requesting-permission") {
    return <p className="text-sm text-neutral-500">Requesting microphone access...</p>;
  }

  if (phase === "permission-denied") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <h1 className="mb-2 text-xl font-semibold">Microphone access needed</h1>
        <p className="mb-4 text-neutral-400">
          VepAIr needs microphone access to grade a tone match. You denied (or previously
          denied) permission. Check your browser&apos;s site settings for this page and allow
          the microphone, then try again.
        </p>
        <button
          type="button"
          onClick={startPracticing}
          className="rounded-lg border border-neutral-700 px-4 py-2 hover:bg-neutral-800"
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
        <p className="mb-4 text-neutral-400">
          VepAIr couldn&apos;t find a microphone on this device. Connect one and try again.
        </p>
        <button
          type="button"
          onClick={startPracticing}
          className="rounded-lg border border-neutral-700 px-4 py-2 hover:bg-neutral-800"
        >
          Try again
        </button>
      </div>
    );
  }

  if (phase === "ready") {
    return (
      <div className="mx-auto w-full max-w-lg">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Tone Match</h1>
        <p className="mb-6 text-sm text-neutral-400">Tap a note to hear it, then sing it back.</p>

        <div className="mb-8">
          <GoalTonesEditor />
        </div>

        <div className="mb-8">
          <AveragePitchRecorder />
        </div>

        <div className="grid grid-cols-6 gap-2">
          {NOTES.map((note) => (
            <button
              key={note.label}
              type="button"
              onClick={() => attemptNote(note)}
              className="rounded-lg border border-neutral-700 px-2 py-3 text-sm font-medium text-neutral-200 hover:bg-neutral-800"
            >
              {note.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (phase === "tone-playing" && selectedNote) {
    return (
      <div className="mx-auto w-full max-w-lg text-center">
        <p className="mb-2 text-sm text-neutral-400">Listen for the note...</p>
        <p className="text-6xl font-bold tracking-tight text-neutral-100">{selectedNote.label}</p>
      </div>
    );
  }

  if (phase === "listening" && selectedNote) {
    return (
      <div className="mx-auto w-full max-w-lg text-center">
        <p className="mb-1 text-sm text-neutral-400">Now sing it back &mdash; target:</p>
        <p className="mb-4 text-4xl font-bold tracking-tight text-neutral-100">
          {selectedNote.label}
        </p>
        <Waveform ref={waveformRef} active={true} />
        <p className="mt-3 font-mono text-2xl tabular-nums text-neutral-200">
          {remainingSeconds}s
        </p>
      </div>
    );
  }

  if (phase === "graded" && result) {
    return (
      <div className="mx-auto w-full max-w-lg">
        <div className="flex justify-center">
          <div
            className="overflow-hidden rounded-2xl border border-neutral-800"
            style={{
              width: CARD_WIDTH * (PREVIEW_WIDTH / CARD_WIDTH),
              height: CARD_HEIGHT * (PREVIEW_WIDTH / CARD_WIDTH),
            }}
          >
            <div
              style={{
                width: CARD_WIDTH,
                transform: `scale(${PREVIEW_WIDTH / CARD_WIDTH})`,
                transformOrigin: "top left",
              }}
            >
              <ToneMatchResultCard
                ref={resultCardRef}
                result={result}
                date={new Date().toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              />
            </div>
          </div>
        </div>

        {shareError && (
          <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-center text-xs text-red-300">
            {shareError}
          </p>
        )}

        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            type="button"
            onClick={handleShare}
            disabled={shareBusy !== null}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
          >
            {shareBusy === "share" ? "Preparing..." : "Share"}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={shareBusy !== null}
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
          >
            {shareBusy === "save" ? "Saving..." : "Save"}
          </button>
          <button
            type="button"
            onClick={pickAnotherNote}
            disabled={shareBusy !== null}
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
          >
            Try another note
          </button>
        </div>

        <div className="mt-8 text-center">
          <Link href="/" className="text-xs text-neutral-500 hover:text-neutral-300">
            Close
          </Link>
        </div>
      </div>
    );
  }

  return null;
}

export default function ToneMatchPage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <ToneMatchFlow />
      </main>
    </RequireAuth>
  );
}
