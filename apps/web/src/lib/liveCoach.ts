"use client";

// Stage 7's Web Audio integration layer. Wraps Stage 2's AudioRecorder (already handles
// microphone permission and Web Audio setup) rather than duplicating that, and layers the pure
// pitchDetector/feedbackEngine logic on top, frame by frame, in real time.
//
// Live *feedback* is entirely client-side and never leaves the browser. `stop()` also returns
// the raw recording, though — Stage 8 ("listen to your exercises and track improvement")
// optionally uploads it for exercises with a target_measurement, so the deeper Parselmouth
// analysis (Stage 3's pipeline, not a second live algorithm) can run server-side. The caller
// (apps/web/src/app/exercises/page.tsx) decides whether to use or discard the bytes — this
// class stays a general-purpose recorder+coach, not a privacy-policy decision point.

import { computeRms, detectPitch } from "./pitchDetector";
import {
  createFeedbackEngineState,
  processSample,
  type FeedbackContext,
  type FeedbackEngineState,
  type FeedbackMessage,
} from "./feedbackEngine";
import { AudioRecorder, MicrophonePermissionDeniedError, MicrophoneUnavailableError } from "./recorder";

export { MicrophonePermissionDeniedError, MicrophoneUnavailableError };

export interface LiveCoachSummary {
  /** Fraction of processed frames with a detected pitch — a rough "how much of this exercise
   * was actually phonated" completion signal, not a precision measurement. */
  voicedRatio: number;
  frameCount: number;
  /** Average time to analyze one frame (pitch detection + feedback rules), in ms. Null if no
   * frames were processed. This is the dominant component of Stage 7's "analysis latency" —
   * see TESTING.md Stage 7. */
  averageAnalysisLatencyMs: number | null;
  /** The raw WAV recording, for the caller to optionally upload for deeper server-side
   * analysis (Stage 8) — see the module docstring above. */
  wavBytes: ArrayBuffer;
}

export class LiveCoachSession {
  private recorder = new AudioRecorder();
  private engineState: FeedbackEngineState = createFeedbackEngineState();
  private context: FeedbackContext | null = null;
  private startedAtMs = 0;
  private voicedFrameCount = 0;
  private frameCount = 0;
  private analysisLatenciesMs: number[] = [];

  /** Called synchronously whenever a new feedback message is decided. Keep this cheap — it
   * runs on every audio chunk, not just when there's a message. */
  onFeedback: ((message: FeedbackMessage) => void) | null = null;

  async requestPermissionAndPrepare(): Promise<void> {
    await this.recorder.requestPermissionAndPrepare();
  }

  getMicrophoneLabel(): string | null {
    return this.recorder.getMicrophoneLabel();
  }

  start(context: FeedbackContext): void {
    this.context = context;
    this.engineState = createFeedbackEngineState();
    this.voicedFrameCount = 0;
    this.frameCount = 0;
    this.analysisLatenciesMs = [];
    this.startedAtMs = performance.now();

    this.recorder.onChunk = (chunk) => this.handleChunk(chunk);
    this.recorder.start();
  }

  private handleChunk(chunk: Float32Array): void {
    if (!this.context) return;
    const sampleRate = this.recorder.getSampleRate();
    if (!sampleRate) return;

    const analysisStart = performance.now();
    const pitch = detectPitch(chunk, sampleRate);
    const rms = computeRms(chunk);
    this.analysisLatenciesMs.push(performance.now() - analysisStart);

    this.frameCount += 1;
    if (pitch !== null) this.voicedFrameCount += 1;

    const result = processSample(
      this.engineState,
      { timestampMs: performance.now() - this.startedAtMs, pitchHz: pitch?.frequencyHz ?? null, rms },
      this.context
    );
    this.engineState = result.state;
    if (result.message) this.onFeedback?.(result.message);
  }

  /** Stops capturing and releases Web Audio nodes. Returns the recording alongside the live
   * summary — see the module docstring for who decides what happens to it. */
  stop(): LiveCoachSummary {
    const { wavBytes } = this.recorder.stop();
    return {
      voicedRatio: this.frameCount > 0 ? this.voicedFrameCount / this.frameCount : 0,
      frameCount: this.frameCount,
      averageAnalysisLatencyMs:
        this.analysisLatenciesMs.length > 0
          ? this.analysisLatenciesMs.reduce((a, b) => a + b, 0) / this.analysisLatenciesMs.length
          : null,
      wavBytes,
    };
  }

  /** Releases the microphone entirely. Call when leaving the exercise flow. */
  release(): void {
    this.recorder.release();
  }
}
