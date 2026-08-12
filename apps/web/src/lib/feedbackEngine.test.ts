import { describe, expect, it } from "vitest";
import {
  coachingProfileForCategory,
  createFeedbackEngineState,
  processSample,
  type FeedbackContext,
  type FeedbackEngineState,
  type FeedbackMessage,
  type FeedbackSample,
} from "./feedbackEngine";

const FRAME_INTERVAL_MS = 90; // matches AudioRecorder's ScriptProcessor chunk cadence

function runSequence(
  samples: FeedbackSample[],
  context: FeedbackContext
): { messages: FeedbackMessage[]; finalState: FeedbackEngineState } {
  let state = createFeedbackEngineState();
  const messages: FeedbackMessage[] = [];
  for (const sample of samples) {
    const result = processSample(state, sample, context);
    state = result.state;
    if (result.message) messages.push(result.message);
  }
  return { messages, finalState: state };
}

/** Builds a sample stream at a fixed frame interval. `pitchAt` returns the pitch for a given
 * elapsed-ms (or null for silence); `rmsAt` likewise for volume. */
function buildStream(
  durationMs: number,
  pitchAt: (elapsedMs: number) => number | null,
  rmsAt: (elapsedMs: number) => number = () => 0.08
): FeedbackSample[] {
  const samples: FeedbackSample[] = [];
  for (let t = 0; t <= durationMs; t += FRAME_INTERVAL_MS) {
    samples.push({ timestampMs: t, pitchHz: pitchAt(t), rms: rmsAt(t) });
  }
  return samples;
}

const sustainedContext: FeedbackContext = {
  profile: "sustained",
  comfortableMinHz: null,
  comfortableMaxHz: null,
  minIntervalMs: 4000,
};

const glideContext: FeedbackContext = {
  profile: "glide",
  comfortableMinHz: 150,
  comfortableMaxHz: 350,
  minIntervalMs: 4000,
};

describe("processSample — clean signal (false feedback frequency)", () => {
  it("a gentle, steady tone never produces corrective feedback", () => {
    // Gradual ramp-in over the first 300ms (avoids the harsh-onset rule), then a rock-steady
    // 220Hz tone for several seconds.
    const samples = buildStream(
      4000,
      (t) => (t < 90 ? null : 220),
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages.every((m) => m.tone !== "corrective")).toBe(true);
  });

  it("eventually gives positive reinforcement for a steady tone", () => {
    const samples = buildStream(
      4000,
      (t) => (t < 90 ? null : 220),
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages.some((m) => m.rule === "steady" && m.tone === "positive")).toBe(true);
  });

  it("silence alone never produces any feedback", () => {
    const samples = buildStream(3000, () => null);
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages).toHaveLength(0);
  });

  it("a 'none' profile (e.g. Breathing) never produces feedback regardless of signal", () => {
    const samples = buildStream(3000, () => 220, () => 0.5);
    const { messages } = runSequence(samples, { ...sustainedContext, profile: "none" });
    expect(messages).toHaveLength(0);
  });
});

describe("processSample — onset", () => {
  it("flags an immediately-loud first voiced frame as a harsh onset", () => {
    const samples = buildStream(1000, (t) => (t < 90 ? null : 220), () => 0.4);
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages[0]?.rule).toBe("onset");
  });

  it("does not flag a gradually-building onset", () => {
    const samples = buildStream(
      1000,
      (t) => (t < 90 ? null : 220),
      (t) => 0.02 + (t / 1000) * 0.06
    );
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages.some((m) => m.rule === "onset")).toBe(false);
  });

  it("only checks onset once per attempt, even if a later frame would also qualify", () => {
    // Gentle onset, but a loud frame shows up later -- that's the volume-spike rule's job, not
    // a second onset check.
    const samples = buildStream(
      2000,
      (t) => (t < 90 ? null : 220),
      (t) => (t < 300 ? 0.02 : t > 1000 && t < 1200 ? 0.4 : 0.08)
    );
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages.filter((m) => m.rule === "onset")).toHaveLength(0);
  });
});

describe("processSample — volume spike", () => {
  it("flags a sudden loud frame against an established quiet baseline", () => {
    const samples = buildStream(
      2000,
      (t) => (t < 90 ? null : 220),
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : t >= 1000 && t < 1100 ? 0.4 : 0.08)
    );
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages.some((m) => m.rule === "volume-spike")).toBe(true);
  });
});

