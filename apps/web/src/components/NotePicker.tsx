"use client";

import { buildReferenceRange } from "@/lib/notes";

const NOTES = buildReferenceRange(2, 4); // C2-C6, wide enough to cover any comfortable target

interface NotePickerProps {
  id: string;
  label: string;
  value: string | null;
  onChange: (note: string | null) => void;
  disabled?: boolean;
}

export function NotePicker({ id, label, value, onChange, disabled }: NotePickerProps) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs text-neutral-400">
        {label}
      </label>
      <select
        id={id}
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
        className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500 disabled:opacity-50"
      >
        <option value="">Not set</option>
        {NOTES.map((note) => (
          <option key={note.label} value={note.label}>
            {note.label}
          </option>
        ))}
      </select>
    </div>
  );
}
