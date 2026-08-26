import { describe, expect, it } from "vitest";
import { pickTargetNotes, scoreToneGameAttempt } from "./toneGame";
import { noteNameToMidi } from "./notes";

describe("pickTargetNotes", () => {
  it("picks the requested count of notes", () => {
    const notes = pickTargetNotes("C3", "C5", 5);
    expect(notes).toHaveLength(5);
  });

  it("keeps every pick within the requested range", () => {
    const lowMidi = noteNameToMidi("C3");
    const highMidi = noteNameToMidi("C5");
    const notes = pickTargetNotes("C3", "C5", 5);
    for (const note of notes) {
      expect(note.midi).toBeGreaterThanOrEqual(lowMidi);
      expect(note.midi).toBeLessThanOrEqual(highMidi);
    }
  });

  it("picks distinct notes when the range is wide enough", () => {
    const notes = pickTargetNotes("C3", "C5", 5);
    const distinctMidis = new Set(notes.map((n) => n.midi));
    expect(distinctMidis.size).toBe(5);
  });

  it("falls back to sampling with replacement when the range is narrower than the count", () => {
    // C4-D4 is only 3 semitones wide -- can't produce 5 distinct picks.
    const notes = pickTargetNotes("C4", "D4", 5);
    expect(notes).toHaveLength(5);
    const lowMidi = noteNameToMidi("C4");
    const highMidi = noteNameToMidi("D4");
    for (const note of notes) {
      expect(note.midi).toBeGreaterThanOrEqual(lowMidi);
      expect(note.midi).toBeLessThanOrEqual(highMidi);
    }
  });

  it("handles a low/high pair given in reverse order", () => {
    const notes = pickTargetNotes("C5", "C3", 5);
    const lowMidi = noteNameToMidi("C3");
    const highMidi = noteNameToMidi("C5");
    for (const note of notes) {
      expect(note.midi).toBeGreaterThanOrEqual(lowMidi);
      expect(note.midi).toBeLessThanOrEqual(highMidi);
    }
  });
});

describe("scoreToneGameAttempt", () => {
  it("scores a spot-on, fully-held, instant-reaction attempt near the max", () => {
    const samples = Array.from({ length: 20 }, (_, i) => ({ hz: 440, atMs: i * 100 }));
    const result = scoreToneGameAttempt(440, "A4", samples);
    expect(result.grade).toBe("spot_on");
    expect(result.holdFraction).toBe(1);
    expect(result.reactionMs).toBe(0);
    expect(result.score).toBeGreaterThanOrEqual(95);
    expect(result.score).toBeLessThanOrEqual(100);
  });

  it("scores no_pitch (empty samples) as zero with no fabricated hold or reaction", () => {
    const result = scoreToneGameAttempt(440, "A4", []);
    expect(result.grade).toBe("no_pitch");
    expect(result.holdFraction).toBe(0);
    expect(result.reactionMs).toBeNull();
    expect(result.score).toBe(0);
  });

  it("gives partial hold credit when only some samples land in the close band", () => {
    const samples = [
      { hz: 440, atMs: 0 },
      { hz: 440, atMs: 100 },
      { hz: 600, atMs: 200 }, // well outside the close band
      { hz: 600, atMs: 300 },
    ];
    const result = scoreToneGameAttempt(440, "A4", samples);
    expect(result.holdFraction).toBe(0.5);
  });

  it("credits an early reaction more than a late one", () => {
    const early = scoreToneGameAttempt(440, "A4", [
      { hz: 440, atMs: 50 },
      { hz: 440, atMs: 150 },
    ]);
    const late = scoreToneGameAttempt(440, "A4", [
      { hz: 600, atMs: 0 },
      { hz: 440, atMs: 4000 },
    ]);
    expect(early.score).toBeGreaterThan(late.score);
  });

  it("gives zero reaction credit when the close band is never reached", () => {
    const samples = [
      { hz: 600, atMs: 0 },
      { hz: 600, atMs: 100 },
    ];
    const result = scoreToneGameAttempt(440, "A4", samples);
    expect(result.reactionMs).toBeNull();
    expect(result.holdFraction).toBe(0);
  });

  it("never returns a score outside 0-100", () => {
    const samples = [{ hz: 40, atMs: 0 }]; // wildly off target
    const result = scoreToneGameAttempt(440, "A4", samples);
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(100);
  });
});
