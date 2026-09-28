"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { useAuth } from "@/lib/auth-context";
import type { SingerCoachNote } from "@/lib/types";

const MAX_NOTE_LENGTH = 2000;

function NotesContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ singerId: string }>();
  const [notes, setNotes] = useState<SingerCoachNote[] | null>(null);
  const [body, setBody] = useState("");
  const [lastWarning, setLastWarning] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    try {
      const data = await apiFetch<SingerCoachNote[]>(
        `/api/v1/coach/singers/${params.singerId}/notes`
      );
      setNotes(data);
    } catch {
      setError("Could not load notes for this Vrotégé.");
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.singerId]);

  async function submit() {
    if (!body.trim()) return;
    setSubmitting(true);
    setError(null);
    setLastWarning(null);
    try {
      const created = await apiFetch<SingerCoachNote>(
        `/api/v1/coach/singers/${params.singerId}/notes`,
        { method: "POST", body: { body } }
      );
      setBody("");
      if (created.flagged_terms && created.flagged_terms.length > 0) {
        setLastWarning(created.flagged_terms);
      }
      await load();
    } catch {
      setError("Could not save this note. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function deleteNote(noteId: string) {
    await apiFetch(`/api/v1/coach/notes/${noteId}`, { method: "DELETE" });
    await load();
  }

  if (error && notes === null) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (notes === null) {
    return <p className="text-sm text-text-faint">Loading...</p>;
  }

  return (
    <div className="mx-auto w-full max-w-2xl">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Notes</h1>
      <p className="mb-2 rounded-lg border border-warning bg-warning-faint px-3 py-2 text-xs text-warning">
        Notes are for coaching purposes only — not a medical or clinical record. Do not record
        diagnoses, medical history, or clinical assessments here. The Vrotégé can read every
        note you write.
      </p>

      <div className="mb-6 mt-4">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value.slice(0, MAX_NOTE_LENGTH))}
          rows={3}
          placeholder="Great breath support today — keep working the glide exercises."
          className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <p className="mt-1 text-right text-xs text-text-faint">
          {body.length}/{MAX_NOTE_LENGTH}
        </p>

        {lastWarning && (
          <p className="mb-2 rounded-lg bg-warning-faint px-3 py-2 text-xs text-warning">
            This note was saved, but contains language that may read as clinical (
            {lastWarning.join(", ")}) — consider rephrasing as an observation or a suggestion
            to see a professional, rather than a diagnosis.
          </p>
        )}
        {error && (
          <p className="mb-2 rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
        )}

        <button
          type="button"
          onClick={submit}
          disabled={submitting || !body.trim()}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Save note"}
        </button>
      </div>

      <div className="space-y-2">
        {notes.length === 0 ? (
          <p className="text-sm text-text-faint">No notes yet.</p>
        ) : (
          notes.map((note) => (
            <div
              key={note.id}
              className="rounded-xl border border-border bg-surface/60 p-4"
            >
              <p className="text-sm text-text">{note.body}</p>
              <div className="mt-2 flex items-center justify-between">
                <p className="text-xs text-text-faint">
                  {new Date(note.created_at).toLocaleString()}
                  {note.flagged_terms && note.flagged_terms.length > 0 && (
                    <span className="ml-2 text-warning">flagged for review</span>
                  )}
                </p>
                <button
                  type="button"
                  onClick={() => deleteNote(note.id)}
                  className="text-xs text-text-faint hover:text-danger"
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-8">
        <Link
          href={`/coach/singers/${params.singerId}`}
          className="text-xs text-text-faint hover:text-text-dim"
        >
          &larr; Back to dashboard
        </Link>
      </div>
    </div>
  );
}

export default function CoachNotesPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-6 py-10">
          <NotesContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
