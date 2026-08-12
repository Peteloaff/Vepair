"use client";

import { useState } from "react";
import { buildReferenceRange, playTone } from "@/lib/notes";

const NOTES = buildReferenceRange();

export function ReferenceTonePlayer() {
  const [open, setOpen] = useState(false);
  const [playing, setPlaying] = useState<string | null>(null);

  async function handlePlay(label: string, frequencyHz: number) {
    if (playing) return;
    setPlaying(label);
    try {
      await playTone(frequencyHz, 2000);
    } finally {
      setPlaying(null);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mb-4 text-xs text-emerald-400 hover:text-emerald-300"
      >
        Need a starting note? Tap one to hear it &rarr;
      </button>
    );
  }

  return (
    <div className="mb-4 rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs text-neutral-400">Tap a note to hear it (2s)</p>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          Hide
        </button>
      </div>
      <div className="grid grid-cols-6 gap-1.5">
        {NOTES.map(({ label, frequencyHz }) => (
          <button
            key={label}
            type="button"
            disabled={playing !== null}
            onClick={() => handlePlay(label, frequencyHz)}
            className={`rounded-md border px-2 py-1.5 text-xs font-medium disabled:opacity-40 ${
              playing === label
                ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                : "border-neutral-700 text-neutral-300 hover:bg-neutral-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
