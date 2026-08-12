export interface SampleStep {
  type: "sustained_ah" | "sustained_ee" | "sustained_oo" | "hum" | "glide" | "sentence" | "singing";
  title: string;
  instructions: string;
  prompt?: string;
  optional: boolean;
}

// First sentence of the Fairbanks (1960) "Rainbow Passage" — a standard, phonetically
// balanced reading passage used in voice/speech assessment. Public domain.
const RAINBOW_PASSAGE_OPENING =
  "When the sunlight strikes raindrops in the air, they act as a prism and form a rainbow.";

export const RECORDING_SEQUENCE: SampleStep[] = [
  {
    type: "sustained_ah",
    title: 'Sustained "Ah"',
    instructions:
      'Take a comfortable breath, then say "Ah" and hold it steady for as long as feels comfortable.',
    optional: false,
  },
  {
    type: "sustained_ee",
    title: 'Sustained "Ee"',
    instructions:
      'Take a comfortable breath, then say "Ee" and hold it steady for as long as feels comfortable.',
    optional: false,
  },
  {
    type: "sustained_oo",
    title: 'Sustained "Oo"',
    instructions:
      'Take a comfortable breath, then say "Oo" and hold it steady for as long as feels comfortable.',
    optional: false,
  },
  {
    type: "hum",
    title: "Comfortable hum",
    instructions: "Hum gently at a pitch that feels natural and comfortable. No strain.",
    optional: false,
  },
  {
    type: "glide",
    title: "Gentle pitch glide",
    instructions:
      "Gently glide your pitch from low to high, like a soft siren. Keep it easy — don't push for range.",
    optional: false,
  },
  {
    type: "sentence",
    title: "Standardized sentence",
    instructions: "Read the sentence below aloud, at your normal speaking volume and pace.",
    prompt: RAINBOW_PASSAGE_OPENING,
    optional: false,
  },
  {
    type: "singing",
    title: "Singing sample",
    instructions: "Optional: sing a short phrase from a song you know well.",
    optional: true,
  },
];
