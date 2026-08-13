"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { useAuth } from "@/lib/auth-context";
import type { CoachAssignment, Exercise } from "@/lib/types";

function AssignContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ singerId: string }>();
  const [exercises, setExercises] = useState<Exercise[] | null>(null);
  const [history, setHistory] = useState<CoachAssignment[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
      await apiFetch(`/api/v1/coach/singers/${params.singerId}/assignments`, {
        method: "POST",
        body: { exercise_ids: Array.from(selected), note_to_singer: note || null },
      });
      setSelected(new Set());
      setNote("");
      await load();
    } catch {
      setError("Could not save this assignment. Please try again.");
    } finally {
      setSubmitting(false);
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
            {active.exercise_ids.map((id) => (
              <li key={id}>{exercises.find((e) => e.id === id)?.name ?? id}</li>
            ))}
          </ul>
          {active.note_to_singer && (
            <p className="mt-2 text-xs text-neutral-500">
              &ldquo;{active.note_to_singer}&rdquo;
            </p>
          )}
        </div>
      )}

      <div className="mb-4 space-y-1.5">
        {exercises.map((exercise) => (
          <label
            key={exercise.id}
            className="flex items-center gap-2 rounded-lg border border-neutral-800 bg-neutral-900/60 p-2 text-sm text-neutral-300"
          >
            <input
              type="checkbox"
              checked={selected.has(exercise.id)}
              onChange={() => toggle(exercise.id)}
              className="h-4 w-4 rounded border-neutral-700 bg-neutral-900"
            />
            <span>
              {exercise.name}{" "}
              <span className="text-xs text-neutral-500">
                &middot; {exercise.category} &middot; {exercise.difficulty}
              </span>
            </span>
          </label>
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
