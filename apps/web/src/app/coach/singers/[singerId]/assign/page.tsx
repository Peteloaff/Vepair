"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ExerciseInfoButton } from "@/components/ExerciseInfoButton";
import { NotePicker } from "@/components/NotePicker";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { useAuth } from "@/lib/auth-context";
import type { AssignmentTemplate, CoachAssignment, Exercise } from "@/lib/types";

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
  const [templates, setTemplates] = useState<AssignmentTemplate[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [toneTargets, setToneTargets] = useState<Record<string, string | null>>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showSaveTemplateForm, setShowSaveTemplateForm] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [newName, setNewName] = useState("");
  const [newInstructions, setNewInstructions] = useState("");
  const [newCategory, setNewCategory] = useState<string>(EXERCISE_CATEGORIES[0]);
  const [newDuration, setNewDuration] = useState(60);
  const [newDifficulty, setNewDifficulty] = useState<"easy" | "moderate" | "hard">("easy");
  const [addError, setAddError] = useState<string | null>(null);
  const [addSubmitting, setAddSubmitting] = useState(false);
  // Exercises created in this sitting -- lets a coach add several in a row and see what
  // they've queued up so far, without the form closing (and losing category/difficulty/
  // duration) after every single one.
  const [addedThisSession, setAddedThisSession] = useState<Exercise[]>([]);

  async function load() {
    try {
      const [exercisesData, historyData, templatesData] = await Promise.all([
        apiFetch<Exercise[]>("/api/v1/exercises"),
        apiFetch<CoachAssignment[]>(`/api/v1/coach/singers/${params.singerId}/assignments`),
        apiFetch<AssignmentTemplate[]>("/api/v1/coach/assignment-templates"),
      ]);
      setExercises(exercisesData);
      setHistory(historyData);
      setTemplates(templatesData);
    } catch {
      setError("Could not load exercises for this Vrotégé.");
    }
  }

  function applyTemplate(template: AssignmentTemplate) {
    setSelected(new Set(template.exercise_ids));
    setToneTargets(template.exercise_tone_targets ?? {});
    setNote(template.note_to_singer ?? "");
  }

  async function saveTemplate() {
    if (!templateName.trim()) {
      setTemplateError("Give this template a name.");
      return;
    }
    setSavingTemplate(true);
    setTemplateError(null);
    try {
      const targets: Record<string, string> = {};
      for (const id of selected) {
        const targetNote = toneTargets[id];
        if (targetNote) targets[id] = targetNote;
      }
      const created = await apiFetch<AssignmentTemplate>("/api/v1/coach/assignment-templates", {
        method: "POST",
        body: {
          name: templateName,
          exercise_ids: Array.from(selected),
          note_to_singer: note || null,
          exercise_tone_targets: Object.keys(targets).length > 0 ? targets : null,
        },
      });
      setTemplates((prev) => [...(prev ?? []), created]);
      setTemplateName("");
      setShowSaveTemplateForm(false);
    } catch {
      setTemplateError("Could not save this template. Please try again.");
    } finally {
      setSavingTemplate(false);
    }
  }

  async function deleteTemplate(templateId: string) {
    try {
      await apiFetch(`/api/v1/coach/assignment-templates/${templateId}`, { method: "DELETE" });
      setTemplates((prev) => (prev ?? []).filter((t) => t.id !== templateId));
    } catch {
      // Best-effort -- the list simply keeps the item if the delete failed; the coach can retry.
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
      setAddError("Name and description are both required.");
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
      // Deliberately does NOT close the form or reset category/difficulty/duration -- a coach
      // adding several exercises in one sitting (often the same rough category) can keep going
      // without re-opening it or re-picking those each time. Only name/description clear.
      setNewName("");
      setNewInstructions("");
      setAddedThisSession((prev) => [...prev, created]);
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

  if (exercises === null || history === null || templates === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  const active = history.find((a) => a.status === "active");

  return (
    <div className="mx-auto w-full max-w-2xl">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Assign training</h1>
      <p className="mb-6 text-sm text-neutral-400">
        Assigned exercises are included in the Vrotégé&apos;s daily routine only where today&apos;s
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

      {templates.length > 0 && (
        <div className="mb-4 rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
          <p className="mb-2 text-xs text-neutral-400">
            Load from a saved template — replaces your current selection below.
          </p>
          <div className="flex flex-wrap gap-2">
            {templates.map((template) => (
              <div
                key={template.id}
                className="flex items-center gap-1 rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1"
              >
                <button
                  type="button"
                  onClick={() => applyTemplate(template)}
                  className="text-sm text-neutral-200 hover:text-emerald-400"
                >
                  {template.name}
                </button>
                <button
                  type="button"
                  onClick={() => deleteTemplate(template.id)}
                  aria-label={`Delete template ${template.name}`}
                  className="text-xs text-neutral-600 hover:text-red-400"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4">
        {!showSaveTemplateForm ? (
          <button
            type="button"
            onClick={() => setShowSaveTemplateForm(true)}
            disabled={selected.size === 0}
            className="rounded-lg border border-neutral-700 px-3 py-2 text-sm font-medium text-neutral-200 hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Save current selection as template
          </button>
        ) : (
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
            <input
              type="text"
              placeholder="Template name"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="mb-2 w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            {templateError && (
              <p className="mb-2 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">
                {templateError}
              </p>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={saveTemplate}
                disabled={savingTemplate}
                className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
              >
                {savingTemplate ? "Saving..." : "Save template"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowSaveTemplateForm(false);
                  setTemplateError(null);
                }}
                disabled={savingTemplate}
                className="rounded-lg border border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-800 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="mb-4">
        {!showAddForm ? (
          <button
            type="button"
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 rounded-lg border border-neutral-700 px-3 py-2 text-sm font-medium text-neutral-200 hover:bg-neutral-800"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-sm font-bold leading-none text-neutral-950">
              +
            </span>
            Create your own exercise
          </button>
        ) : (
          <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-3">
            <p className="mb-2 text-xs text-neutral-400">
              Adds a new exercise to the library — selectable below once saved. Add as many as
              you like; the form stays open after each save.
            </p>
            <input
              type="text"
              placeholder="Name"
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

            <button
              type="button"
              onClick={() => setShowAdvanced((s) => !s)}
              className="mb-2 text-xs text-neutral-500 hover:text-neutral-300"
            >
              {showAdvanced ? "Hide" : "Show"} category, difficulty & duration
              {!showAdvanced && (
                <span className="text-neutral-600">
                  {" "}
                  (currently {newCategory} &middot; {newDifficulty} &middot; {newDuration}s)
                </span>
              )}
            </button>
            {showAdvanced && (
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
            )}

            {addError && (
              <p className="mb-2 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">
                {addError}
              </p>
            )}

            {addedThisSession.length > 0 && (
              <div className="mb-2 rounded-lg border border-emerald-900 bg-emerald-950/20 p-2">
                <p className="mb-1 text-xs text-emerald-300">
                  Added just now ({addedThisSession.length}):
                </p>
                <ul className="text-xs text-neutral-300">
                  {addedThisSession.map((e) => (
                    <li key={e.id}>{e.name}</li>
                  ))}
                </ul>
              </div>
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
                onClick={() => {
                  setShowAddForm(false);
                  setAddedThisSession([]);
                  setAddError(null);
                }}
                disabled={addSubmitting}
                className="rounded-lg border border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-800 disabled:opacity-50"
              >
                Done
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
        placeholder="Note to Vrotégé (optional)"
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
