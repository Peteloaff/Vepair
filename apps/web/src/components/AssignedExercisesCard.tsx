"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, Chip } from "@/components/Card";
import { Icon } from "@/components/icons";
import { useAuth } from "@/lib/auth-context";
import { todayLocalDate } from "@/lib/date";
import type { AssignedExercises } from "@/lib/types";

const OPEN_STORAGE_KEY = "vepair.assignedCardOpen";

// Collapsed unless the singer has opened it before on this device.
function savedOpenState(): boolean {
  try {
    return window.localStorage.getItem(OPEN_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function saveOpenState(open: boolean) {
  try {
    window.localStorage.setItem(OPEN_STORAGE_KEY, open ? "1" : "0");
  } catch {
    // Private mode or blocked storage: it just starts collapsed next time.
  }
}

// "Assigned by your coach" -- the singer's own, always-visible view of what a coach assigned,
// with a Start button. Renders nothing when there is no active assignment, so it can sit on any
// page (the home page, Coach Access) without leaving an empty box. With `collapsible` (the home
// page) it can be shrunk to a single line and starts that way.
export function AssignedExercisesCard({
  className = "",
  collapsible = false,
}: {
  className?: string;
  collapsible?: boolean;
}) {
  const { apiFetch } = useAuth();
  const [assigned, setAssigned] = useState<AssignedExercises | null>(null);
  // The card renders nothing until the fetch below finishes, so reading storage here can't
  // differ between the server render and the first client render.
  const [open, setOpen] = useState(() => !collapsible || savedOpenState());

  useEffect(() => {
    apiFetch<AssignedExercises>("/api/v1/assigned-exercises", {
      searchParams: { date: todayLocalDate() },
    })
      .then(setAssigned)
      .catch(() => {
        // Best-effort -- the page works without this card.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!assigned || !assigned.has_assignment) return null;

  const minutes = Math.max(1, Math.round(assigned.total_duration_seconds / 60));
  const canStart = assigned.items.length > 0;
  const coachLine = (
    <>
      {assigned.coach_display_name}
      {assigned.coach_studio_name ? ` · ${assigned.coach_studio_name}` : ""}
    </>
  );

  const body = (
    <>
      {assigned.note_to_singer && (
        <p className="mb-4 rounded-2xl bg-violet-faint px-4 py-3 text-sm text-text-dim">
          <span className="font-semibold text-violet">Note from your coach:</span>{" "}
          {assigned.note_to_singer}
        </p>
      )}

      {assigned.safety_message && (
        <p className="mb-4 rounded-2xl bg-warning-faint px-4 py-3 text-sm text-warning">
          {assigned.safety_message}
        </p>
      )}

      <ul className="mb-4 space-y-2">
        {assigned.items.map((exercise) => {
          const target = assigned.exercise_tone_targets[exercise.id];
          return (
            <li
              key={exercise.id}
              className="flex items-center justify-between gap-3 rounded-2xl border border-border bg-surface-2 px-4 py-3"
            >
              <span className="min-w-0">
                <span className="block font-medium">{exercise.name}</span>
                <span className="block text-xs text-text-faint">
                  {exercise.category} &middot; {Math.max(1, Math.round(exercise.duration_seconds / 60))} min
                </span>
              </span>
              {target && <Chip tone="violet">Target {target}</Chip>}
            </li>
          );
        })}
        {assigned.held_back.map((exercise) => (
          <li
            key={exercise.id}
            className="flex items-center justify-between gap-3 rounded-2xl border border-dashed border-border px-4 py-3 opacity-70"
          >
            <span className="min-w-0">
              <span className="block font-medium">{exercise.name}</span>
              <span className="block text-xs text-text-faint">{exercise.category}</span>
            </span>
            <Chip tone="warn">Held back today</Chip>
          </li>
        ))}
      </ul>

      {assigned.held_back.length > 0 && (
        <p className="mb-4 text-xs text-text-faint">
          {assigned.held_back.length === 1 ? "One exercise is" : `${assigned.held_back.length} exercises are`}{" "}
          held back for today because they&apos;re more demanding than is safe for your voice
          right now. They&apos;ll be available again when your check-in looks better.
        </p>
      )}

      {canStart ? (
        <Link
          href="/assigned"
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-accent-ink"
        >
          <Icon name="wave" className="h-4 w-4" />
          Start assigned exercises &middot; about {minutes} min
        </Link>
      ) : (
        <p className="text-sm text-text-dim">
          Nothing in this assignment is safe to run today. Rest up, and check back tomorrow.
        </p>
      )}
    </>
  );

  if (!collapsible) {
    return (
      <Card title="Assigned by your coach" meta={coachLine} className={className}>
        {body}
      </Card>
    );
  }

  const count = assigned.items.length;
  const summary = canStart
    ? `${count} ${count === 1 ? "exercise" : "exercises"} · about ${minutes} min`
    : "Nothing safe to run today";

  return (
    <Card className={className}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls="assigned-exercises-body"
        onClick={() => {
          setOpen(!open);
          saveOpenState(!open);
        }}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <span className="min-w-0">
          <span className="block text-lg font-medium tracking-tight">Assigned by your coach</span>
          <span className="block truncate text-xs text-text-faint">
            {coachLine} &middot; {summary}
          </span>
        </span>
        <svg
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className={`h-5 w-5 shrink-0 text-text-dim transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path d="M5 8l5 5 5-5" />
        </svg>
      </button>
      {open && (
        <div id="assigned-exercises-body" className="mt-4">
          {body}
        </div>
      )}
    </Card>
  );
}
