import { describe, expect, it } from "vitest";
import { isBlackKey, midiToNoteName, noteNameToMidi } from "./notes";

describe("noteNameToMidi / midiToNoteName round trip", () => {
  it.each(["A4", "C4", "G4", "A3", "A5", "C#4", "B3"])("round-trips %s", (note) => {
    expect(midiToNoteName(noteNameToMidi(note))).toBe(note);
  });

  it("matches known reference: A4 = MIDI 69", () => {
    expect(noteNameToMidi("A4")).toBe(69);
  });

  it("matches known reference: C4 = MIDI 60 (middle C)", () => {
    expect(noteNameToMidi("C4")).toBe(60);
  });

  it("rejects an invalid note name", () => {
    expect(() => noteNameToMidi("not a note")).toThrow();
  });
});

describe("isBlackKey", () => {
  it("is true for sharps", () => {
    expect(isBlackKey(noteNameToMidi("C#4"))).toBe(true);
  });

  it("is false for naturals", () => {
    expect(isBlackKey(noteNameToMidi("C4"))).toBe(false);
  });
});
