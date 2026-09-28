"use client";

import { useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type { AdminOrganization } from "@/lib/types";
import { ApiError } from "@/lib/apiClient";

function AdminOrganizationSearch() {
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

export default function AdminOrganizationsPage() {
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
          <AdminOrganizationSearch />
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
