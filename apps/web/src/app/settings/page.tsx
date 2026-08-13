"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/apiClient";

const CONFIRM_PHRASE = "DELETE";

function DeleteAccountSection() {
  const { deleteAccount } = useAuth();
  const [showConfirm, setShowConfirm] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleDelete(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await deleteAccount(password);
      // deleteAccount() clears the local session; RequireAuth picks up the status change
      // and redirects to /login on its own — no navigation needed here.
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      setSubmitting(false);
    }
  }

  return (
    <section className="rounded-2xl border border-red-900/60 bg-red-950/10 p-5">
      <h2 className="mb-1 text-sm font-medium text-red-300">Delete my account</h2>
      <p className="mb-4 text-xs text-neutral-400">
        This permanently deletes your account, every recording you&apos;ve uploaded (the actual
        audio files, not just the database record), and everything derived from them —
        check-ins, measurements, vocal range history, exercise history, coach connections, and
        notes. This cannot be undone.
      </p>

      {!showConfirm ? (
        <button
          type="button"
          onClick={() => setShowConfirm(true)}
          className="rounded-lg border border-red-800 px-3 py-1.5 text-sm text-red-300 hover:bg-red-950/40"
        >
          Delete my account
        </button>
      ) : (
        <form onSubmit={handleDelete} className="space-y-3">
          <div>
            <label htmlFor="delete-password" className="mb-1 block text-xs text-neutral-400">
              Confirm your password
            </label>
            <input
              id="delete-password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-red-600"
            />
          </div>

          <div>
            <label htmlFor="delete-confirm" className="mb-1 block text-xs text-neutral-400">
              Type <span className="font-mono text-red-300">{CONFIRM_PHRASE}</span> to confirm
            </label>
            <input
              id="delete-confirm"
              type="text"
              required
              autoComplete="off"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-red-600"
            />
          </div>

          {error && (
            <p className="rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
          )}

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={submitting || confirmText !== CONFIRM_PHRASE}
              className="rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Deleting..." : "Permanently delete my account"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowConfirm(false);
                setPassword("");
                setConfirmText("");
                setError(null);
              }}
              disabled={submitting}
              className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

export default function SettingsPage() {
  return (
    <RequireAuth>
      <main className="mx-auto w-full max-w-lg flex-1 px-6 py-12">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mb-8 text-sm text-neutral-400">
          Manage your account. For onboarding preferences and notifications, see{" "}
          <a href="/onboarding" className="underline hover:text-neutral-200">
            your profile
          </a>
          .
        </p>

        <DeleteAccountSection />
      </main>
    </RequireAuth>
  );
}
