"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type { AdminOrganization } from "@/lib/types";
import { ApiError } from "@/lib/apiClient";

function AdminOrganizationSearch({ refreshToken }: { refreshToken: number }) {
  const { apiFetch } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AdminOrganization[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch(q: string) {
    setLoading(true);
    setError(null);
    try {
      const rows = await apiFetch<AdminOrganization[]>("/api/v1/admin/organizations", {
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
    if (refreshToken > 0) void runSearch(query);
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
          placeholder="Search by org name, coach email, or coach name..."
          className="w-full max-w-sm rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2 disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      {results === null ? (
        <p className="text-sm text-text-faint">
          Enter a search term, or search with an empty query to list the most recent 100
          coach organizations.
        </p>
      ) : results.length === 0 ? (
        <p className="text-sm text-text-faint">No matching organizations.</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-dim">
              <th className="py-2 pr-4">Organization</th>
              <th className="py-2 pr-4">Coach</th>
              <th className="py-2 pr-4">Coach Pro</th>
              <th className="py-2 pr-4">Invites used</th>
            </tr>
          </thead>
          <tbody>
            {results.map((org) => (
              <tr key={org.id} className="border-b border-border">
                <td className="py-2 pr-4">
                  <Link
                    href={`/admin/organizations/${org.id}`}
                    className="underline hover:text-text"
                  >
                    {org.name || "(unnamed)"}
                  </Link>
                </td>
                <td className="py-2 pr-4">
                  {org.coach_display_name} &middot; {org.coach_email}
                  {org.member_count > 1 && (
                    <span className="text-text-faint"> &middot; +{org.member_count - 1} more</span>
                  )}
                </td>
                <td className="py-2 pr-4">
                  {org.is_coach_pro_active ? (
                    "active"
                  ) : (
                    <span className="text-warning">inactive</span>
                  )}
                </td>
                <td className="py-2 pr-4">
                  {org.invites_used_this_period} / {org.invite_quota_included}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

type DemoStatus = { exists: boolean; organizations: number; singers: number };

function DemoDataPanel({ onChanged }: { onChanged: () => void }) {
  const { apiFetch } = useAuth();
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<DemoStatus>("/api/v1/admin/demo-data")
      .then(setStatus)
      .catch(() => setStatus(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(path: string, message: (r: Record<string, number>) => string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await apiFetch<Record<string, number>>(path, { method: "POST" });
      setNotice(message(result));
      setConfirmRemove(false);
      setStatus(await apiFetch<DemoStatus>("/api/v1/admin/demo-data"));
      onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "The request didn't complete — try again, and check the server logs if it keeps happening."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mb-8 rounded-2xl border border-border bg-surface p-4">
      <h2 className="text-sm font-medium">Demo data</h2>
      <p className="mt-1 mb-3 text-xs text-text-dim">
        Adds four fake organizations (an active one, one over its invite quota, one with Coach Pro
        turned off, and a brand-new one), each with a coach, singers, check-ins, and activity, so
        you can see how this page and the Coach Portal behave. Demo accounts use{" "}
        <code className="font-mono">@demo.vepair.invalid</code> emails, can&apos;t log in, and send
        no email. Removing them deletes only those accounts; nothing else is touched.
      </p>
      {status?.exists && (
        <p className="mb-3 text-xs text-text-dim">
          Currently in the system: {status.organizations} demo organizations and {status.singers}{" "}
          demo singers.
        </p>
      )}
      {error && <p className="mb-3 text-xs text-danger">{error}</p>}
      {notice && <p className="mb-3 text-xs text-accent">{notice}</p>}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy || status?.exists}
          onClick={() =>
            run("/api/v1/admin/demo-data", (r) =>
              r.created
                ? `Created ${r.organizations} organizations and ${r.singers} singers.`
                : "Demo data already exists."
            )
          }
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy && !confirmRemove ? "Working..." : "Add demo organizations"}
        </button>
        {!confirmRemove ? (
          <button
            type="button"
            disabled={busy || !status?.exists}
            onClick={() => setConfirmRemove(true)}
            className="rounded-lg border border-danger px-4 py-2 text-sm text-danger hover:bg-danger-faint disabled:cursor-not-allowed disabled:opacity-40"
          >
            Remove demo data
          </button>
        ) : (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                run(
                  "/api/v1/admin/demo-data/remove",
                  (r) =>
                    `Removed ${r.removed_accounts} demo accounts and ${r.removed_organizations} organizations.`
                )
              }
              className="rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {busy ? "Removing..." : "Yes, remove all demo data"}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirmRemove(false)}
              className="rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2"
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </section>
  );
}

export default function AdminOrganizationsPage() {
  const [refreshToken, setRefreshToken] = useState(0);
  return (
    <RequireAuth>
      <RequireAdmin>
        <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="mb-1 text-2xl font-semibold tracking-tight">Organizations</h1>
              <p className="text-sm text-text-dim">
                Coach billing entities — one per coach account. Activate Coach Pro to unblock a
                coach&apos;s account.
              </p>
            </div>
            <Link href="/admin" className="text-sm underline hover:text-text">
              ← Back to Admin
            </Link>
          </div>
          <DemoDataPanel onChanged={() => setRefreshToken((t) => t + 1)} />
          <AdminOrganizationSearch refreshToken={refreshToken} />
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
