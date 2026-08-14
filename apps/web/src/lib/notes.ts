// Mirrors apps/api/app/vocal_range.py's note-name <-> MIDI conversion (A4 = MIDI 69) so the
// piano visualization can lay out notes consistently with what the backend already computed.
// The backend remains the source of truth for which note a recording maps to (Parselmouth's
// F0 -> note-name conversion) — this file only re-derives positions for already-named notes.

const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

export function noteNameToMidi(note: string): number {
  const match = /^([A-G]#?)(-?\d+)$/.exec(note);
  if (!match) throw new Error(`Not a valid note name: ${note}`);
  const [, name, octaveStr] = match;
  const index = NOTE_NAMES.indexOf(name);
  if (index === -1) throw new Error(`Not a valid note name: ${note}`);
  return index + (parseInt(octaveStr, 10) + 1) * 12;
}

export function midiToNoteName(midi: number): string {
  const name = NOTE_NAMES[((midi % 12) + 12) % 12];
  const octave = Math.floor(midi / 12) - 1;
  return `${name}${octave}`;
}

export function isBlackKey(midi: number): boolean {
  return NOTE_NAMES[((midi % 12) + 12) % 12].includes("#");
}

export function isNaturalNote(midi: number): boolean {
  return !isBlackKey(midi);
}

/** Equal-temperament frequency for a MIDI note number (A4 = MIDI 69 = 440Hz). */
export function midiToFrequency(midi: number): number {
  return 440 * Math.pow(2, (midi - 69) / 12);
}

/** Inverse of midiToFrequency, rounded to the nearest note — for labeling an arbitrary
 * measured Hz value (e.g. the Tone Match average-pitch recorder) with the closest note name. */
export function frequencyToMidi(hz: number): number {
  return Math.round(69 + 12 * Math.log2(hz / 440));
}

export interface ReferenceNote {
  label: string;
  midi: number;
  frequencyHz: number;
}

/** A generic reference range spanning octaves 3-4 by default (roughly bass to soprano
 * speaking/singing pitch) — deliberately not personalized to any one user's measured vocal
 * range, since this is a general-purpose "what note is that?" reference, not a claim about
 * what any specific user should be singing. */
export function buildReferenceRange(startOctave = 3, octaveCount = 2): ReferenceNote[] {
  const notes: ReferenceNote[] = [];
  const startMidi = noteNameToMidi(`C${startOctave}`);
  for (let midi = startMidi; midi < startMidi + octaveCount * 12; midi++) {
    notes.push({ label: midiToNoteName(midi), midi, frequencyHz: midiToFrequency(midi) });
  }
  return notes;
}

/** Plays a short pure tone via the Web Audio API with a brief fade in/out to avoid clicks. */
export function playTone(frequencyHz: number, durationMs = 2000): Promise<void> {
  const AudioContextCtor =
    window.AudioContext ||
    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const ctx = new AudioContextCtor();
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = frequencyHz;
  oscillator.connect(gain);
  gain.connect(ctx.destination);

  const now = ctx.currentTime;
  const fadeSeconds = 0.03;
  const durationSeconds = durationMs / 1000;
  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(0.2, now + fadeSeconds);
  gain.gain.setValueAtTime(0.2, now + Math.max(fadeSeconds, durationSeconds - fadeSeconds));
  gain.gain.linearRampToValueAtTime(0, now + durationSeconds);

  oscillator.start(now);
  oscillator.stop(now + durationSeconds);

  return new Promise((resolve) => {
    oscillator.onended = () => {
      ctx.close();
      resolve();
    };
  });
}
