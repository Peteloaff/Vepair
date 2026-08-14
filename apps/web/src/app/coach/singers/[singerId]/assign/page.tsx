"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ExerciseInfoButton } from "@/components/ExerciseInfoButton";
import { NotePicker } from "@/components/NotePicker";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { useAuth } from "@/lib/auth-context";
import type { CoachAssignment, Exercise } from "@/lib/types";

// Must match app/exercise_library.py's CATEGORY_INTENSITY keys exactly -- the adaptive routine
// generator's safety gate is keyed on this fixed set, so a custom exercise has to land in one
// of these, not a free-typed category.
const EXERCISE_CATEGORIES = [
  "Breathing",
  "Vocal cooldown",
  "SOVT",
  "Straw phonation",
  "Gentle humming",
  "Resonant voice exercises",
  "Lip trill",
  "Tongue trill",
  "Speaking voice recovery",
  "Gentle sirens",
  "Pitch glides",
  "Range exploration",
] as const;

function AssignContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ singerId: string }>();
  const [exercises, setExercises] = useState<Exercise[] | null>(null);
  const [history, setHistory] = useState<CoachAssignment[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [toneTargets, setToneTargets] = useState<Record<string, string | null>>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newInstructions, setNewInstructions] = useState("");
  const [newCategory, setNewCategory] = useState<string>(EXERCISE_CATEGORIES[0]);
  const [newDuration, setNewDuration] = useState(60);
  const [newDifficulty, setNewDifficulty] = useState<"easy" | "moderate" | "hard">("easy");
  const [addError, setAddError] = useState<string | null>(null);
  const [addSubmitting, setAddSubmitting] = useState(false);

  async function load() {
    try {
      const [exercisesData, historyData] = await Promise.all([
        apiFetch<Exercise[]>("/api/v1/exercises"),
        apiFetch<CoachAssignment[]>(`/api/v1/coach/singers/${params.singerId}/assignments`),
      ]);
      setExercises(exercisesData);
      setHistory(historyData);
    } catch {
      setError("Could not load exercises for this singer.");
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.singerId]);

  function toggle(exerciseId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(exerciseId)) {
        next.delete(exerciseId);
      } else {
        next.add(exerciseId);
      }
      return next;
    });
  }

  async function submit() {
    if (selected.size === 0) {
      setError("Select at least one exercise.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const targets: Record<string, string> = {};
      for (const id of selected) {
        const targetNote = toneTargets[id];
        if (targetNote) targets[id] = targetNote;
      }
      await apiFetch(`/api/v1/coach/singers/${params.singerId}/assignments`, {
        method: "POST",
        body: {
          exercise_ids: Array.from(selected),
          note_to_singer: note || null,
          exercise_tone_targets: Object.keys(targets).length > 0 ? targets : null,
        },
      });
      setSelected(new Set());
      setToneTargets({});
      setNote("");
      await load();
    } catch {
      setError("Could not save this assignment. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitNewExercise() {
    if (!newName.trim() || !newInstructions.trim()) {
      setAddError("Title and description are both required.");
      return;
    }
    setAddSubmitting(true);
    setAddError(null);
    try {
      const created = await apiFetch<Exercise>("/api/v1/coach/exercises", {
        method: "POST",
        body: {
          name: newName,
          instructions: newInstructions,
          category: newCategory,
          duration_seconds: newDuration,
          difficulty: newDifficulty,
        },
      });
      setNewName("");
      setNewInstructions("");
      setNewDuration(60);
      setShowAddForm(false);
      await load();
      // Pre-select it so the coach doesn't have to hunt for the exercise they just typed in.
      setSelected((prev) => new Set(prev).add(created.id));
    } catch {
      setAddError("Could not save this exercise. Please try again.");
    } finally {
      setAddSubmitting(false);
    }
  }

  if (error && exercises === null) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (exercises === null || history === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  const active = history.find((a) => a.status === "active");

  return (
    <div className="mx-auto w-full max-w-2xl">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Assign training</h1>
      <p className="mb-6 text-sm text-neutral-400">
        Assigned exercises are included in the singer&apos;s daily routine only where today&apos;s
        own safety limits already allow — an assignment can never push past what would be safe
        for them today.
      </p>

      {active && (
        <div className="mb-6 rounded-xl border border-emerald-800 bg-emerald-950/20 p-4">
          <p className="text-xs text-emerald-300">Currently assigned</p>
          <ul className="mt-1 text-sm text-neutral-300">
            {active.exercise_ids.map((id) => {
              const target = active.exercise_tone_targets?.[id];
              return (
                <li key={id}>
                  {exercises.find((e) => e.id === id)?.name ?? id}
                  {target && <span className="text-xs text-neutral-500"> &middot; target: {target}</span>}
                </li>
              );
            })}
          </ul>
          {active.note_to_singer && (
            <p className="mt-2 text-xs text-neutral-500">
              &ldquo;{active.note_to_singer}&rdquo;
            </p>
          )}
        </div>
      )}

      <div className="mb-4">
        {!showAddForm ? (
          <button
            type="button"
            onClick={() => setShowAddForm(true)}
            className="text-xs text-emerald-400 hover:text-emerald-300"
          >
            + Add custom exercise
          </button>
        ) : (
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
            <p className="mb-2 text-xs text-neutral-400">
              Adds a new exercise to the library — selectable below once saved.
            </p>
            <input
              type="text"
              placeholder="Title"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="mb-2 w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            <textarea
              placeholder="Description — how to do this exercise"
              value={newInstructions}
              onChange={(e) => setNewInstructions(e.target.value)}
              rows={3}
              className="mb-2 w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            <div className="mb-2 grid grid-cols-3 gap-2">
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-2 text-sm outline-none focus:border-neutral-500"
              >
                {EXERCISE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <select
                value={newDifficulty}
                onChange={(e) =>
                  setNewDifficulty(e.target.value as "easy" | "moderate" | "hard")
                }
                className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-2 text-sm outline-none focus:border-neutral-500"
              >
                <option value="easy">Easy</option>
                <option value="moderate">Moderate</option>
                <option value="hard">Hard</option>
              </select>
              <input
                type="number"
                min={5}
                max={1800}
                value={newDuration}
                onChange={(e) => setNewDuration(Number(e.target.value))}
                className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-2 text-sm outline-none focus:border-neutral-500"
                aria-label="Duration in seconds"
              />
            </div>
            {addError && (
              <p className="mb-2 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">
                {addError}
              </p>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={submitNewExercise}
                disabled={addSubmitting}
                className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
              >
                {addSubmitting ? "Saving..." : "Save exercise"}
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                disabled={addSubmitting}
                className="rounded-lg border border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-800 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="mb-4 space-y-1.5">
        {exercises.map((exercise) => (
          <div
            key={exercise.id}
            className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-2"
          >
            <label className="flex items-center gap-2 text-sm text-neutral-300">
              <input
                type="checkbox"
                checked={selected.has(exercise.id)}
                onChange={() => toggle(exercise.id)}
                className="h-4 w-4 rounded border-neutral-700 bg-neutral-900"
              />
              <span className="inline-flex items-center gap-1">
                {exercise.name}
                <ExerciseInfoButton
                  purpose={exercise.purpose}
                  instructions={exercise.instructions}
                  contraindications={exercise.contraindications}
                />
                <span className="text-xs text-neutral-500">
                  &middot; {exercise.category} &middot; {exercise.difficulty}
                </span>
              </span>
            </label>
            {selected.has(exercise.id) && (
              <div className="mt-2 max-w-[160px] pl-6">
                <NotePicker
                  id={`tone-target-${exercise.id}`}
                  label="Target tone for this exercise (optional)"
                  value={toneTargets[exercise.id] ?? null}
                  onChange={(note) =>
                    setToneTargets((prev) => ({ ...prev, [exercise.id]: note }))
                  }
                />
              </div>
            )}
          </div>
        ))}
      </div>

      <textarea
        placeholder="Note to singer (optional)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
        className="mb-3 w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
      />

      {error && (
        <p className="mb-3 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={submit}
          disabled={submitting}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Assign"}
        </button>
        <Link
          href={`/coach/singers/${params.singerId}`}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
        >
          Back
        </Link>
      </div>
    </div>
  );
}

export default function CoachAssignPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-6 py-10">
          <AssignContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
