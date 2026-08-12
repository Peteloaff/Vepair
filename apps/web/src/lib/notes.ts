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
