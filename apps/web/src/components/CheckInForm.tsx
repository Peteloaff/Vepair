"use client";

import { useState } from "react";
import type { CheckIn, CheckInInput } from "@/lib/types";

type FormValues = Omit<CheckInInput, "checkin_date">;

const EMPTY: FormValues = {
  voice_quality: undefined,
  fatigue: undefined,
  throat_discomfort: undefined,
  speaking_load: undefined,
  singing_load: undefined,
  rehearsal_or_performance_yesterday: undefined,
  sleep_hours: undefined,
  hydration_estimate: undefined,
  alcohol_exposure: undefined,
  smoke_vape_exposure: undefined,
  illness_symptoms: undefined,
  reflux_symptoms: undefined,
  notes: undefined,
};

function fromCheckIn(c: CheckIn | null): FormValues {
  if (!c) return EMPTY;
  return {
    voice_quality: c.voice_quality ?? undefined,
    fatigue: c.fatigue ?? undefined,
    throat_discomfort: c.throat_discomfort ?? undefined,
    speaking_load: c.speaking_load ?? undefined,
    singing_load: c.singing_load ?? undefined,
    rehearsal_or_performance_yesterday: c.rehearsal_or_performance_yesterday ?? undefined,
    sleep_hours: c.sleep_hours ?? undefined,
    hydration_estimate: c.hydration_estimate ?? undefined,
    alcohol_exposure: c.alcohol_exposure ?? undefined,
    smoke_vape_exposure: c.smoke_vape_exposure ?? undefined,
    illness_symptoms: c.illness_symptoms ?? undefined,
    reflux_symptoms: c.reflux_symptoms ?? undefined,
    notes: c.notes ?? undefined,
  };
}

function ScaleInput({
  label,
  min,
  max,
  value,
  onChange,
}: {
  label: string;
  min: number;
  max: number;
  value: number | null | undefined;
  onChange: (v: number | undefined) => void;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <label className="text-xs text-text-dim">{label}</label>
        <span className="text-xs text-text-dim">{value ?? "Skipped"}</span>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="range"
          min={min}
          max={max}
          value={value ?? min - 1}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full accent-accent"
        />
        {value !== undefined && value !== null && (
          <button
            type="button"
            onClick={() => onChange(undefined)}
            className="shrink-0 text-xs text-text-faint hover:text-text-dim"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

function LoadSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string | null | undefined;
  onChange: (v: string | undefined) => void;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs text-text-dim">{label}</label>
      <select
        value={value ?? ""}
        aria-label={label}
        onChange={(e) => onChange(e.target.value || undefined)}
        className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
      >
        <option value="">Skip</option>
        <option value="none">None</option>
        <option value="low">Low</option>
        <option value="moderate">Moderate</option>
        <option value="high">High</option>
      </select>
    </div>
  );
}

export function CheckInForm({
  initial = null,
  onSubmit,
  submitLabel = "Save today's check-in",
}: {
  initial?: CheckIn | null;
  onSubmit: (values: FormValues) => Promise<void>;
  submitLabel?: string;
}) {
  const [values, setValues] = useState<FormValues>(fromCheckIn(initial));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((v) => ({ ...v, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(values);
    } catch {
      setError("Could not save your check-in. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <ScaleInput
        label="Perceived voice quality (1-10)"
        min={1}
        max={10}
        value={values.voice_quality}
        onChange={(v) => set("voice_quality", v)}
      />
      <ScaleInput
        label="Fatigue (1-10)"
        min={1}
        max={10}
        value={values.fatigue}
        onChange={(v) => set("fatigue", v)}
      />
      <ScaleInput
        label="Throat discomfort (0-10)"
        min={0}
        max={10}
        value={values.throat_discomfort}
        onChange={(v) => set("throat_discomfort", v)}
      />

      <div className="grid grid-cols-2 gap-3">
        <LoadSelect
          label="Speaking load yesterday"
          value={values.speaking_load}
          onChange={(v) => set("speaking_load", v)}
        />
        <LoadSelect
          label="Singing load yesterday"
          value={values.singing_load}
          onChange={(v) => set("singing_load", v)}
        />
      </div>

      <div>
        <span className="mb-1 block text-xs text-text-dim">
          Rehearsal or performance yesterday?
        </span>
        <div className="flex gap-2">
          {(
            [
              ["Yes", true],
              ["No", false],
              ["Skip", undefined],
            ] as const
          ).map(([text, val]) => (
            <button
              key={text}
              type="button"
              onClick={() => set("rehearsal_or_performance_yesterday", val)}
              className={`rounded-lg border px-3 py-1.5 text-xs ${
                values.rehearsal_or_performance_yesterday === val
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-border-strong text-text-dim hover:bg-surface-2"
              }`}
            >
              {text}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs text-text-dim">Sleep last night (hours)</label>
        <input
          type="number"
          min={0}
          max={24}
          step={0.5}
          value={values.sleep_hours ?? ""}
          onChange={(e) =>
            set("sleep_hours", e.target.value === "" ? undefined : Number(e.target.value))
          }
          className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <LoadSelect
          label="Hydration"
          value={values.hydration_estimate}
          onChange={(v) => set("hydration_estimate", v)}
        />
        <LoadSelect
          label="Alcohol exposure"
          value={values.alcohol_exposure}
          onChange={(v) => set("alcohol_exposure", v)}
        />
        <LoadSelect
          label="Smoke/vape exposure"
          value={values.smoke_vape_exposure}
          onChange={(v) => set("smoke_vape_exposure", v)}
        />
      </div>

      <div>
        <label className="mb-1 block text-xs text-text-dim">
          Illness symptoms (optional)
        </label>
        <textarea
          value={values.illness_symptoms ?? ""}
          onChange={(e) => set("illness_symptoms", e.target.value || undefined)}
          rows={2}
          className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs text-text-dim">
          Reflux symptoms (optional)
        </label>
        <textarea
          value={values.reflux_symptoms ?? ""}
          onChange={(e) => set("reflux_symptoms", e.target.value || undefined)}
          rows={2}
          className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
        />
      </div>

      <div>
        <label className="mb-1 block text-xs text-text-dim">Notes</label>
        <textarea
          value={values.notes ?? ""}
          onChange={(e) => set("notes", e.target.value || undefined)}
          rows={2}
          className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
        />
      </div>

      {error && (
        <p className="rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong disabled:opacity-50"
      >
        {submitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
