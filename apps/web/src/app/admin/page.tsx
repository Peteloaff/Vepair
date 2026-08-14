"use client";

import { useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type { AdminUserListItem } from "@/lib/types";
import { ApiError } from "@/lib/apiClient";

function AdminUserSearch() {
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
              <Link href="/admin/reports" className="text-sm underline hover:text-neutral-200">
                Reports
              </Link>
            </div>
          </div>
          <AdminUserSearch />
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
