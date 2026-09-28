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
// Display-only relabeling -- the stored account_type value stays "singer" (API contract,
// database), only what an admin sees changes.
const ACCOUNT_TYPE_LABEL: Record<"singer" | "coach", string> = {
  singer: "Vrotégé",
  coach: "Coach",
};

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
  const [newPassword, setNewPassword] = useState("");

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
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (!detail) {
    return <p className="text-sm text-text-faint">Loading...</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/admin" className="text-sm underline hover:text-text">
          ← Back to search
        </Link>
      </div>

      <section className="rounded-2xl border border-border p-5">
        <h1 className="mb-1 text-xl font-semibold">{detail.email}</h1>
        <p className="mb-4 text-sm text-text-dim">
          {ACCOUNT_TYPE_LABEL[detail.account_type]} · {detail.is_active ? "active" : "deactivated"}
          {detail.is_admin ? ` · admin (${detail.admin_role ?? "full"})` : ""}
        </p>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <dt className="text-text-faint">Signed up</dt>
          <dd>{formatDate(detail.created_at)}</dd>
          <dt className="text-text-faint">Onboarding complete</dt>
          <dd>{detail.onboarding_complete ? "yes" : "no"}</dd>
          <dt className="text-text-faint">Last session issued</dt>
          <dd>{formatDate(detail.last_session_at)}</dd>
          <dt className="text-text-faint">Last check-in</dt>
          <dd>{detail.last_checkin_date ?? "—"}</dd>
          <dt className="text-text-faint">Last recording</dt>
          <dd>{formatDate(detail.last_recording_at)}</dd>
        </dl>
      </section>

      {notice && (
        <p className="rounded-lg bg-accent-faint px-3 py-2 text-sm text-accent">
          {notice}
        </p>
      )}
      {error && <p className="rounded-lg bg-danger-faint px-3 py-2 text-sm text-danger">{error}</p>}

      <section className="rounded-2xl border border-border p-5">
        <h2 className="mb-3 text-sm font-medium text-text-dim">Roles</h2>
        <div className="flex flex-wrap items-start gap-4">
          <div>
            <p className="mb-1.5 text-xs text-text-faint">Admin</p>
            <div className="flex items-center gap-2">
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
                className="rounded-lg border border-border-strong px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50"
              >
                {detail.is_admin ? "Revoke admin" : "Grant admin"}
              </button>
              {detail.is_admin && (
                <select
                  value={detail.admin_role ?? "full"}
                  disabled={busy}
                  onChange={(e) =>
                    runAction(
                      () =>
                        apiFetch(`/api/v1/admin/users/${detail.id}/set-admin`, {
                          method: "POST",
                          body: { is_admin: true, admin_role: e.target.value },
                        }),
                      `Tier set to ${e.target.value}.`
                    )
                  }
                  className="rounded-lg border border-border-strong bg-surface px-2.5 py-1.5 text-sm outline-none focus:border-accent disabled:opacity-50"
                >
                  <option value="full">Full</option>
                  <option value="support">Support</option>
                </select>
              )}
            </div>
            <p className="mt-1.5 text-xs text-text-faint">
              Support can view accounts, deactivate/reactivate, and send password resets —
              never hard-delete, grant admin, set-coach, or site settings.
            </p>
          </div>

          <div>
            <p className="mb-1.5 text-xs text-text-faint">Coach</p>
            {detail.account_type === "coach" ? (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  if (
                    !window.confirm(
                      "Remove coach status? This deletes any exercises this account authored — including from every other Vrotégé's routine that included one. This cannot be undone."
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
                className="rounded-lg border border-border-strong px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50"
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
                  className="w-40 rounded-lg border border-border-strong bg-surface px-2.5 py-1.5 text-sm outline-none focus:border-accent"
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
                  className="rounded-lg border border-border-strong px-3 py-1.5 text-sm hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Make coach
                </button>
              </div>
            )}
          </div>
        </div>
        <p className="mt-3 text-xs text-text-faint">
          Making a Vrotégé account a coach doesn&apos;t remove their Vrotégé data — the account
          keeps both.
        </p>
      </section>

      <section className="rounded-2xl border border-border p-5">
        <h2 className="mb-3 text-sm font-medium text-text-dim">Account actions</h2>
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
              className="rounded-lg border border-border-strong px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50"
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
              className="rounded-lg border border-border-strong px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50"
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
            className="rounded-lg border border-border-strong px-3 py-1.5 text-sm hover:bg-surface-2 disabled:opacity-50"
          >
            Send password reset
          </button>

          <Link
            href={`/admin/users/${detail.id}/view-as`}
            className="rounded-lg border border-warning px-3 py-1.5 text-sm text-warning hover:bg-warning-faint"
          >
            View as this user
          </Link>
        </div>

        <div className="mt-4 border-t border-border pt-4">
          <p className="mb-1.5 text-xs text-text-faint">
            Or set a new password directly — takes effect immediately, no email required. Every
            existing session for this account is signed out.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="New password (min 8 characters)"
              autoComplete="off"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full max-w-xs rounded-lg border border-border-strong bg-surface px-2.5 py-1.5 text-sm outline-none focus:border-accent"
            />
            <button
              type="button"
              disabled={busy || newPassword.length < 8}
              onClick={() =>
                runAction(
                  () =>
                    apiFetch(`/api/v1/admin/users/${detail.id}/set-password`, {
                      method: "POST",
                      body: { new_password: newPassword },
                    }),
                  "Password updated. Every existing session was signed out."
                ).then(() => setNewPassword(""))
              }
              className="shrink-0 rounded-lg border border-border-strong px-3 py-1.5 text-sm hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Set password
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-danger/60 bg-danger-faint p-5">
        <h2 className="mb-1 text-sm font-medium text-danger">Permanently delete account</h2>
        <p className="mb-4 text-xs text-text-dim">
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
            className="rounded-lg border border-danger px-3 py-1.5 text-sm text-danger hover:bg-danger-faint disabled:cursor-not-allowed disabled:opacity-50"
          >
            Delete this account
          </button>
        ) : (
          <div className="space-y-3">
            <div>
              <label htmlFor="admin-delete-confirm" className="mb-1 block text-xs text-text-dim">
                Type <span className="font-mono text-danger">{CONFIRM_PHRASE}</span> to confirm
              </label>
              <input
                id="admin-delete-confirm"
                type="text"
                autoComplete="off"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className="w-full max-w-xs rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-danger"
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
                className="rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white hover:bg-danger disabled:cursor-not-allowed disabled:opacity-50"
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
                className="rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2 disabled:opacity-50"
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
