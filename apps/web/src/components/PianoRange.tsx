import { isNaturalNote, midiToNoteName, noteNameToMidi } from "@/lib/notes";

const LOW_MIDI = noteNameToMidi("C2");
const HIGH_MIDI = noteNameToMidi("C6");

interface PianoRangeProps {
  currentLowNote: string | null;
  currentHighNote: string | null;
  historicalBestLowNote: string | null;
  historicalBestHighNote: string | null;
  stretchTargetNote: string | null;
}

export function PianoRange({
  currentLowNote,
  currentHighNote,
  historicalBestLowNote,
  historicalBestHighNote,
  stretchTargetNote,
}: PianoRangeProps) {
  const naturalKeys: number[] = [];
  for (let m = LOW_MIDI; m <= HIGH_MIDI; m++) {
    if (isNaturalNote(m)) naturalKeys.push(m);
  }
  const keyWidth = 100 / naturalKeys.length;

  const currentLowMidi = currentLowNote ? noteNameToMidi(currentLowNote) : null;
  const currentHighMidi = currentHighNote ? noteNameToMidi(currentHighNote) : null;

  function xForMidi(midi: number): number {
    // Position within the natural-key strip, snapping sharps to their nearest natural.
    let nearestIndex = 0;
    let nearestDistance = Infinity;
    naturalKeys.forEach((k, i) => {
      const distance = Math.abs(k - midi);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestIndex = i;
      }
    });
    return nearestIndex * keyWidth;
  }

  const highlightStart =
    currentLowMidi !== null ? xForMidi(currentLowMidi) : null;
  const highlightEnd = currentHighMidi !== null ? xForMidi(currentHighMidi) + keyWidth : null;

  return (
    <div>
      <div className="relative h-16 w-full overflow-hidden rounded-lg border border-neutral-800">
        {highlightStart !== null && highlightEnd !== null && (
          <div
            className="absolute top-0 h-full bg-emerald-500/20"
            style={{ left: `${highlightStart}%`, width: `${highlightEnd - highlightStart}%` }}
          />
        )}
        <div className="flex h-full">
          {naturalKeys.map((midi) => (
            <div
              key={midi}
              className="flex-1 border-r border-neutral-800 last:border-r-0"
              title={midiToNoteName(midi)}
            />
          ))}
        </div>
        {historicalBestHighNote && currentHighMidi !== noteNameToMidi(historicalBestHighNote) && (
          <div
            className="absolute top-0 h-full w-0.5 bg-amber-400"
            style={{ left: `${xForMidi(noteNameToMidi(historicalBestHighNote))}%` }}
            title={`Historical best: ${historicalBestHighNote}`}
          />
        )}
        {stretchTargetNote && (
          <div
            className="absolute top-0 h-full w-0.5 border-l-2 border-dashed border-emerald-400"
            style={{ left: `${xForMidi(noteNameToMidi(stretchTargetNote))}%` }}
            title={`Optional stretch target: ${stretchTargetNote}`}
          />
        )}
      </div>
      <div className="mt-1 flex justify-between text-xs text-neutral-600">
        <span>{midiToNoteName(LOW_MIDI)}</span>
        <span>{midiToNoteName(HIGH_MIDI)}</span>
      </div>
      {historicalBestLowNote && (
        <p className="mt-2 text-xs text-neutral-500">
          <span className="inline-block h-2 w-2 rounded-full bg-amber-400 align-middle" />{" "}
          Historical best marker shown when different from your current range.
        </p>
      )}
    </div>
  );
}
