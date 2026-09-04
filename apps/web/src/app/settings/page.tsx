"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth-context";
import { ApiError, API_BASE } from "@/lib/apiClient";
import {
  API_TOKEN_SCOPES,
  type ApiToken,
  type ApiTokenCreateResponse,
  type ApiTokenScope,
} from "@/lib/types";

const CONFIRM_PHRASE = "DELETE";

const SCOPE_LABELS: Record<ApiTokenScope, string> = {
  recovery_trends: "Recovery score & history",
  vocal_range: "Vocal range summary",
  exercise_history: "Exercise & training history",
};

function DownloadDataSection() {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setDownloading(true);
    setError(null);
    try {
      const token = localStorage.getItem("vepair_access_token");
      const res = await fetch(`${API_BASE}/api/v1/profile/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vepair-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not download your data. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <section className="mb-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
      <h2 className="mb-1 text-sm font-medium text-neutral-200">Download my data</h2>
      <p className="mb-4 text-xs text-neutral-400">
        Get a copy of everything VepAIr has on your account — check-ins, measurements, vocal
        range history, exercise history, coach notes and messages, and more — as a single JSON
        file. Raw audio isn&apos;t included in the file; each recording links to where you can
        download it separately.
      </p>
      <button
        type="button"
        onClick={download}
        disabled={downloading}
        className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-50"
      >
        {downloading ? "Preparing..." : "Download my data"}
      </button>
      {error && <p className="mt-3 text-xs text-red-300">{error}</p>}
    </section>
  );
}

function ApiTokensSection() {
  const { apiFetch } = useAuth();
  const [tokens, setTokens] = useState<ApiToken[] | null>(null);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<Set<ApiTokenScope>>(new Set());
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<ApiTokenCreateResponse | null>(null);

  async function load() {
    try {
      setTokens(await apiFetch<ApiToken[]>("/api/v1/api-tokens"));
    } catch {
      setTokens([]);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggleScope(scope: ApiTokenScope) {
    setScopes((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) {
        next.delete(scope);
      } else {
        next.add(scope);
      }
      return next;
    });
  }

  async function create() {
    if (!name.trim() || scopes.size === 0) {
      setCreateError("Give the token a name and select at least one scope.");
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const created = await apiFetch<ApiTokenCreateResponse>("/api/v1/api-tokens", {
        method: "POST",
        body: { name, scopes: Array.from(scopes) },
      });
      setJustCreated(created);
      setName("");
      setScopes(new Set());
      await load();
    } catch {
      setCreateError("Could not create this token. Please try again.");
    } finally {
      setCreating(false);
    }
  }

  async function revoke(tokenId: string) {
    try {
      await apiFetch(`/api/v1/api-tokens/${tokenId}`, { method: "DELETE" });
      await load();
    } catch {
      // Best-effort -- the list simply keeps showing it as active if the revoke failed.
    }
  }

  return (
    <section className="mb-6 rounded-2xl border border-neutral-800 bg-neutral-900/60 p-5">
      <h2 className="mb-1 text-sm font-medium text-neutral-200">API access</h2>
      <p className="mb-4 text-xs text-neutral-400">
        Generate a personal access token to pull your own recovery, vocal range, or training
        data into another tool you use. Read-only — raw recordings and check-in notes are never
        reachable this way. A token only works while an admin has the public API turned on.
      </p>

      {justCreated && (
        <div className="mb-4 rounded-lg border border-emerald-800 bg-emerald-950/20 p-3">
          <p className="mb-2 text-xs text-emerald-300">
            Copy this token now — it won&apos;t be shown again.
          </p>
          <code className="mb-2 block break-all rounded-lg bg-neutral-950 px-2 py-1.5 text-xs text-neutral-200">
            {justCreated.token}
          </code>
          <button
            type="button"
            onClick={() => setJustCreated(null)}
            className="rounded-lg border border-neutral-700 px-3 py-1 text-xs hover:bg-neutral-800"
          >
            Done
          </button>
        </div>
      )}

      {tokens && tokens.length > 0 && (
        <ul className="mb-4 space-y-2">
          {tokens.map((token) => (
            <li
              key={token.id}
              className="flex items-center justify-between rounded-lg border border-neutral-800 px-3 py-2 text-xs"
            >
              <div>
                <p className="text-neutral-200">{token.name}</p>
                <p className="text-neutral-500">
                  {token.scopes.map((s) => SCOPE_LABELS[s]).join(", ")}
                  {token.revoked_at ? " · revoked" : ""}
                </p>
              </div>
              {!token.revoked_at && (
                <button
                  type="button"
                  onClick={() => revoke(token.id)}
                  className="text-red-400 hover:text-red-300"
                >
                  Revoke
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
        <input
          type="text"
          placeholder="Token name (e.g. Zapier)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mb-2 w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
        <div className="mb-2 space-y-1">
          {API_TOKEN_SCOPES.map((scope) => (
            <label key={scope} className="flex items-center gap-2 text-xs text-neutral-300">
              <input
                type="checkbox"
                checked={scopes.has(scope)}
                onChange={() => toggleScope(scope)}
                className="h-4 w-4 rounded border-neutral-700 bg-neutral-900"
              />
              {SCOPE_LABELS[scope]}
            </label>
          ))}
        </div>
        {createError && (
          <p className="mb-2 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">
            {createError}
          </p>
        )}
        <button
          type="button"
          onClick={create}
          disabled={creating}
          className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-50"
        >
          {creating ? "Creating..." : "Create token"}
        </button>
      </div>
    </section>
  );
}

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

        <DownloadDataSection />
        <ApiTokensSection />
        <DeleteAccountSection />
      </main>
    </RequireAuth>
  );
}
