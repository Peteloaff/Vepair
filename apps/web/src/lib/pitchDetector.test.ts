import { describe, expect, it } from "vitest";
import { computeRms, detectPitch, semitoneDifference } from "./pitchDetector";

const SAMPLE_RATE = 44100;

function sineWave(freqHz: number, durationS: number, amplitude = 0.5): Float32Array {
  const n = Math.floor(SAMPLE_RATE * durationS);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    out[i] = amplitude * Math.sin((2 * Math.PI * freqHz * i) / SAMPLE_RATE);
  }
  return out;
}

function silence(durationS: number): Float32Array {
  return new Float32Array(Math.floor(SAMPLE_RATE * durationS));
}

function whiteNoise(durationS: number, amplitude = 0.5): Float32Array {
  const n = Math.floor(SAMPLE_RATE * durationS);
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = amplitude * (Math.random() * 2 - 1);
  return out;
}

describe("detectPitch", () => {
  it.each([110, 220, 440])("detects a pure %dHz tone within 1%%", (freq) => {
    const buffer = sineWave(freq, 0.1);
    const result = detectPitch(buffer, SAMPLE_RATE);
    expect(result).not.toBeNull();
    expect(result!.frequencyHz).toBeGreaterThan(freq * 0.99);
    expect(result!.frequencyHz).toBeLessThan(freq * 1.01);
  });

  it("returns null for silence, never a fabricated pitch", () => {
    expect(detectPitch(silence(0.1), SAMPLE_RATE)).toBeNull();
  });

  it("returns null for pure white noise", () => {
    expect(detectPitch(whiteNoise(0.1), SAMPLE_RATE)).toBeNull();
  });

  it("returns null for a buffer too short to detect the lowest frequency looked for", () => {
    const tiny = sineWave(440, 0.002); // ~88 samples at 44.1kHz
    expect(detectPitch(tiny, SAMPLE_RATE)).toBeNull();
  });

  it("still detects pitch under moderate simulated background noise", () => {
    // Approximates "moderate background noise" from the Stage 7 test plan -- no real noisy
    // room is available in this environment, so a tone is mixed with noise at a realistic
    // signal-to-noise ratio instead. Documented as a simulation, not a substitute for real
    // hardware/environment testing -- see TESTING.md Stage 7.
    const tone = sineWave(220, 0.1, 0.5);
    const noise = whiteNoise(0.1, 0.08);
    const mixed = tone.map((v, i) => v + noise[i]);
    const result = detectPitch(mixed, SAMPLE_RATE);
    expect(result).not.toBeNull();
    expect(result!.frequencyHz).toBeGreaterThan(220 * 0.98);
    expect(result!.frequencyHz).toBeLessThan(220 * 1.02);
  });

  it("confidence is high for a pure tone and reported alongside the frequency", () => {
    const result = detectPitch(sineWave(220, 0.1), SAMPLE_RATE);
    expect(result!.confidence).toBeGreaterThan(0.95);
  });
});

describe("computeRms", () => {
  it("is zero for silence", () => {
    expect(computeRms(silence(0.05))).toBe(0);
  });

  it("is proportional to amplitude for a sine wave", () => {
    const quiet = computeRms(sineWave(220, 0.05, 0.1));
    const loud = computeRms(sineWave(220, 0.05, 0.5));
    expect(loud).toBeGreaterThan(quiet * 4);
  });

  it("handles an empty buffer without throwing", () => {
    expect(computeRms(new Float32Array(0))).toBe(0);
  });
});

describe("semitoneDifference", () => {
  it("is 12 for exactly one octave up", () => {
    expect(semitoneDifference(220, 440)).toBeCloseTo(12, 5);
  });

  it("is 0 for the same frequency", () => {
    expect(semitoneDifference(220, 220)).toBeCloseTo(0, 5);
  });

  it("is negative for a lower target frequency", () => {
    expect(semitoneDifference(440, 220)).toBeCloseTo(-12, 5);
  });
});
