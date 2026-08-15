"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type { AdminUserDetail } from "@/lib/types";
import { ApiError } from "@/lib/apiClient";

const CONFIRM_PHRASE = "DELETE";

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function UserDetailContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ userId: string }>();
  const [detail, setDetail] = useState<AdminUserDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [newCoachName, setNewCoachName] = useState("");

  function load() {
    apiFetch<AdminUserDetail>(`/api/v1/admin/users/${params.userId}`)
      .then(setDetail)
      .catch(() => setError("Could not load this account."));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.userId]);

  async function runAction(action: () => Promise<void>, successMessage: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(successMessage);
      load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Something went wrong. Please try again."
      );
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
        <Link href="/admin" className="text-sm underline hover:text-neutral-200">
          ← Back to search
        </Link>
      </div>

      <section className="rounded-2xl border border-neutral-800 p-5">
        <h1 className="mb-1 text-xl font-semibold">{detail.email}</h1>
        <p className="mb-4 text-sm text-neutral-400">
          {detail.account_type} · {detail.is_active ? "active" : "deactivated"}
          {detail.is_admin ? " · admin" : ""}
        </p>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <dt className="text-neutral-500">Signed up</dt>
          <dd>{formatDate(detail.created_at)}</dd>
          <dt className="text-neutral-500">Onboarding complete</dt>
          <dd>{detail.onboarding_complete ? "yes" : "no"}</dd>
          <dt className="text-neutral-500">Last session issued</dt>
          <dd>{formatDate(detail.last_session_at)}</dd>
          <dt className="text-neutral-500">Last check-in</dt>
          <dd>{detail.last_checkin_date ?? "—"}</dd>
          <dt className="text-neutral-500">Last recording</dt>
          <dd>{formatDate(detail.last_recording_at)}</dd>
        </dl>
      </section>

      {notice && (
        <p className="rounded-lg bg-emerald-950/40 px-3 py-2 text-sm text-emerald-300">
          {notice}
        </p>
      )}
      {error && <p className="rounded-lg bg-red-950/40 px-3 py-2 text-sm text-red-300">{error}</p>}

      <section className="rounded-2xl border border-neutral-800 p-5">
        <h2 className="mb-3 text-sm font-medium text-neutral-300">Roles</h2>
        <div className="flex flex-wrap items-start gap-4">
          <div>
            <p className="mb-1.5 text-xs text-neutral-500">Admin</p>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                runAction(
                  () =>
                    apiFetch(`/api/v1/admin/users/${detail.id}/set-admin`, {
                      method: "POST",
                      body: { is_admin: !detail.is_admin },
                    }),
                  detail.is_admin ? "Admin access revoked." : "Admin access granted."
                )
              }
              className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-50"
            >
              {detail.is_admin ? "Revoke admin" : "Grant admin"}
            </button>
          </div>

          <div>
            <p className="mb-1.5 text-xs text-neutral-500">Coach</p>
            {detail.account_type === "coach" ? (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  if (
                    !window.confirm(
                      "Remove coach status? This deletes any exercises this account authored — including from every other singer's routine that included one. This cannot be undone."
                    )
                  ) {
                    return;
                  }
                  runAction(
                    () =>
                      apiFetch(`/api/v1/admin/users/${detail.id}/set-coach`, {
                        method: "POST",
                        body: { is_coach: false },
                      }),
                    "Coach status removed."
                  );
                }}
                className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-50"
              >
                Remove coach
              </button>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Display name"
                  value={newCoachName}
                  onChange={(e) => setNewCoachName(e.target.value)}
                  className="w-40 rounded-lg border border-neutral-700 bg-neutral-900 px-2.5 py-1.5 text-sm outline-none focus:border-neutral-500"
                />
                <button
                  type="button"
                  disabled={busy || newCoachName.trim().length === 0}
                  onClick={() =>
                    runAction(
                      () =>
                        apiFetch(`/api/v1/admin/users/${detail.id}/set-coach`, {
                          method: "POST",
                          body: { is_coach: true, display_name: newCoachName.trim() },
                        }),
                      "Coach access granted."
                    ).then(() => setNewCoachName(""))
                  }
                  className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Make coach
                </button>
              </div>
            )}
          </div>
        </div>
        <p className="mt-3 text-xs text-neutral-500">
          Making a singer account a coach doesn&apos;t remove their singer data — the account
          keeps both.
        </p>
      </section>

      <section className="rounded-2xl border border-neutral-800 p-5">
        <h2 className="mb-3 text-sm font-medium text-neutral-300">Account actions</h2>
        <div className="flex flex-wrap gap-2">
          {detail.is_active ? (
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                runAction(
                  () =>
                    apiFetch(`/api/v1/admin/users/${detail.id}/deactivate`, { method: "POST" }),
                  "Account deactivated. All sessions were revoked."
                )
              }
              className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-50"
            >
              Deactivate
            </button>
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                runAction(
                  () =>
                    apiFetch(`/api/v1/admin/users/${detail.id}/reactivate`, { method: "POST" }),
                  "Account reactivated."
                )
              }
              className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-50"
            >
              Reactivate
            </button>
          )}

          <button
            type="button"
            disabled={busy}
            onClick={() =>
              runAction(
                () =>
                  apiFetch(`/api/v1/admin/users/${detail.id}/send-password-reset`, {
                    method: "POST",
                  }),
                "Password reset email sent."
              )
            }
            className="rounded-lg border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-800 disabled:opacity-50"
          >
            Send password reset
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-red-900/60 bg-red-950/10 p-5">
        <h2 className="mb-1 text-sm font-medium text-red-300">Permanently delete account</h2>
        <p className="mb-4 text-xs text-neutral-400">
          Deletes this account, every recording (the actual audio files, not just the database
          record), and everything derived from them. This cannot be undone. The account must
          already be deactivated first.
        </p>

        {!showDeleteConfirm ? (
          <button
            type="button"
            disabled={detail.is_active}
            onClick={() => setShowDeleteConfirm(true)}
            title={detail.is_active ? "Deactivate the account first" : undefined}
            className="rounded-lg border border-red-800 px-3 py-1.5 text-sm text-red-300 hover:bg-red-950/40 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Delete this account
          </button>
        ) : (
          <div className="space-y-3">
            <div>
              <label htmlFor="admin-delete-confirm" className="mb-1 block text-xs text-neutral-400">
                Type <span className="font-mono text-red-300">{CONFIRM_PHRASE}</span> to confirm
              </label>
              <input
                id="admin-delete-confirm"
                type="text"
                autoComplete="off"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className="w-full max-w-xs rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-red-600"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={busy || confirmText !== CONFIRM_PHRASE}
                onClick={() =>
                  runAction(
                    () => apiFetch(`/api/v1/admin/users/${detail.id}/delete`, { method: "POST" }),
                    "Account permanently deleted."
                  ).then(() => {
                    setShowDeleteConfirm(false);
                    setConfirmText("");
                  })
                }
                className="rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? "Deleting..." : "Permanently delete"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setConfirmText("");
                }}
                disabled={busy}
                className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default function AdminUserDetailPage() {
  return (
    <RequireAuth>
      <RequireAdmin>
        <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12">
          <UserDetailContent />
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
