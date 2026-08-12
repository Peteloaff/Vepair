import { describe, expect, it } from "vitest";
import { gradeToneMatch } from "./pitchGrading";

describe("gradeToneMatch", () => {
  it("grades an exact match as spot_on", () => {
    const result = gradeToneMatch(440, "A4", [440, 440, 440]);
    expect(result.grade).toBe("spot_on");
    expect(result.semitonesOff).toBeCloseTo(0, 5);
    expect(result.detectedLabel).toBe("A4");
  });

  it("grades a slightly sharp attempt as spot_on within tolerance", () => {
    // ~10 cents sharp of A4 — well inside the 0.25-semitone spot-on band
    const result = gradeToneMatch(440, "A4", [442.5]);
    expect(result.grade).toBe("spot_on");
    expect(result.semitonesOff).toBeGreaterThan(0);
  });

  it("grades a half-semitone-ish deviation as close, not spot_on", () => {
    // A4 (440) vs A#4 (~466.16) is a full semitone away, but 0.4 semitones off should land
    // in "close" (<=0.5 semitones), not "spot_on" (<=0.25) or "off" (>0.5)
    const target = 440;
    const detectedHz = target * Math.pow(2, 0.4 / 12);
    const result = gradeToneMatch(target, "A4", [detectedHz]);
    expect(result.grade).toBe("close");
  });

  it("grades a full semitone off as off pitch", () => {
    const target = 440;
    const detectedHz = target * Math.pow(2, 1 / 12); // A#4
    const result = gradeToneMatch(target, "A4", [detectedHz]);
    expect(result.grade).toBe("off");
  });

  it("flags flat attempts with a negative semitonesOff", () => {
    const target = 440;
    const detectedHz = target * Math.pow(2, -0.4 / 12);
    const result = gradeToneMatch(target, "A4", [detectedHz]);
    expect(result.semitonesOff).toBeLessThan(0);
  });

  it("returns no_pitch when nothing was detected, never a fabricated score", () => {
    const result = gradeToneMatch(440, "A4", []);
    expect(result.grade).toBe("no_pitch");
    expect(result.detectedHz).toBeNull();
    expect(result.detectedLabel).toBeNull();
    expect(result.semitonesOff).toBeNull();
  });

  it("uses the median of detected samples, resistant to a single outlier spike", () => {
    // Nine clean 440Hz samples plus one wild 880Hz spike (e.g. a stray octave-detection error)
    const samples = [440, 440, 440, 440, 440, 440, 440, 440, 440, 880];
    const result = gradeToneMatch(440, "A4", samples);
    expect(result.grade).toBe("spot_on");
  });
});
