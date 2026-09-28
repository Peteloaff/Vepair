"use client";

import { useEffect, useState } from "react";
import { NotePicker } from "@/components/NotePicker";
import { useAuth } from "@/lib/auth-context";
import type { VocalGoal } from "@/lib/types";

export function GoalTonesEditor() {
  const { apiFetch } = useAuth();
  const [goal, setGoal] = useState<VocalGoal | null>(null);
  const [low, setLow] = useState<string | null>(null);
  const [avg, setAvg] = useState<string | null>(null);
  const [high, setHigh] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function applyGoal(g: VocalGoal) {
    setGoal(g);
    setLow(g.target_low_note);
    setAvg(g.target_avg_note);
    setHigh(g.target_high_note);
  }

  useEffect(() => {
    apiFetch<VocalGoal>("/api/v1/vocal-goals").then(applyGoal).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const updated = await apiFetch<VocalGoal>("/api/v1/vocal-goals", {
        method: "PUT",
        body: { target_low_note: low, target_avg_note: avg, target_high_note: high },
      });
      applyGoal(updated);
    } catch {
      setError("Could not save your target tones. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function resetToAi() {
    setSaving(true);
    setError(null);
    try {
      await apiFetch("/api/v1/vocal-goals", { method: "DELETE" });
      const updated = await apiFetch<VocalGoal>("/api/v1/vocal-goals");
      applyGoal(updated);
    } catch {
      setError("Could not reset to the AI suggestion. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (goal === null) {
    return <p className="text-sm text-text-faint">Loading your target tones...</p>;
  }

  return (
    <div className="rounded-2xl border border-border bg-surface/60 p-5">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-sm font-medium text-text">Your target tones</h2>
        <span
          className={`rounded-full px-2 py-0.5 text-xs ${
            goal.source === "manual"
              ? "bg-accent/10 text-accent"
              : "bg-surface-2 text-text-dim"
          }`}
        >
          {goal.source === "manual" ? "Your target" : "AI-suggested"}
        </span>
      </div>
      <p className="mb-4 text-xs text-text-faint">
        Set the low, average, and high notes you&apos;re working toward. The AI suggests these
        from your own measured vocal range until you set your own — your daily exercises and
        home page adapt to whichever is active.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <NotePicker id="goal-low" label="Low" value={low} onChange={setLow} disabled={saving} />
        <NotePicker id="goal-avg" label="Average" value={avg} onChange={setAvg} disabled={saving} />
        <NotePicker
          id="goal-high"
          label="High"
          value={high}
          onChange={setHigh}
          disabled={saving}
        />
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
      )}

      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save my targets"}
        </button>
        <button
          type="button"
          onClick={resetToAi}
          disabled={saving || goal.source === "ai"}
          className="rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2 disabled:opacity-50"
        >
          Reset to AI suggestion
        </button>
      </div>
    </div>
  );
}
