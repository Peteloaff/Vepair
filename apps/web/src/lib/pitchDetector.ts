// Real-time pitch detection for Stage 7's live coaching. A deliberately simple, well-understood
// technique — normalized autocorrelation — rather than anything ML-based: this only needs to
// track "roughly what note am I on right now" for live feedback, not the archival-precision F0
// Stage 3 already gets from Parselmouth/Praat on the finished recording. Pure function, no
// Web Audio dependency, so it's directly unit-testable with synthetic sine waves (see
// pitchDetector.test.ts) the same way Stage 3's known-frequency tests validate the backend.

export interface PitchResult {
  frequencyHz: number;
  /** Normalized autocorrelation strength at the chosen lag, 0-1. Not a statistical confidence
   * interval — just "how periodic does this window look." */
  confidence: number;
}

// Covers typical speaking/singing range including falsetto/head voice, with margin. Frequencies
// outside this band are outside what this detector looks for, not evidence of "no pitch."
const MIN_FREQUENCY_HZ = 60;
const MAX_FREQUENCY_HZ = 1000;

// Below this RMS, the frame is treated as silence — never invent a pitch for silence.
const SILENCE_RMS_THRESHOLD = 0.01;

// Below this normalized-correlation strength, the estimate isn't trusted enough to report —
// matches "never present false precision" (MEDICAL_SAFETY.md): a shaky guess returns null,
// not a number the caller has no way to know is shaky.
const MIN_CONFIDENCE = 0.85;

export function computeRms(buffer: Float32Array): number {
  if (buffer.length === 0) return 0;
  let sumSquares = 0;
  for (let i = 0; i < buffer.length; i++) sumSquares += buffer[i] * buffer[i];
  return Math.sqrt(sumSquares / buffer.length);
}

/** Detects the fundamental frequency of one audio frame via normalized autocorrelation.
 * Returns null for silence, unvoiced/noisy input, or a buffer too short to detect the lowest
 * frequency this function looks for — never a fabricated pitch for input with no clear pitch. */
export function detectPitch(buffer: Float32Array, sampleRate: number): PitchResult | null {
  if (computeRms(buffer) < SILENCE_RMS_THRESHOLD) return null;

  const minLag = Math.floor(sampleRate / MAX_FREQUENCY_HZ);
  const maxLag = Math.min(Math.floor(sampleRate / MIN_FREQUENCY_HZ), buffer.length - 1);
  if (maxLag <= minLag) return null;

  const correlations = new Float32Array(maxLag - minLag + 1);
  for (let lag = minLag; lag <= maxLag; lag++) {
    let dot = 0;
    let normA = 0;
    let normB = 0;
    const limit = buffer.length - lag;
    for (let i = 0; i < limit; i++) {
      const a = buffer[i];
      const b = buffer[i + lag];
      dot += a * b;
      normA += a * a;
      normB += b * b;
    }
    const denom = Math.sqrt(normA * normB);
    correlations[lag - minLag] = denom > 0 ? dot / denom : 0;
  }

  // A pure periodic tone correlates strongly not just at its true period but at every integer
  // multiple of it too (2x period, 3x period, ...), so taking the single highest correlation
  // across the whole lag range is prone to octave-down errors (locking onto a subharmonic).
  // Instead, walk from the shortest lag (highest frequency) up and take the first strong local
  // peak — the standard fix, and the reason this is a peak-picking loop rather than a max().
  for (let i = 1; i < correlations.length - 1; i++) {
    const correlation = correlations[i];
    if (
      correlation >= MIN_CONFIDENCE &&
      correlation >= correlations[i - 1] &&
      correlation >= correlations[i + 1]
    ) {
      const lag = minLag + i;
      return { frequencyHz: sampleRate / lag, confidence: correlation };
    }
  }

  return null;
}

/** Semitone difference between two frequencies (positive = b is higher). The app's existing
 * convention for pitch differences (see pitch_stability_semitones in the backend) — musically
 * meaningful and scale-independent, unlike a raw Hz difference. */
export function semitoneDifference(fromHz: number, toHz: number): number {
  return 12 * Math.log2(toHz / fromHz);
}
