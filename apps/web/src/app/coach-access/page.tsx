"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth-context";
import {
  COACH_SHARE_CATEGORIES,
  COACH_SHARE_CATEGORY_LABEL,
  type CoachConnection,
  type CoachShareCategory,
  type SingerCoachNote,
  type SingerInvite,
} from "@/lib/types";

function InviteCard({
  invite,
  onRespond,
}: {
  invite: SingerInvite;
  onRespond: () => void;
}) {
  const { apiFetch } = useAuth();
  const [checked, setChecked] = useState<Set<CoachShareCategory>>(new Set());
  const [busy, setBusy] = useState<"accept" | "decline" | null>(null);
  const [error, setError] = useState<string | null>(null);

  function toggle(category: CoachShareCategory) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  }

  async function accept() {
    if (checked.size === 0) {
      setError("Select at least one category to share, or decline instead.");
      return;
    }
    setBusy("accept");
    setError(null);
    try {
      await apiFetch(`/api/v1/invites/${invite.id}/accept`, {
        method: "POST",
        body: { granted_categories: Array.from(checked) },
      });
      onRespond();
    } catch {
      setError("Could not accept this invite. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  async function decline() {
    setBusy("decline");
    setError(null);
    try {
      await apiFetch(`/api/v1/invites/${invite.id}/decline`, { method: "POST" });
      onRespond();
    } catch {
      setError("Could not decline this invite. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
      <p className="text-sm font-medium text-neutral-100">
        {invite.coach_display_name}
        {invite.coach_studio_name && (
          <span className="text-neutral-500"> &middot; {invite.coach_studio_name}</span>
        )}
      </p>
      {invite.message && (
        <p className="mt-1 text-sm text-neutral-400">&ldquo;{invite.message}&rdquo;</p>
      )}

      <p className="mt-3 mb-2 text-xs text-neutral-500">
        Choose what to share — nothing is selected by default:
      </p>
      <div className="space-y-1.5">
        {COACH_SHARE_CATEGORIES.map((category) => (
          <label key={category} className="flex items-center gap-2 text-sm text-neutral-300">
            <input
              type="checkbox"
              checked={checked.has(category)}
              onChange={() => toggle(category)}
              className="h-4 w-4 rounded border-neutral-700 bg-neutral-900"
            />
            {COACH_SHARE_CATEGORY_LABEL[category]}
          </label>
        ))}
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
      )}

      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={accept}
          disabled={busy !== null}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          {busy === "accept" ? "Accepting..." : "Accept"}
        </button>
        <button
          type="button"
          onClick={decline}
          disabled={busy !== null}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
        >
          {busy === "decline" ? "Declining..." : "Decline"}
        </button>
      </div>
      <p className="mt-3 text-xs text-neutral-500">
        You can change or revoke this any time.
      </p>
    </div>
  );
}

function ConnectionCard({
  connection,
  onChange,
}: {
  connection: CoachConnection;
  onChange: () => void;
}) {
  const { apiFetch } = useAuth();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState<SingerCoachNote[] | null>(null);
  const isActive = connection.status === "active";
  const granted = new Set(connection.granted_categories);

  async function toggleNotes() {
    if (notes !== null) {
      setNotes(null);
      return;
    }
    try {
      const data = await apiFetch<SingerCoachNote[]>(
        `/api/v1/coach-connections/${connection.id}/notes`
      );
      setNotes(data);
    } catch {
      setError("Could not load notes.");
    }
  }

  async function toggleCategory(category: CoachShareCategory) {
    setBusy(category);
    setError(null);
    try {
      await apiFetch(`/api/v1/coach-connections/${connection.id}/categories`, {
        method: "PATCH",
        body: { category, granted: !granted.has(category) },
      });
      onChange();
    } catch {
      setError("Could not update this category. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  async function revoke() {
    if (
      !window.confirm(
        "Your coach will lose access to new data immediately. This does not undo anything they already viewed. Continue?"
      )
    ) {
      return;
    }
    setBusy("revoke");
    setError(null);
    try {
      await apiFetch(`/api/v1/coach-connections/${connection.id}`, { method: "DELETE" });
      onChange();
    } catch {
      setError("Could not revoke access. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-neutral-100">
          {connection.coach_display_name}
          {connection.coach_studio_name && (
            <span className="text-neutral-500"> &middot; {connection.coach_studio_name}</span>
          )}
        </p>
        <span
          className={`text-xs ${isActive ? "text-emerald-400" : "text-neutral-500"}`}
        >
          {isActive ? "Active" : "Revoked"}
        </span>
      </div>

      {isActive ? (
        <div className="mt-3 space-y-1.5">
          {COACH_SHARE_CATEGORIES.map((category) => (
            <label key={category} className="flex items-center gap-2 text-sm text-neutral-300">
              <input
                type="checkbox"
                checked={granted.has(category)}
                disabled={busy !== null}
                onChange={() => toggleCategory(category)}
                className="h-4 w-4 rounded border-neutral-700 bg-neutral-900"
              />
              {COACH_SHARE_CATEGORY_LABEL[category]}
            </label>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-xs text-neutral-500">
          Shared: {connection.granted_categories.map((c) => COACH_SHARE_CATEGORY_LABEL[c]).join(", ") || "nothing"}
        </p>
      )}

      {error && (
        <p className="mt-3 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
      )}

      <div className="mt-4 flex gap-2">
        {isActive && (
          <button
            type="button"
            onClick={revoke}
            disabled={busy !== null}
            className="rounded-lg border border-red-900 px-4 py-2 text-sm text-red-300 hover:bg-red-950/40 disabled:opacity-50"
          >
            {busy === "revoke" ? "Revoking..." : "Revoke access"}
          </button>
        )}
        <button
          type="button"
          onClick={toggleNotes}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
        >
          {notes === null ? "View notes" : "Hide notes"}
        </button>
      </div>

      {notes !== null && (
        <div className="mt-3 space-y-2">
          {notes.length === 0 ? (
            <p className="text-xs text-neutral-500">No notes yet.</p>
          ) : (
            notes.map((note) => (
              <div key={note.id} className="rounded-lg border border-neutral-800 p-2">
                <p className="text-sm text-neutral-300">{note.body}</p>
                <p className="mt-1 text-xs text-neutral-600">
                  {new Date(note.created_at).toLocaleString()}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function CoachAccessContent() {
  const { apiFetch } = useAuth();
  const [invites, setInvites] = useState<SingerInvite[] | null>(null);
  const [connections, setConnections] = useState<CoachConnection[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [invitesData, connectionsData] = await Promise.all([
        apiFetch<SingerInvite[]>("/api/v1/invites"),
        apiFetch<CoachConnection[]>("/api/v1/coach-connections"),
      ]);
      setInvites(invitesData);
      setConnections(connectionsData);
    } catch {
      setError("Could not load your coach access settings.");
    }
  }

  useEffect(() => {
    // Data-fetch-on-mount: setInvites/setConnections/setError run after an awaited network
    // call inside load(), not synchronously in this effect body.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (invites === null || connections === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  return (
    <div className="mx-auto w-full max-w-lg">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Coach Access</h1>
      <p className="mb-8 text-sm text-neutral-400">
        Control which vocal coaches can see your data, and exactly what they can see. Nothing
        is shared automatically — a coach only sees what you explicitly choose.
      </p>

      <section className="mb-8">
        <h2 className="mb-3 text-sm font-medium text-neutral-200">Pending invites</h2>
        {invites.length === 0 ? (
          <p className="text-sm text-neutral-500">No pending invites.</p>
        ) : (
          <div className="space-y-3">
            {invites.map((invite) => (
              <InviteCard key={invite.id} invite={invite} onRespond={load} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium text-neutral-200">Your coaches</h2>
        {connections.length === 0 ? (
          <p className="text-sm text-neutral-500">No coach connections yet.</p>
        ) : (
          <div className="space-y-3">
            {connections.map((connection) => (
              <ConnectionCard key={connection.id} connection={connection} onChange={load} />
            ))}
          </div>
        )}
      </section>

      <div className="mt-8">
        <Link href="/" className="text-xs text-neutral-500 hover:text-neutral-300">
          &larr; Back to dashboard
        </Link>
      </div>
    </div>
  );
}

export default function CoachAccessPage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <CoachAccessContent />
      </main>
    </RequireAuth>
  );
}
