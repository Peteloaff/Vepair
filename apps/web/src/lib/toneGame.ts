// Pure functions for the Tone Match Challenge (5-tone scored game) — target-note selection and
// per-note scoring. Deliberately built on top of pitchGrading.ts's gradeToneMatch rather than
// re-deriving its median/semitone-distance logic, so "close enough" means the same thing here
// as it does in the ungraded single-note practice flow this game sits alongside.

import { semitoneDifference } from "./pitchDetector";
import { gradeToneMatch, CLOSE_SEMITONES, type ToneMatchResult } from "./pitchGrading";
import { midiToFrequency, midiToNoteName, noteNameToMidi, type ReferenceNote } from "./notes";

export const GAME_ATTEMPT_COUNT = 5;

// 6 seconds per tone (a short tone-playback cue, then a listening window), 5 tones = 30
// seconds per game.
export const GAME_TONE_DURATION_MS = 1000;
export const GAME_LISTEN_DURATION_MS = 5000;

const ACCURACY_MAX_POINTS = 60;
const ACCURACY_SEMITONE_PENALTY = 40;
const HOLD_MAX_POINTS = 30;
const REACTION_MAX_POINTS = 10;
const REACTION_FALLOFF_MS = 5000;

/** Picks `count` target notes from the singer's own measured vocal range (inclusive of both
 * endpoints), distinct where the range is wide enough to allow it. A range narrower than
 * `count` semitones falls back to sampling with replacement rather than failing — a real, if
 * narrow, measured range is still usable for the game. */
export function pickTargetNotes(
  lowNote: string,
  highNote: string,
  count: number = GAME_ATTEMPT_COUNT,
  rng: () => number = Math.random
): ReferenceNote[] {
  const lowMidi = noteNameToMidi(lowNote);
  const highMidi = noteNameToMidi(highNote);
  const rangeLow = Math.min(lowMidi, highMidi);
  const rangeHigh = Math.max(lowMidi, highMidi);
  const rangeWidth = rangeHigh - rangeLow + 1;

  const pool: number[] = [];
  for (let midi = rangeLow; midi <= rangeHigh; midi++) pool.push(midi);

  const chosen: number[] = [];
  if (rangeWidth >= count) {
    const remaining = [...pool];
    for (let i = 0; i < count; i++) {
      const index = Math.floor(rng() * remaining.length);
      chosen.push(remaining.splice(index, 1)[0]);
    }
  } else {
    for (let i = 0; i < count; i++) {
      chosen.push(pool[Math.floor(rng() * pool.length)]);
    }
  }

  return chosen.map((midi) => ({
    label: midiToNoteName(midi),
    midi,
    frequencyHz: midiToFrequency(midi),
  }));
}

export interface ToneGameAttemptResult extends ToneMatchResult {
  /** Fraction (0-1) of pitch samples during the listening window that landed within the
   * "close" band around the target note — how long the singer held it, not just whether the
   * median attempt was close. */
  holdFraction: number;
  /** Milliseconds from the start of the listening window to the first sample that landed
   * within the "close" band. Null if the close band was never reached. */
  reactionMs: number | null;
  /** 0-100: accuracy (0-60) + hold (0-30) + reaction (0-10). */
  score: number;
}

export interface PitchSample {
  hz: number;
  atMs: number;
}

/** Scores one attempt in the 5-tone challenge from the raw pitch-sample stream collected
 * during its listening window (already voiced-only — see detectPitch/onChunk in
 * tone-match/page.tsx, same as the single-note flow). */
export function scoreToneGameAttempt(
  targetHz: number,
  targetLabel: string,
  samples: PitchSample[]
): ToneGameAttemptResult {
  const graded = gradeToneMatch(
    targetHz,
    targetLabel,
    samples.map((s) => s.hz)
  );

  if (samples.length === 0) {
    return { ...graded, holdFraction: 0, reactionMs: null, score: 0 };
  }

  let closeCount = 0;
  let reactionMs: number | null = null;
  for (const sample of samples) {
    const withinBand = Math.abs(semitoneDifference(targetHz, sample.hz)) <= CLOSE_SEMITONES;
    if (withinBand) {
      closeCount += 1;
      if (reactionMs === null) reactionMs = sample.atMs;
    }
  }
  const holdFraction = closeCount / samples.length;

  const accuracyPoints =
    graded.semitonesOff === null
      ? 0
      : Math.max(0, ACCURACY_MAX_POINTS - Math.abs(graded.semitonesOff) * ACCURACY_SEMITONE_PENALTY);
  const holdPoints = Math.round(holdFraction * HOLD_MAX_POINTS);
  const reactionPoints =
    reactionMs === null
      ? 0
      : Math.round(REACTION_MAX_POINTS * Math.max(0, 1 - reactionMs / REACTION_FALLOFF_MS));

  const score = Math.round(accuracyPoints) + holdPoints + reactionPoints;

  return { ...graded, holdFraction, reactionMs, score };
}
