"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import Link from "next/link";
import { toBlob } from "html-to-image";
import { RequireAuth } from "@/components/RequireAuth";
import { Waveform, type WaveformHandle } from "@/components/Waveform";
import { ToneMatchResultCard } from "@/components/ToneMatchResultCard";
import { ToneGameResultCard } from "@/components/ToneGameResultCard";
import { GoalTonesEditor } from "@/components/GoalTonesEditor";
import { AveragePitchRecorder } from "@/components/AveragePitchRecorder";
import { PitchMeter } from "@/components/PitchMeter";
import { useAuth } from "@/lib/auth-context";
import {
  AudioRecorder,
  MicrophonePermissionDeniedError,
  MicrophoneUnavailableError,
} from "@/lib/recorder";
import { detectPitch } from "@/lib/pitchDetector";
import { buildReferenceRange, playTone, type ReferenceNote } from "@/lib/notes";
import { gradeToneMatch, type ToneMatchResult } from "@/lib/pitchGrading";
import {
  GAME_ATTEMPT_COUNT,
  GAME_LISTEN_DURATION_MS,
  GAME_TONE_DURATION_MS,
  pickTargetNotes,
  scoreToneGameAttempt,
  type PitchSample,
  type ToneGameAttemptResult,
} from "@/lib/toneGame";
import type { ToneGameAttempt as ToneGameAttemptOut, ToneGameSession, VocalRangeSummary } from "@/lib/types";

type Phase =
  | "intro"
  | "requesting-permission"
  | "permission-denied"
  | "no-microphone"
  | "ready"
  | "tone-playing"
  | "listening"
  | "graded"
  | "game-checking-range"
  | "game-no-range"
  | "game-tone-playing"
  | "game-listening"
  | "game-complete";

const NOTES = buildReferenceRange();
const TONE_DURATION_MS = 2000;
const LISTEN_DURATION_SECONDS = 7;
const CARD_WIDTH = 1080;
const CARD_HEIGHT = 1920;
const PREVIEW_WIDTH = 280;