describe("processSample — pitch drift", () => {
  it("flags pitch rising more than the threshold across a sustained attempt", () => {
    const samples = buildStream(
      2600,
      (t) => (t < 90 ? null : t < 1300 ? 220 : 235),
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages.some((m) => m.rule === "pitch-drift")).toBe(true);
  });

  it("does not flag a small, within-tolerance pitch wobble", () => {
    const samples = buildStream(
      2600,
      (t) => (t < 90 ? null : 220 + Math.sin(t / 200) * 1.5),
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const { messages } = runSequence(samples, sustainedContext);
    expect(messages.some((m) => m.rule === "pitch-drift")).toBe(false);
  });

  it("drift is only checked for the sustained profile, not glide", () => {
    const samples = buildStream(
      2600,
      (t) => (t < 90 ? null : t < 1300 ? 200 : 220), // stays within the comfortable range
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const { messages } = runSequence(samples, glideContext);
    expect(messages.some((m) => m.rule === "pitch-drift")).toBe(false);
  });
});

describe("processSample — comfortable range (glide profile)", () => {
  it("flags pitch that climbs past the personal-baseline maximum", () => {
    const samples = buildStream(
      2000,
      (t) => (t < 90 ? null : 200 + (t / 2000) * 250), // glides from 200Hz up to 450Hz
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const { messages } = runSequence(samples, glideContext);
    expect(messages.some((m) => m.rule === "range-high")).toBe(true);
  });

  it("flags pitch that dips below the personal-baseline minimum", () => {
    const samples = buildStream(
      2000,
      (t) => (t < 90 ? null : 250 - (t / 2000) * 150), // glides from 250Hz down to 100Hz
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const { messages } = runSequence(samples, glideContext);
    expect(messages.some((m) => m.rule === "range-low")).toBe(true);
  });

  it("never fires a range warning when no personal baseline exists yet", () => {
    const samples = buildStream(
      2000,
      (t) => (t < 90 ? null : 200 + (t / 2000) * 250),
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const noBaselineContext: FeedbackContext = {
      ...glideContext,
      comfortableMinHz: null,
      comfortableMaxHz: null,
    };
    const { messages } = runSequence(samples, noBaselineContext);
    expect(messages.some((m) => m.rule === "range-high" || m.rule === "range-low")).toBe(false);
  });

  it("staying inside the comfortable range never fires a range warning", () => {
    const samples = buildStream(
      2000,
      (t) => (t < 90 ? null : 200 + Math.sin(t / 300) * 20), // wobbles between 180-220Hz
      (t) => (t < 300 ? 0.02 + (t / 300) * 0.06 : 0.08)
    );
    const { messages } = runSequence(samples, glideContext);
    expect(messages.some((m) => m.rule === "range-high" || m.rule === "range-low")).toBe(false);
  });
});

describe("processSample — feedback frequency / cooldown", () => {
  it("never emits two messages closer together than minIntervalMs", () => {
    // Two volume spikes close together; only the first should produce a message.
    const samples = buildStream(
      2000,
      (t) => (t < 90 ? null : 220),
      (t) =>
        t < 300
          ? 0.02 + (t / 300) * 0.06
          : (t >= 500 && t < 600) || (t >= 900 && t < 1000)
            ? 0.4
            : 0.08
    );
    const { messages } = runSequence(samples, { ...sustainedContext, minIntervalMs: 4000 });
    expect(messages.filter((m) => m.rule === "volume-spike")).toHaveLength(1);
  });

  it("allows a new message once minIntervalMs has elapsed", () => {
    const samples = buildStream(
      3000,
      (t) => (t < 90 ? null : 220),
      (t) =>
        t < 300
          ? 0.02 + (t / 300) * 0.06
          : (t >= 500 && t < 600) || (t >= 2600 && t < 2700)
            ? 0.4
            : 0.08
    );
    const { messages } = runSequence(samples, { ...sustainedContext, minIntervalMs: 2000 });
    expect(messages.filter((m) => m.rule === "volume-spike")).toHaveLength(2);
  });

  it("a shorter configured interval allows feedback to repeat sooner", () => {
    const buildSamples = () =>
      buildStream(
        3000,
        (t) => (t < 90 ? null : 220),
        (t) =>
          t < 300
            ? 0.02 + (t / 300) * 0.06
            : (t >= 500 && t < 600) || (t >= 1600 && t < 1700)
              ? 0.4
              : 0.08
      );
    const frequent = runSequence(buildSamples(), { ...sustainedContext, minIntervalMs: 1000 });
    const minimal = runSequence(buildSamples(), { ...sustainedContext, minIntervalMs: 8000 });
    expect(frequent.messages.filter((m) => m.rule === "volume-spike")).toHaveLength(2);
    expect(minimal.messages.filter((m) => m.rule === "volume-spike")).toHaveLength(1);
  });
});

describe("coachingProfileForCategory", () => {
  it("gives Breathing no live coaching (no vocal signal to analyze)", () => {
    expect(coachingProfileForCategory("Breathing")).toBe("none");
  });

  it.each(["Pitch glides", "Gentle sirens", "Range exploration"])(
    "treats %s as the glide profile",
    (category) => {
      expect(coachingProfileForCategory(category)).toBe("glide");
    }
  );

  it.each([
    "Gentle humming",
    "Lip trill",
    "Tongue trill",
    "Resonant voice exercises",
    "SOVT",
    "Straw phonation",
    "Vocal cooldown",
    "Speaking voice recovery",
  ])("treats %s as the sustained profile", (category) => {
    expect(coachingProfileForCategory(category)).toBe("sustained");
  });
});
