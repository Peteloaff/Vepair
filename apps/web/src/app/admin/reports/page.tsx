"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type { AdminReportsSummary } from "@/lib/types";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-neutral-800 p-4">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
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
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
