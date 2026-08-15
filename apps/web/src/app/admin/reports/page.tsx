"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type { AdminReportsSummary, AdminUserListItem } from "@/lib/types";
import { ApiError } from "@/lib/apiClient";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-neutral-800 p-4">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}

const TRI_STATE_LABEL: Record<string, string> = { "": "Any", true: "Yes", false: "No" };

function TriStateSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-neutral-400">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm text-neutral-200 outline-none focus:border-neutral-500"
      >
        {["", "true", "false"].map((v) => (
          <option key={v} value={v}>
            {TRI_STATE_LABEL[v]}
          </option>
        ))}
      </select>
    </label>
  );
}

function ReportQuery() {
  const { apiFetch } = useAuth();
  const [email, setEmail] = useState("");
  const [accountType, setAccountType] = useState("");
  const [isActive, setIsActive] = useState("");
  const [isAdmin, setIsAdmin] = useState("");
  const [onboardingComplete, setOnboardingComplete] = useState("");
  const [createdAfter, setCreatedAfter] = useState("");
  const [createdBefore, setCreatedBefore] = useState("");
  const [results, setResults] = useState<AdminUserListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runReport() {
    setLoading(true);
    setError(null);
    const searchParams: Record<string, string> = {};
    if (email) searchParams.email = email;
    if (accountType) searchParams.account_type = accountType;
    if (isActive) searchParams.is_active = isActive;
    if (isAdmin) searchParams.is_admin = isAdmin;
    if (onboardingComplete) searchParams.onboarding_complete = onboardingComplete;
    if (createdAfter) searchParams.created_after = createdAfter;
    if (createdBefore) searchParams.created_before = createdBefore;
    try {
      const rows = await apiFetch<AdminUserListItem[]>("/api/v1/admin/reports/query", {
        searchParams,
      });
      setResults(rows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run this report.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-10">
      <h2 className="mb-1 text-lg font-medium tracking-tight">Run a report</h2>
      <p className="mb-4 text-sm text-neutral-400">
        Filter on any combination of fields below — every filter is optional and they combine
        together (AND, not OR).
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          runReport();
        }}
        className="mb-6 rounded-2xl border border-neutral-800 p-4"
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <label className="col-span-2 flex flex-col gap-1 text-xs text-neutral-400 sm:col-span-1">
            Email contains
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm outline-none focus:border-neutral-500"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs text-neutral-400">
            Account type
            <select
              value={accountType}
              onChange={(e) => setAccountType(e.target.value)}
              className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm text-neutral-200 outline-none focus:border-neutral-500"
            >
              <option value="">Any</option>
              <option value="singer">Singer</option>
              <option value="coach">Coach</option>
            </select>
          </label>

          <TriStateSelect label="Active" value={isActive} onChange={setIsActive} />
          <TriStateSelect label="Admin" value={isAdmin} onChange={setIsAdmin} />
          <TriStateSelect
            label="Onboarding complete"
            value={onboardingComplete}
            onChange={setOnboardingComplete}
          />

          <label className="flex flex-col gap-1 text-xs text-neutral-400">
            Signed up after
            <input
              type="date"
              value={createdAfter}
              onChange={(e) => setCreatedAfter(e.target.value)}
              className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm text-neutral-200 outline-none focus:border-neutral-500"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-neutral-400">
            Signed up before
            <input
              type="date"
              value={createdBefore}
              onChange={(e) => setCreatedBefore(e.target.value)}
              className="rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1.5 text-sm text-neutral-200 outline-none focus:border-neutral-500"
            />
          </label>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="mt-4 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          {loading ? "Running..." : "Run report"}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      {results !== null && (
        <>
          <p className="mb-2 text-xs text-neutral-500">
            {results.length} account{results.length === 1 ? "" : "s"} matched (capped at 200).
          </p>
          {results.length === 0 ? (
            <p className="text-sm text-neutral-500">No matching accounts.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-neutral-800 text-left text-neutral-400">
                    <th className="py-2 pr-4">Email</th>
                    <th className="py-2 pr-4">Type</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4">Admin</th>
                    <th className="py-2 pr-4">Onboarded</th>
                    <th className="py-2 pr-4">Signed up</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((u) => (
                    <tr key={u.id} className="border-b border-neutral-900">
                      <td className="py-2 pr-4">
                        <Link
                          href={`/admin/users/${u.id}`}
                          className="underline hover:text-neutral-200"
                        >
                          {u.email}
                        </Link>
                      </td>
                      <td className="py-2 pr-4">{u.account_type}</td>
                      <td className="py-2 pr-4">
                        {u.is_active ? "active" : <span className="text-red-400">deactivated</span>}
                      </td>
                      <td className="py-2 pr-4">{u.is_admin ? "yes" : "—"}</td>
                      <td className="py-2 pr-4">{u.onboarding_complete ? "yes" : "no"}</td>
                      <td className="py-2 pr-4">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ReportsContent() {
  const { apiFetch } = useAuth();
  const [summary, setSummary] = useState<AdminReportsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<AdminReportsSummary>("/api/v1/admin/reports/summary")
      .then(setSummary)
      .catch(() => setError("Could not load reports."));
  }, [apiFetch]);

  if (error) {
    return <p className="text-sm text-red-400">{error}</p>;
  }

  if (!summary) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <Stat label="Total users" value={summary.total_users} />
      <Stat label="Singers" value={summary.singer_count} />
      <Stat label="Coaches" value={summary.coach_count} />
      <Stat label="Active" value={summary.active_count} />
      <Stat label="Deactivated" value={summary.deactivated_count} />
      <Stat
        label="Onboarding completion"
        value={`${Math.round(summary.onboarding_completion_rate * 100)}%`}
      />
      <Stat label="Signups, last 7 days" value={summary.signups_last_7_days} />
      <Stat label="Signups, last 90 days" value={summary.signups_last_90_days} />
      <Stat label="DAU (proxy)" value={summary.dau} />
      <Stat label="WAU (proxy)" value={summary.wau} />
    </div>
  );
}

export default function AdminReportsPage() {
  return (
    <RequireAuth>
      <RequireAdmin>
        <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
          <div className="mb-8">
            <Link href="/admin" className="text-sm underline hover:text-neutral-200">
              ← Back to search
            </Link>
          </div>
          <h1 className="mb-1 text-2xl font-semibold tracking-tight">Reports</h1>
          <p className="mb-8 text-sm text-neutral-400">
            Aggregate, read-only figures over the current data. DAU/WAU are a proxy (distinct
            users with a check-in or recording in the window), not a true session-based metric —
            there&apos;s no login-event table yet.
          </p>
          <ReportsContent />
          <ReportQuery />
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