function ToneMatchFlow() {
  const { apiFetch } = useAuth();
  const [phase, setPhase] = useState<Phase>("intro");
  const [selectedNote, setSelectedNote] = useState<ReferenceNote | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState(LISTEN_DURATION_SECONDS);
  const [result, setResult] = useState<ToneMatchResult | null>(null);
  const [liveHz, setLiveHz] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shareBusy, setShareBusy] = useState<string | null>(null);
  const [shareError, setShareError] = useState<string | null>(null);

  // 5-Tone Challenge (game mode) — a separate loop sharing the same recorder/pitch-detection
  // plumbing as the free-practice flow above.
  const [gameError, setGameError] = useState<string | null>(null);
  const [gameTargets, setGameTargets] = useState<ReferenceNote[]>([]);
  const [gameIndex, setGameIndex] = useState(0);
  const [gameAttempts, setGameAttempts] = useState<ToneGameAttemptResult[]>([]);
  const [gameSubmitting, setGameSubmitting] = useState(false);
  const [gameSaveError, setGameSaveError] = useState<string | null>(null);
  const [gameShareBusy, setGameShareBusy] = useState<string | null>(null);
  const [gameShareError, setGameShareError] = useState<string | null>(null);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const waveformRef = useRef<WaveformHandle>(null);
  const pitchSamplesRef = useRef<number[]>([]);
  const countdownIntervalRef = useRef<number | null>(null);
  const stopTimeoutRef = useRef<number | null>(null);
  const resultCardRef = useRef<HTMLDivElement>(null);
  const gameResultCardRef = useRef<HTMLDivElement>(null);
  const gameSamplesRef = useRef<PitchSample[]>([]);
  const gameAttemptsRef = useRef<ToneGameAttemptResult[]>([]);
  const gameListenStartRef = useRef<number>(0);

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
    setLiveHz(null);
    recorder.onChunk = (chunk) => {
      waveformRef.current?.pushChunk(chunk);
      const sampleRate = recorder.getSampleRate();
      if (!sampleRate) return;
      const pitch = detectPitch(chunk, sampleRate);
      setLiveHz(pitch?.frequencyHz ?? null);
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
    setLiveHz(null);
    const graded = gradeToneMatch(note.frequencyHz, note.label, pitchSamplesRef.current);
    setResult(graded);
    setPhase("graded");
  }

  function pickAnotherNote() {
    setResult(null);
    setSelectedNote(null);
    setPhase("ready");
  }

  async function startGame() {
    setGameError(null);
    setGameSaveError(null);
    setPhase("game-checking-range");
    try {
      const summary = await apiFetch<VocalRangeSummary>("/api/v1/vocal-range/summary");
      if (!summary.current_low_note || !summary.current_high_note) {
        setPhase("game-no-range");
        return;
      }
      const targets = pickTargetNotes(
        summary.current_low_note,
        summary.current_high_note,
        GAME_ATTEMPT_COUNT
      );
      gameAttemptsRef.current = [];
      setGameAttempts([]);
      setGameTargets(targets);
      setGameIndex(0);
      await playGameNote(targets, 0);
    } catch {
      setGameError("Could not check your vocal range. Please try again.");
      setPhase("ready");
    }
  }

  async function playGameNote(targets: ReferenceNote[], index: number) {
    setPhase("game-tone-playing");
    await playTone(targets[index].frequencyHz, GAME_TONE_DURATION_MS);
    beginGameListening(targets, index);
  }

  function beginGameListening(targets: ReferenceNote[], index: number) {
    const recorder = recorderRef.current;
    if (!recorder) return;

    gameSamplesRef.current = [];
    waveformRef.current?.reset();
    setLiveHz(null);
    // Only ever reached via a user-triggered chain (the "Start the challenge" button, or the
    // per-note setTimeout advancing to the next tone) -- never during render. The compiler's
    // purity check can't trace that through the intervening async playGameNote() hop, the same
    // way it can for a function bound directly to an onClick prop (see beginRecording in
    // vocal-range/page.tsx for that directly-recognized shape).
    // eslint-disable-next-line react-hooks/purity
    gameListenStartRef.current = performance.now();
    recorder.onChunk = (chunk) => {
      waveformRef.current?.pushChunk(chunk);
      const sampleRate = recorder.getSampleRate();
      if (!sampleRate) return;
      const pitch = detectPitch(chunk, sampleRate);
      setLiveHz(pitch?.frequencyHz ?? null);
      if (pitch) {
        gameSamplesRef.current.push({
          hz: pitch.frequencyHz,
          atMs: performance.now() - gameListenStartRef.current,
        });
      }
    };
    recorder.start();
    setPhase("game-listening");
    setRemainingSeconds(Math.round(GAME_LISTEN_DURATION_MS / 1000));

    countdownIntervalRef.current = window.setInterval(() => {
      setRemainingSeconds((s) => Math.max(0, s - 1));
    }, 1000);

    stopTimeoutRef.current = window.setTimeout(() => {
      finishGameListening(targets, index);
    }, GAME_LISTEN_DURATION_MS);
  }

  function finishGameListening(targets: ReferenceNote[], index: number) {
    if (countdownIntervalRef.current !== null) window.clearInterval(countdownIntervalRef.current);
    recorderRef.current?.stop();
    setLiveHz(null);

    const note = targets[index];
    const scored = scoreToneGameAttempt(note.frequencyHz, note.label, gameSamplesRef.current);
    gameAttemptsRef.current = [...gameAttemptsRef.current, scored];
    setGameAttempts(gameAttemptsRef.current);

    if (index + 1 < targets.length) {
      setGameIndex(index + 1);
      playGameNote(targets, index + 1);
    } else {
      finishGame(gameAttemptsRef.current);
    }
  }

  async function finishGame(attempts: ToneGameAttemptResult[]) {
    setPhase("game-complete");
    setGameSubmitting(true);
    setGameSaveError(null);
    try {
      await apiFetch<ToneGameSession>("/api/v1/tone-game/sessions", {
        method: "POST",
        body: {
          attempts: attempts.map((a, i) => ({
            order_index: i,
            target_note: a.targetLabel,
            target_hz: a.targetHz,
            detected_hz: a.detectedHz,
            semitones_off: a.semitonesOff,
            grade: a.grade,
            hold_fraction: a.holdFraction,
            reaction_ms: a.reactionMs,
            score: a.score,
          })),
        },
      });
    } catch {
      setGameSaveError("Your score was calculated but could not be saved.");
    } finally {
      setGameSubmitting(false);
    }
  }

  function playGameAgain() {
    setGameShareError(null);
    startGame();
  }

  async function exportResultBlob(cardRef: RefObject<HTMLDivElement | null>): Promise<Blob> {
    if (!cardRef.current) throw new Error("Nothing to export yet.");
    if (document.fonts?.ready) await document.fonts.ready;
    const blob = await toBlob(cardRef.current, {
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
      const blob = await exportResultBlob(resultCardRef);
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
      const blob = await exportResultBlob(resultCardRef);
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

  async function handleGameSave() {
    setGameShareError(null);
    setGameShareBusy("save");
    try {
      const blob = await exportResultBlob(gameResultCardRef);
      downloadBlob(blob, "vepair-5-tone-challenge.png");
    } catch {
      setGameShareError("Could not save this image. Please try again.");
    } finally {
      setGameShareBusy(null);
    }
  }

  async function handleGameShare() {
    setGameShareError(null);
    setGameShareBusy("share");
    try {
      const blob = await exportResultBlob(gameResultCardRef);
      const file = new File([blob], "vepair-5-tone-challenge.png", { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: "My VepAIr 5-Tone Challenge" });
      } else {
        downloadBlob(blob, "vepair-5-tone-challenge.png");
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setGameShareError("Could not share this image. Please try Save instead.");
    } finally {
      setGameShareBusy(null);
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

        <div className="mb-8 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
          <h2 className="mb-2 text-sm font-medium text-neutral-200">5-Tone Challenge</h2>
          <p className="mb-4 text-sm text-neutral-400">
            5 tones from your own vocal range, scored on accuracy, hold, and reaction &mdash;
            about 30 seconds.
          </p>
          <button
            type="button"
            onClick={startGame}
            className="rounded-lg bg-violet-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-violet-400"
          >
            Start the challenge
          </button>
          {gameError && <p className="mt-3 text-xs text-red-300">{gameError}</p>}
        </div>

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
        <div className="mx-auto mt-4 max-w-xs text-left">
          <PitchMeter liveHz={liveHz} goalHz={selectedNote.frequencyHz} />
        </div>
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

  if (phase === "game-checking-range") {
    return <p className="text-sm text-neutral-500">Checking your vocal range...</p>;
  }

  if (phase === "game-no-range") {
    return (
      <div className="mx-auto w-full max-w-lg text-sm">
        <h1 className="mb-2 text-xl font-semibold">Vocal range needed</h1>
        <p className="mb-4 text-neutral-400">
          The 5-Tone Challenge picks its notes from your own measured vocal range. Record one
          first, then come back and try again.
        </p>
        <div className="flex gap-2">
          <Link
            href="/vocal-range"
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400"
          >
            Go to vocal range test
          </Link>
          <button
            type="button"
            onClick={() => setPhase("ready")}
            className="rounded-lg border border-neutral-700 px-4 py-2 hover:bg-neutral-800"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  if (phase === "game-tone-playing" && gameTargets[gameIndex]) {
    return (
      <div className="mx-auto w-full max-w-lg text-center">
        <p className="mb-2 text-sm text-neutral-400">
          5-Tone Challenge &middot; Note {gameIndex + 1} of {gameTargets.length}
        </p>
        <p className="text-6xl font-bold tracking-tight text-neutral-100">
          {gameTargets[gameIndex].label}
        </p>
      </div>
    );
  }

  if (phase === "game-listening" && gameTargets[gameIndex]) {
    const note = gameTargets[gameIndex];
    return (
      <div className="mx-auto w-full max-w-lg text-center">
        <p className="mb-1 text-sm text-neutral-400">
          Note {gameIndex + 1} of {gameTargets.length} &mdash; target:
        </p>
        <p className="mb-4 text-4xl font-bold tracking-tight text-neutral-100">{note.label}</p>
        <Waveform ref={waveformRef} active={true} />
        <div className="mx-auto mt-4 max-w-xs text-left">
          <PitchMeter liveHz={liveHz} goalHz={note.frequencyHz} />
        </div>
        <p className="mt-3 font-mono text-2xl tabular-nums text-neutral-200">
          {remainingSeconds}s
        </p>
      </div>
    );
  }

  if (phase === "game-complete") {
    const totalScore = gameAttempts.reduce((sum, a) => sum + a.score, 0);
    const cardAttempts: ToneGameAttemptOut[] = gameAttempts.map((a, i) => ({
      order_index: i,
      target_note: a.targetLabel,
      target_hz: a.targetHz,
      detected_hz: a.detectedHz,
      semitones_off: a.semitonesOff,
      grade: a.grade,
      hold_fraction: a.holdFraction,
      reaction_ms: a.reactionMs,
      score: a.score,
    }));

    return (
      <div className="mx-auto w-full max-w-lg">
        {gameSubmitting && (
          <p className="mb-4 text-center text-sm text-neutral-500">Saving your score...</p>
        )}
        {gameSaveError && (
          <p className="mb-4 rounded-lg bg-red-950/50 px-3 py-2 text-center text-xs text-red-300">
            {gameSaveError}
          </p>
        )}

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
              <ToneGameResultCard
                ref={gameResultCardRef}
                attempts={cardAttempts}
                totalScore={totalScore}
                date={new Date().toLocaleDateString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                })}
              />
            </div>
          </div>
        </div>

        {gameShareError && (
          <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-center text-xs text-red-300">
            {gameShareError}
          </p>
        )}

        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            type="button"
            onClick={handleGameShare}
            disabled={gameShareBusy !== null}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
          >
            {gameShareBusy === "share" ? "Preparing..." : "Share"}
          </button>
          <button
            type="button"
            onClick={handleGameSave}
            disabled={gameShareBusy !== null}
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
          >
            {gameShareBusy === "save" ? "Saving..." : "Save"}
          </button>
          <button
            type="button"
            onClick={playGameAgain}
            disabled={gameShareBusy !== null}
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
          >
            Play again
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
