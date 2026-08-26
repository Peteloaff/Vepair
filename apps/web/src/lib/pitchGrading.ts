// Grades a single tone-match attempt: how close was the sung pitch to a reference tone. Pure
// function, no Web Audio dependency — the caller (apps/web/src/app/tone-match/page.tsx)
// collects pitch samples via pitchDetector.ts during a fixed listening window and hands them
// here. Deliberately reuses the app's existing semitone convention (see pitch_stability_semitones
// throughout the backend, and semitoneDifference already in pitchDetector.ts) rather than
// introducing cents or any other new unit.

import { semitoneDifference } from "./pitchDetector";
import { midiToNoteName } from "./notes";

export type ToneMatchGrade = "spot_on" | "close" | "off" | "no_pitch";

export interface ToneMatchResult {
  targetHz: number;
  targetLabel: string;
  detectedHz: number | null;
  detectedLabel: string | null;
  /** Positive = sung sharp of the target, negative = flat. Null when no pitch was detected. */
  semitonesOff: number | null;
  grade: ToneMatchGrade;
}

const SPOT_ON_SEMITONES = 0.25;
// Exported for toneGame.ts's hold-fraction scoring — "matching" a note during the 5-tone
// challenge uses the same closeness band as this single-note grader's "close" tier, so the
// two never drift apart into different definitions of "close enough."
export const CLOSE_SEMITONES = 0.5;

export const GRADE_LABEL: Record<ToneMatchGrade, string> = {
  spot_on: "Spot on!",
  close: "Close",
  off: "Off pitch",
  no_pitch: "No clear pitch detected",
};

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function frequencyToNearestMidi(hz: number): number {
  return Math.round(69 + 12 * Math.log2(hz / 440));
}

/** `detectedSamplesHz` should already be voiced-only frequency estimates (e.g. from
 * pitchDetector.ts's detectPitch, filtered for non-null results) — silence/unvoiced frames
 * must never be averaged in as if they were a pitch. An empty array means no pitch was ever
 * detected during the window, which is its own outcome ("no_pitch"), not a score of zero. */
export function gradeToneMatch(
  targetHz: number,
  targetLabel: string,
  detectedSamplesHz: number[]
): ToneMatchResult {
  if (detectedSamplesHz.length === 0) {
    return {
      targetHz,
      targetLabel,
      detectedHz: null,
      detectedLabel: null,
      semitonesOff: null,
      grade: "no_pitch",
    };
  }

  const detectedHz = median(detectedSamplesHz);
  const semitonesOff = semitoneDifference(targetHz, detectedHz);
  const absOff = Math.abs(semitonesOff);
  const grade: ToneMatchGrade =
    absOff <= SPOT_ON_SEMITONES ? "spot_on" : absOff <= CLOSE_SEMITONES ? "close" : "off";

  return {
    targetHz,
    targetLabel,
    detectedHz,
    detectedLabel: midiToNoteName(frequencyToNearestMidi(detectedHz)),
    semitonesOff,
    grade,
  };
}
