// Stage 7's real-time coaching rules. Pure and deterministic — given the same sequence of
// samples and context, always produces the same feedback — so it's fully unit-testable without
// a browser or a microphone (see feedbackEngine.test.ts).
//
// Every message here is phrased around something actually measured (pitch, volume, timing),
// never a claim about what's happening physically in the throat — see MEDICAL_SAFETY.md's rule
// against claiming the microphone can identify anatomical tension. The five message texts below
// are drawn directly from the product brief's own examples.

import { semitoneDifference } from "./pitchDetector";

export type CoachingProfile = "sustained" | "glide" | "none";

export interface FeedbackSample {
  timestampMs: number;
  /** null = silent/unvoiced frame (see pitchDetector.detectPitch) */
  pitchHz: number | null;
  rms: number;
}

export interface FeedbackContext {
  profile: CoachingProfile;
  /** The user's own established comfortable range, from their personal baseline (Stage 4) —
   * never a population norm. Either bound may be null if no baseline exists yet, in which case
   * the range-check rule simply doesn't fire (no data, no fabricated target). */
  comfortableMinHz: number | null;
  comfortableMaxHz: number | null;
  /** Minimum time between any two feedback messages — "configurable feedback frequency" and
   * "avoid overwhelming the user" from the product brief, in one knob. */
  minIntervalMs: number;
}

export type FeedbackTone = "positive" | "corrective";

export interface FeedbackMessage {
  text: string;
  tone: FeedbackTone;
  /** Which rule produced this message — not shown to the user, useful for tests/debugging. */
  rule: string;
}

export interface FeedbackEngineState {
  samples: FeedbackSample[];
  lastFeedbackAtMs: number | null;
  onsetChecked: boolean;
}

export function createFeedbackEngineState(): FeedbackEngineState {
  return { samples: [], lastFeedbackAtMs: null, onsetChecked: false };
}

const WINDOW_MS = 3000;
const RANGE_MARGIN_RATIO = 1.02;
const ONSET_HARD_RMS_THRESHOLD = 0.15;
const VOLUME_SPIKE_RATIO = 1.6;
const MIN_SAMPLES_FOR_VOLUME_BASELINE = 3;
const DRIFT_MIN_VOICED_MS = 2000;
const DRIFT_THRESHOLD_SEMITONES = 0.7;
const STEADY_MIN_VOICED_MS = 1500;
const STEADY_MAX_RANGE_SEMITONES = 0.5;

export function processSample(
  state: FeedbackEngineState,
  sample: FeedbackSample,
  context: FeedbackContext
): { state: FeedbackEngineState; message: FeedbackMessage | null } {
  const samples = [...state.samples, sample].filter(
    (s) => sample.timestampMs - s.timestampMs <= WINDOW_MS
  );
  const trimmedState: FeedbackEngineState = { ...state, samples };

  if (context.profile === "none") {
    return { state: trimmedState, message: null };
  }

  const sinceLastFeedback =
    state.lastFeedbackAtMs === null ? Infinity : sample.timestampMs - state.lastFeedbackAtMs;
  if (sinceLastFeedback < context.minIntervalMs) {
    return { state: trimmedState, message: null };
  }

  if (context.profile === "glide" && sample.pitchHz !== null) {
    if (
      context.comfortableMaxHz !== null &&
      sample.pitchHz > context.comfortableMaxHz * RANGE_MARGIN_RATIO
    ) {
      return emit(trimmedState, sample.timestampMs, "range-high");
    }
    if (
      context.comfortableMinHz !== null &&
      sample.pitchHz < context.comfortableMinHz / RANGE_MARGIN_RATIO
    ) {
      return emit(trimmedState, sample.timestampMs, "range-low");
    }
  }

  if (!trimmedState.onsetChecked) {
    const isHarsh = checkOnset(samples);
    if (isHarsh !== null) {
      const checkedState = { ...trimmedState, onsetChecked: true };
      if (isHarsh) {
        return emit(checkedState, sample.timestampMs, "onset");
      }
      return processRemainingRules(checkedState, sample, context, samples);
    }
  }

  return processRemainingRules(trimmedState, sample, context, samples);
}

function processRemainingRules(
  state: FeedbackEngineState,
  sample: FeedbackSample,
  context: FeedbackContext,
  samples: FeedbackSample[]
): { state: FeedbackEngineState; message: FeedbackMessage | null } {
  if (checkVolumeSpike(samples)) {
    return emit(state, sample.timestampMs, "volume-spike");
  }

  if (context.profile === "sustained" && checkPitchDrift(samples)) {
    return emit(state, sample.timestampMs, "pitch-drift");
  }

  if (checkSteady(samples)) {
    return emit(state, sample.timestampMs, "steady");
  }

  return { state, message: null };
}

