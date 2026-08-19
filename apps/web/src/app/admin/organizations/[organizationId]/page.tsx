"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type { AdminOrganization } from "@/lib/types";
import { ApiError } from "@/lib/apiClient";

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function OrganizationDetailContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ organizationId: string }>();
  const [detail, setDetail] = useState<AdminOrganization | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function load() {
    apiFetch<AdminOrganization>(`/api/v1/admin/organizations/${params.organizationId}`)
      .then(setDetail)
      .catch(() => setError("Could not load this organization."));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.organizationId]);

  async function toggleCoachPro() {
    if (!detail) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch(`/api/v1/admin/organizations/${detail.id}/set-coach-pro`, {
        method: "POST",
        body: { is_coach_pro_active: !detail.is_coach_pro_active },
      });
      setNotice(
        detail.is_coach_pro_active
          ? "Coach Pro deactivated. The coach is locked out until reactivated."
          : "Coach Pro activated. The coach can use their account now."
      );
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !detail) {
    return <p className="text-sm text-red-400">{error}</p>;
  }

  if (!detail) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/admin/organizations" className="text-sm underline hover:text-neutral-200">
          ← Back to search
        </Link>
      </div>

      <section className="rounded-2xl border border-neutral-800 p-5">
        <h1 className="mb-1 text-xl font-semibold">{detail.name || "(unnamed organization)"}</h1>
        <p className="mb-4 text-sm text-neutral-400">
          {detail.coach_display_name} &middot; {detail.coach_email}
        </p>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <dt className="text-neutral-500">Coach Pro status</dt>
          <dd>
            {detail.is_coach_pro_active ? (
              "active"
            ) : (
              <span className="text-amber-400">inactive</span>
            )}
          </dd>
          <dt className="text-neutral-500">Period start</dt>
          <dd>{formatDate(detail.coach_pro_period_start)}</dd>
          <dt className="text-neutral-500">Period end</dt>
          <dd>{formatDate(detail.coach_pro_period_end)}</dd>
          <dt className="text-neutral-500">Invites used this period</dt>
          <dd>
            {detail.invites_used_this_period} / {detail.invite_quota_included} included
            {detail.invites_used_this_period > detail.invite_quota_included && (
              <span className="ml-1 text-amber-400">
                ({detail.invites_used_this_period - detail.invite_quota_included} over — bills on
                the next QuickBooks invoice)
              </span>
            )}
          </dd>
        </dl>
      </section>

      {notice && (
        <p className="rounded-lg bg-emerald-950/40 px-3 py-2 text-sm text-emerald-300">
          {notice}
        </p>
      )}
      {error && <p className="rounded-lg bg-red-950/40 px-3 py-2 text-sm text-red-300">{error}</p>}

      <section className="rounded-2xl border border-neutral-800 p-5">
        <h2 className="mb-3 text-sm font-medium text-neutral-300">Coach Pro</h2>
        <p className="mb-3 text-xs text-neutral-500">
          All coach billing goes through QuickBooks, not Stripe — there&apos;s no automatic payment
          signal, so activation is manual. Turn this on once payment is confirmed outside the
          app.
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={toggleCoachPro}
          className={`rounded-lg border px-3 py-1.5 text-sm disabled:opacity-50 ${
            detail.is_coach_pro_active
              ? "border-red-800 text-red-300 hover:bg-red-950/60"
              : "border-emerald-700 text-emerald-300 hover:bg-emerald-950/60"
          }`}
        >
          {busy
            ? "..."
            : detail.is_coach_pro_active
              ? "Deactivate Coach Pro"
              : "Activate Coach Pro"}
        </button>
      </section>
    </div>
  );
}

export default function AdminOrganizationDetailPage() {
  return (
    <RequireAuth>
      <RequireAdmin>
        <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12">
          <OrganizationDetailContent />
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
