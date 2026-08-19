"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type { AdminSiteSettings, AdminUserListItem } from "@/lib/types";
import { ApiError } from "@/lib/apiClient";

function SiteSettingsPanel() {
  const { apiFetch } = useAuth();
  const [settings, setSettings] = useState<AdminSiteSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiFetch<AdminSiteSettings>("/api/v1/admin/site-settings")
      .then(setSettings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Something went wrong."));
  }, [apiFetch]);

  async function update(next: Partial<AdminSiteSettings>) {
    if (!settings) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiFetch<AdminSiteSettings>("/api/v1/admin/site-settings", {
        method: "POST",
        body: { ...settings, ...next },
      });
      setSettings(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (!settings) return null;

  return (
    <div className="mb-8 space-y-3">
      <section
        className={`flex items-center justify-between rounded-lg border px-4 py-3 text-sm ${
          settings.signups_enabled
            ? "border-neutral-800 bg-neutral-900/40"
            : "border-red-900 bg-red-950/40"
        }`}
      >
        <div>
          <p className="font-medium">
            New signups are {settings.signups_enabled ? "open" : "locked down"}
          </p>
          <p className="text-xs text-neutral-400">
            {settings.signups_enabled
              ? "Anyone can create an account from the public signup pages."
              : "The public signup and coach-signup pages are rejecting new accounts. Admin-created accounts still work."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => update({ signups_enabled: !settings.signups_enabled })}
          disabled={busy}
          className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${
            settings.signups_enabled
              ? "border-red-800 text-red-300 hover:bg-red-950/60"
              : "border-emerald-700 text-emerald-300 hover:bg-emerald-950/60"
          }`}
        >
          {busy ? "..." : settings.signups_enabled ? "Lock down signups" : "Re-open signups"}
        </button>
      </section>

      <section
        className={`flex items-center justify-between rounded-lg border px-4 py-3 text-sm ${
          settings.nda_required
            ? "border-amber-900 bg-amber-950/20"
            : "border-neutral-800 bg-neutral-900/40"
        }`}
      >
        <div>
          <p className="font-medium">
            Beta NDA is {settings.nda_required ? "required" : "not required"} on login
          </p>
          <p className="text-xs text-neutral-400">
            {settings.nda_required
              ? "Every user has to accept the beta NDA before they can use the app. Turn this off once the beta phase ends."
              : "The NDA pop-up is off — users go straight into the app after logging in."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => update({ nda_required: !settings.nda_required })}
          disabled={busy}
          className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${
            settings.nda_required
              ? "border-amber-700 text-amber-300 hover:bg-amber-950/60"
              : "border-neutral-700 text-neutral-300 hover:bg-neutral-800"
          }`}
        >
          {busy ? "..." : settings.nda_required ? "Turn off NDA gate" : "Turn on NDA gate"}
        </button>
      </section>

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

const ACCOUNT_TYPE_OPTIONS = ["singer", "coach"] as const;

function CreateUserForm({ onCreated }: { onCreated: (user: AdminUserListItem) => void }) {
  const { apiFetch } = useAuth();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [accountType, setAccountType] = useState<(typeof ACCOUNT_TYPE_OPTIONS)[number]>("singer");
  const [displayName, setDisplayName] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  function reset() {
    setEmail("");
    setPassword("");
    setAccountType("singer");
    setDisplayName("");
    setIsAdmin(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const user = await apiFetch<AdminUserListItem>("/api/v1/admin/users", {
        method: "POST",
        body: {
          email,
          password,
          account_type: accountType,
          display_name: accountType === "coach" ? displayName.trim() : undefined,
          is_admin: isAdmin,
        },
      });
      setSuccess(`Created ${user.email}.`);
      onCreated(user);
      reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mb-8 rounded-lg border border-neutral-800 p-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-sm font-medium hover:text-neutral-200"
      >
        {open ? "Cancel" : "+ Create user"}
      </button>
      {open && (
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          {error && <p className="text-sm text-red-400">{error}</p>}
          {success && <p className="text-sm text-emerald-400">{success}</p>}
          <div className="flex gap-2">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              className="w-full max-w-sm rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            <input
              type="text"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password (min 8 characters)"
              className="w-full max-w-sm rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex gap-1 rounded-lg border border-neutral-800 p-1 text-xs">
              {ACCOUNT_TYPE_OPTIONS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setAccountType(t)}
                  className={`rounded-md px-2.5 py-1.5 capitalize ${
                    accountType === t
                      ? "bg-emerald-500 text-neutral-950"
                      : "text-neutral-400 hover:bg-neutral-800"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
            {accountType === "coach" && (
              <input
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Coach display name"
                className="rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
              />
            )}
            <label className="flex items-center gap-2 text-xs text-neutral-400">
              <input
                type="checkbox"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
                className="rounded border-neutral-700 bg-neutral-900"
              />
              Grant admin
            </label>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create account"}
          </button>
        </form>
      )}
    </section>
  );
}

function AdminUserSearch({ refreshToken }: { refreshToken: number }) {
  const { apiFetch } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AdminUserListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch(q: string) {
    setLoading(true);
    setError(null);
    try {
      const rows = await apiFetch<AdminUserListItem[]>("/api/v1/admin/users", {
        searchParams: q ? { query: q } : undefined,
      });
      setResults(rows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (refreshToken > 0) runSearch(query);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshToken]);

  return (
    <section>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          runSearch(query);
        }}
        className="mb-6 flex gap-2"
      >
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by email..."
          className="w-full max-w-sm rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      {results === null ? (
        <p className="text-sm text-neutral-500">
          Enter an email substring, or search with an empty query to list the most recent 100
          signups.
        </p>
      ) : results.length === 0 ? (
        <p className="text-sm text-neutral-500">No matching accounts.</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-neutral-800 text-left text-neutral-400">
              <th className="py-2 pr-4">Email</th>
              <th className="py-2 pr-4">Type</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Onboarded</th>
              <th className="py-2 pr-4">Signed up</th>
            </tr>
          </thead>
          <tbody>
            {results.map((u) => (
              <tr key={u.id} className="border-b border-neutral-900">
                <td className="py-2 pr-4">
                  <Link href={`/admin/users/${u.id}`} className="underline hover:text-neutral-200">
                    {u.email}
                  </Link>
                  {u.is_admin && <span className="ml-2 text-xs text-amber-400">(admin)</span>}
                </td>
                <td className="py-2 pr-4">{u.account_type}</td>
                <td className="py-2 pr-4">
                  {u.is_active ? "active" : <span className="text-red-400">deactivated</span>}
                </td>
                <td className="py-2 pr-4">{u.onboarding_complete ? "yes" : "no"}</td>
                <td className="py-2 pr-4">{new Date(u.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export default function AdminPage() {
  const [refreshToken, setRefreshToken] = useState(0);

  return (
    <RequireAuth>
      <RequireAdmin>
        <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="mb-1 text-2xl font-semibold tracking-tight">Admin</h1>
              <p className="text-sm text-neutral-400">Search and manage user accounts.</p>
            </div>
            <div className="flex gap-4">
              <a
                href="https://claude.ai/code/artifact/1dd7d89c-8b40-4396-ae21-04324c9c09a0"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm underline hover:text-neutral-200"
              >
                Admin guide
              </a>
              <Link
                href="/admin/organizations"
                className="text-sm underline hover:text-neutral-200"
              >
                Organizations
              </Link>
              <Link href="/admin/reports" className="text-sm underline hover:text-neutral-200">
                Reports
              </Link>
            </div>
          </div>
          <SiteSettingsPanel />
          <CreateUserForm onCreated={() => setRefreshToken((t) => t + 1)} />
          <AdminUserSearch refreshToken={refreshToken} />
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