const RULE_MESSAGES: Record<string, FeedbackMessage> = {
  "range-high": { text: "Stay within your comfortable range.", tone: "corrective", rule: "range-high" },
  "range-low": { text: "Stay within your comfortable range.", tone: "corrective", rule: "range-low" },
  onset: { text: "Try a gentler onset.", tone: "corrective", rule: "onset" },
  "volume-spike": { text: "Reduce volume slightly.", tone: "corrective", rule: "volume-spike" },
  "pitch-drift": { text: "Your pitch rose near the end.", tone: "corrective", rule: "pitch-drift" },
  steady: { text: "Good — keep this pitch steady.", tone: "positive", rule: "steady" },
};

function emit(
  state: FeedbackEngineState,
  atMs: number,
  ruleKey: keyof typeof RULE_MESSAGES
): { state: FeedbackEngineState; message: FeedbackMessage } {
  return {
    state: { ...state, lastFeedbackAtMs: atMs },
    message: RULE_MESSAGES[ruleKey],
  };
}

/** true = harsh onset, false = gentle onset, null = no voiced sample yet to judge. Checked once
 * per exercise attempt against the very first voiced frame — a real glottal attack shows up as
 * a sudden jump straight to a loud level with no gradual ramp, which at this analyzer's frame
 * granularity (~90ms chunks) is well-approximated by "was the first voiced frame already loud." */
function checkOnset(samples: FeedbackSample[]): boolean | null {
  const firstVoiced = samples.find((s) => s.pitchHz !== null);
  if (!firstVoiced) return null;
  return firstVoiced.rms > ONSET_HARD_RMS_THRESHOLD;
}

function checkVolumeSpike(samples: FeedbackSample[]): boolean {
  if (samples.length < MIN_SAMPLES_FOR_VOLUME_BASELINE + 1) return false;
  const latest = samples[samples.length - 1];
  const priorVoiced = samples.slice(0, -1).filter((s) => s.pitchHz !== null);
  if (priorVoiced.length < MIN_SAMPLES_FOR_VOLUME_BASELINE) return false;
  const baseline = priorVoiced.reduce((sum, s) => sum + s.rms, 0) / priorVoiced.length;
  if (baseline <= 0) return false;
  return latest.rms > baseline * VOLUME_SPIKE_RATIO;
}

function checkPitchDrift(samples: FeedbackSample[]): boolean {
  const voiced = samples.filter((s) => s.pitchHz !== null);
  if (voiced.length === 0) return false;
  const span = voiced[voiced.length - 1].timestampMs - voiced[0].timestampMs;
  if (span < DRIFT_MIN_VOICED_MS) return false;

  const mid = voiced[0].timestampMs + span / 2;
  const firstHalf = voiced.filter((s) => s.timestampMs < mid);
  const secondHalf = voiced.filter((s) => s.timestampMs >= mid);
  if (firstHalf.length === 0 || secondHalf.length === 0) return false;

  const firstMean = meanHz(firstHalf);
  const secondMean = meanHz(secondHalf);
  return semitoneDifference(firstMean, secondMean) > DRIFT_THRESHOLD_SEMITONES;
}

function checkSteady(samples: FeedbackSample[]): boolean {
  const voiced = samples.filter((s) => s.pitchHz !== null);
  if (voiced.length === 0) return false;
  const span = voiced[voiced.length - 1].timestampMs - voiced[0].timestampMs;
  if (span < STEADY_MIN_VOICED_MS) return false;

  const hzValues = voiced.map((s) => s.pitchHz as number);
  const minHz = Math.min(...hzValues);
  const maxHz = Math.max(...hzValues);
  return semitoneDifference(minHz, maxHz) <= STEADY_MAX_RANGE_SEMITONES;
}

function meanHz(samples: FeedbackSample[]): number {
  return samples.reduce((sum, s) => sum + (s.pitchHz as number), 0) / samples.length;
}

/** Which coaching profile applies to an exercise category — derived from the Stage 6 exercise
 * library. Breathing has no vocal signal to analyze, so it gets no live coaching at all. */
export function coachingProfileForCategory(category: string): CoachingProfile {
  if (category === "Breathing") return "none";
  if (category === "Pitch glides" || category === "Gentle sirens" || category === "Range exploration") {
    return "glide";
  }
  return "sustained";
}
