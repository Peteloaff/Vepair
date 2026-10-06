"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import type {
  AdminBulkDeleteResult,
  AdminBulkResult,
  AdminSiteSettings,
  AdminUserListItem,
} from "@/lib/types";
import { ApiError, API_BASE } from "@/lib/apiClient";

function RetentionInput({
  label,
  value,
  disabled,
  onCommit,
}: {
  label: string;
  value: number;
  disabled: boolean;
  onCommit: (days: number) => void;
}) {
  // Local draft state, committed on blur rather than every keystroke -- typing "90" over an
  // onChange-triggers-save input would fire a save on "9" and another on "90".
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    // Resyncs the draft when the saved value changes from outside this input (e.g. the
    // initial fetch, or committing the *other* retention field re-fetches the whole
    // settings row) -- not a response to this input's own edits, which stay local until blur.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDraft(String(value));
  }, [value]);

  function commit() {
    const parsed = Math.max(1, Number(draft) || value);
    setDraft(String(parsed));
    if (parsed !== value) onCommit(parsed);
  }

  return (
    <label className="flex items-center gap-2 text-xs text-text-dim">
      {label}
      <input
        type="number"
        min={1}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        disabled={disabled}
        className="w-20 rounded-lg border border-border-strong bg-surface px-2 py-1 text-sm outline-none focus:border-accent disabled:opacity-50"
      />
    </label>
  );
}

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
            ? "border-border bg-surface/40"
            : "border-danger bg-danger-faint"
        }`}
      >
        <div>
          <p className="font-medium">
            New signups are {settings.signups_enabled ? "open" : "locked down"}
          </p>
          <p className="text-xs text-text-dim">
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
              ? "border-danger text-danger hover:bg-danger-faint"
              : "border-accent text-accent hover:bg-accent-faint"
          }`}
        >
          {busy ? "..." : settings.signups_enabled ? "Lock down signups" : "Re-open signups"}
        </button>
      </section>

      <section
        className={`flex items-center justify-between rounded-lg border px-4 py-3 text-sm ${
          settings.nda_required
            ? "border-warning bg-warning-faint"
            : "border-border bg-surface/40"
        }`}
      >
        <div>
          <p className="font-medium">
            Beta NDA is {settings.nda_required ? "required" : "not required"} on login
          </p>
          <p className="text-xs text-text-dim">
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
              ? "border-warning text-warning hover:bg-warning-faint"
              : "border-border-strong text-text-dim hover:bg-surface-2"
          }`}
        >
          {busy ? "..." : settings.nda_required ? "Turn off NDA gate" : "Turn on NDA gate"}
        </button>
      </section>

      <section
        className={`flex items-center justify-between rounded-lg border px-4 py-3 text-sm ${
          settings.public_api_enabled
            ? "border-accent bg-accent-faint"
            : "border-border bg-surface/40"
        }`}
      >
        <div>
          <p className="font-medium">
            Public API is {settings.public_api_enabled ? "on" : "off"}
          </p>
          <p className="text-xs text-text-dim">
            {settings.public_api_enabled
              ? "Personal access tokens (Settings → API access) can pull recovery, vocal range, and exercise data read-only."
              : "Users can still generate personal access tokens, but no token authenticates anything until this is on."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => update({ public_api_enabled: !settings.public_api_enabled })}
          disabled={busy}
          className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${
            settings.public_api_enabled
              ? "border-danger text-danger hover:bg-danger-faint"
              : "border-accent text-accent hover:bg-accent-faint"
          }`}
        >
          {busy ? "..." : settings.public_api_enabled ? "Turn off public API" : "Turn on public API"}
        </button>
      </section>

      <section className="rounded-lg border border-border bg-surface/40 px-4 py-3 text-sm">
        <p className="mb-1 font-medium">Data retention</p>
        <p className="mb-3 text-xs text-text-dim">
          Days to keep raw recording audio (measurements are never purged) and the most
          sensitive check-in free-text fields (illness/reflux/notes), before the daily purge
          job removes them. Changes apply on the job&apos;s next run — see TECHNICAL_GUIDE.md
          §12.
        </p>
        <div className="flex flex-wrap gap-4">
          <RetentionInput
            label="Recording audio (days)"
            value={settings.recording_retention_days}
            disabled={busy}
            onCommit={(days) => update({ recording_retention_days: days })}
          />
          <RetentionInput
            label="Check-in notes (days)"
            value={settings.checkin_notes_retention_days}
            disabled={busy}
            onCommit={(days) => update({ checkin_notes_retention_days: days })}
          />
        </div>
      </section>

      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}

const ACCOUNT_TYPE_OPTIONS = ["singer", "coach"] as const;
// Display-only relabeling -- the stored account_type value stays "singer" (API contract,
// database), only what an admin sees on the button changes.
const ACCOUNT_TYPE_LABEL: Record<(typeof ACCOUNT_TYPE_OPTIONS)[number], string> = {
  singer: "Vrotégé",
  coach: "Coach",
};

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
    <section className="mb-8 rounded-lg border border-border p-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-sm font-medium hover:text-text"
      >
        {open ? "Cancel" : "+ Create user"}
      </button>
      {open && (
        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          {error && <p className="text-sm text-danger">{error}</p>}
          {success && <p className="text-sm text-accent">{success}</p>}
          <div className="flex gap-2">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              className="w-full max-w-sm rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
            <input
              type="text"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password (min 8 characters)"
              className="w-full max-w-sm rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex gap-1 rounded-lg border border-border p-1 text-xs">
              {ACCOUNT_TYPE_OPTIONS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setAccountType(t)}
                  className={`rounded-md px-2.5 py-1.5 ${
                    accountType === t
                      ? "bg-accent text-accent-ink"
                      : "text-text-dim hover:bg-surface-2"
                  }`}
                >
                  {ACCOUNT_TYPE_LABEL[t]}
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
                className="rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
              />
            )}
            <label className="flex items-center gap-2 text-xs text-text-dim">
              <input
                type="checkbox"
                checked={isAdmin}
                onChange={(e) => setIsAdmin(e.target.checked)}
                className="rounded border-border-strong bg-surface"
              />
              Grant admin
            </label>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create account"}
          </button>
        </form>
      )}
    </section>
  );
}

function ExportContactsButton() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function download() {
    setBusy(true);
    setError(null);
    try {
      const token = localStorage.getItem("vepair_access_token");
      const res = await fetch(`${API_BASE}/api/v1/admin/users/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vepair-contacts-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not export the contact list — full admin access is required.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={download}
        disabled={busy}
        className="rounded-lg border border-border-strong px-3 py-1.5 text-xs hover:bg-surface-2 disabled:opacity-50"
      >
        {busy ? "Exporting..." : "Export contact list (CSV)"}
      </button>
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  );
}

type SortColumn = "email" | "account_type" | "is_active" | "onboarding_complete" | "created_at";
type SortDirection = "asc" | "desc";

const DELETE_CONFIRM_PHRASE = "DELETE";

function SortHeader({
  label,
  column,
  sortBy,
  direction,
  onSort,
}: {
  label: string;
  column: SortColumn;
  sortBy: SortColumn;
  direction: SortDirection;
  onSort: (column: SortColumn) => void;
}) {
  const active = sortBy === column;
  return (
    <th
      className="py-2 pr-4"
      aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}
    >
      <button
        type="button"
        onClick={() => onSort(column)}
        className={`inline-flex items-center gap-1 font-medium hover:text-text ${
          active ? "text-text" : ""
        }`}
      >
        {label}
        <span aria-hidden="true" className="w-3 text-xs">
          {active ? (direction === "asc" ? "▲" : "▼") : ""}
        </span>
      </button>
    </th>
  );
}

function AdminUserSearch({ refreshToken }: { refreshToken: number }) {
  const { apiFetch, user: currentUser } = useAuth();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AdminUserListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [sortBy, setSortBy] = useState<SortColumn>("created_at");
  const [direction, setDirection] = useState<SortDirection>("desc");
  const [pendingDelete, setPendingDelete] = useState<string[] | null>(null);
  const [confirmText, setConfirmText] = useState("");

  async function runSearch(
    q: string,
    sort: SortColumn = sortBy,
    dir: SortDirection = direction,
    keepNotice = false
  ) {
    setLoading(true);
    setError(null);
    if (!keepNotice) setNotice(null);
    try {
      const rows = await apiFetch<AdminUserListItem[]>("/api/v1/admin/users", {
        searchParams: { ...(q ? { query: q } : {}), sort_by: sort, direction: dir },
      });
      setResults(rows);
      setSelected(new Set());
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

  function changeSort(column: SortColumn) {
    // A new column starts in its natural order (A-Z, oldest signup last); the same column
    // flips direction.
    const nextDirection: SortDirection =
      column === sortBy ? (direction === "asc" ? "desc" : "asc") : column === "created_at" ? "desc" : "asc";
    setSortBy(column);
    setDirection(nextDirection);
    void runSearch(query, column, nextDirection);
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    const selectable = (results ?? []).filter((u) => u.id !== currentUser?.id).map((u) => u.id);
    setSelected((prev) => (prev.size === selectable.length ? new Set() : new Set(selectable)));
  }

  async function runBulk(action: "bulk-deactivate" | "bulk-reactivate", ids: string[]) {
    if (ids.length === 0) return;
    const emails = (results ?? [])
      .filter((u) => ids.includes(u.id))
      .map((u) => u.email)
      .join(", ");
    const verb = action === "bulk-deactivate" ? "Deactivate" : "Reactivate";
    if (!window.confirm(`${verb} ${ids.length} account(s)? ${emails}`)) return;
    setBulkBusy(true);
    setError(null);
    try {
      await apiFetch<AdminBulkResult>(`/api/v1/admin/users/${action}`, {
        method: "POST",
        body: { user_ids: ids },
      });
      await runSearch(query, sortBy, direction);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBulkBusy(false);
    }
  }

  async function runDelete(ids: string[]) {
    setBulkBusy(true);
    setError(null);
    try {
      const result = await apiFetch<AdminBulkDeleteResult>("/api/v1/admin/users/bulk-delete", {
        method: "POST",
        body: { user_ids: ids },
      });
      const parts = [`Permanently deleted ${result.deleted.length} account(s).`];
      if (result.skipped_active.length > 0) {
        parts.push(`${result.skipped_active.length} still active, so left alone.`);
      }
      setPendingDelete(null);
      setConfirmText("");
      await runSearch(query, sortBy, direction, true);
      setNotice(parts.join(" "));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBulkBusy(false);
    }
  }

  const selectedRows = (results ?? []).filter((u) => selected.has(u.id));
  const deleteRows = (results ?? []).filter((u) => pendingDelete?.includes(u.id));
  const deleteBlockedCount = deleteRows.filter((u) => u.is_active).length;
  const selectableCount = (results ?? []).filter((u) => u.id !== currentUser?.id).length;
  const rowButton =
    "rounded-lg border px-2.5 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            runSearch(query);
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by email..."
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
        <ExportContactsButton />
      </div>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {notice && <p className="mb-4 text-sm text-accent">{notice}</p>}

      {pendingDelete && (
        <div className="mb-4 space-y-3 rounded-2xl border border-danger/60 bg-danger-faint p-4">
          <h2 className="text-sm font-medium text-danger">
            Permanently delete {pendingDelete.length} account(s)?
          </h2>
          <p className="text-xs text-text-dim">
            This deletes each account, every recording (the audio files too), and everything
            derived from them. It cannot be undone. Only deactivated accounts are deleted.
          </p>
          <ul className="max-h-32 list-disc overflow-y-auto pl-5 text-xs text-text-dim">
            {deleteRows.map((u) => (
              <li key={u.id}>
                {u.email}
                {u.is_active && <span className="ml-2 text-warning">(still active, will be skipped)</span>}
              </li>
            ))}
          </ul>
          {deleteBlockedCount === deleteRows.length ? (
            <p className="text-xs text-warning">
              Deactivate these accounts first, then delete them.
            </p>
          ) : (
            <div>
              <label htmlFor="admin-bulk-delete-confirm" className="mb-1 block text-xs text-text-dim">
                Type <span className="font-mono text-danger">{DELETE_CONFIRM_PHRASE}</span> to confirm
              </label>
              <input
                id="admin-bulk-delete-confirm"
                type="text"
                autoComplete="off"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                className="w-full max-w-xs rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-danger"
              />
            </div>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={
                bulkBusy ||
                deleteBlockedCount === deleteRows.length ||
                confirmText !== DELETE_CONFIRM_PHRASE
              }
              onClick={() => runDelete(pendingDelete)}
              className="rounded-lg bg-danger px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {bulkBusy ? "Deleting..." : "Permanently delete"}
            </button>
            <button
              type="button"
              disabled={bulkBusy}
              onClick={() => {
                setPendingDelete(null);
                setConfirmText("");
              }}
              className="rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {selected.size > 0 && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border-strong bg-surface px-3 py-2">
          <p className="text-xs text-text-dim">{selected.size} selected</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={bulkBusy}
              onClick={() => runBulk("bulk-deactivate", Array.from(selected))}
              className="rounded-lg border border-danger px-3 py-1 text-xs text-danger hover:bg-danger-faint disabled:opacity-50"
            >
              Deactivate selected
            </button>
            <button
              type="button"
              disabled={bulkBusy}
              onClick={() => runBulk("bulk-reactivate", Array.from(selected))}
              className="rounded-lg border border-border-strong px-3 py-1 text-xs hover:bg-surface-2 disabled:opacity-50"
            >
              Reactivate selected
            </button>
            <button
              type="button"
              disabled={bulkBusy || selectedRows.every((u) => u.is_active)}
              title={
                selectedRows.every((u) => u.is_active)
                  ? "Deactivate accounts first — only deactivated accounts can be deleted"
                  : undefined
              }
              onClick={() => {
                setConfirmText("");
                setPendingDelete(Array.from(selected));
              }}
              className="rounded-lg border border-danger px-3 py-1 text-xs text-danger hover:bg-danger-faint disabled:cursor-not-allowed disabled:opacity-40"
            >
              Delete selected
            </button>
          </div>
        </div>
      )}

      {results === null ? (
        <p className="text-sm text-text-faint">
          Enter an email substring, or search with an empty query to list the most recent 100
          signups.
        </p>
      ) : results.length === 0 ? (
        <p className="text-sm text-text-faint">No matching accounts.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left text-text-dim">
                <th className="w-8 py-2 pr-2">
                  <input
                    type="checkbox"
                    aria-label="Select all"
                    checked={selectableCount > 0 && selected.size === selectableCount}
                    onChange={toggleAll}
                    className="rounded border-border-strong bg-surface"
                  />
                </th>
                <SortHeader label="Email" column="email" sortBy={sortBy} direction={direction} onSort={changeSort} />
                <SortHeader label="Type" column="account_type" sortBy={sortBy} direction={direction} onSort={changeSort} />
                <SortHeader label="Status" column="is_active" sortBy={sortBy} direction={direction} onSort={changeSort} />
                <SortHeader label="Onboarded" column="onboarding_complete" sortBy={sortBy} direction={direction} onSort={changeSort} />
                <SortHeader label="Signed up" column="created_at" sortBy={sortBy} direction={direction} onSort={changeSort} />
                <th className="py-2 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {results.map((u) => {
                const isSelf = u.id === currentUser?.id;
                return (
                  <tr key={u.id} className="border-b border-border">
                    <td className="py-2 pr-2">
                      <input
                        type="checkbox"
                        aria-label={`Select ${u.email}`}
                        checked={selected.has(u.id)}
                        disabled={isSelf}
                        onChange={() => toggle(u.id)}
                        className="rounded border-border-strong bg-surface"
                      />
                    </td>
                    <td className="py-2 pr-4">
                      <Link href={`/admin/users/${u.id}`} className="underline hover:text-text">
                        {u.email}
                      </Link>
                      {u.is_admin && (
                        <span className="ml-2 text-xs text-warning">
                          (admin{u.admin_role === "support" ? " · support" : ""})
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-4">{ACCOUNT_TYPE_LABEL[u.account_type]}</td>
                    <td className="py-2 pr-4">
                      {u.is_active ? "active" : <span className="text-danger">deactivated</span>}
                    </td>
                    <td className="py-2 pr-4">{u.onboarding_complete ? "yes" : "no"}</td>
                    <td className="py-2 pr-4">{new Date(u.created_at).toLocaleDateString()}</td>
                    <td className="py-2">
                      <div className="flex justify-end gap-2">
                        {u.is_active ? (
                          <button
                            type="button"
                            disabled={bulkBusy || isSelf}
                            title={isSelf ? "You can't deactivate your own account" : undefined}
                            onClick={() => runBulk("bulk-deactivate", [u.id])}
                            className={`${rowButton} border-border-strong hover:bg-surface-2`}
                          >
                            Deactivate
                          </button>
                        ) : (
                          <button
                            type="button"
                            disabled={bulkBusy}
                            onClick={() => runBulk("bulk-reactivate", [u.id])}
                            className={`${rowButton} border-border-strong hover:bg-surface-2`}
                          >
                            Reactivate
                          </button>
                        )}
                        <button
                          type="button"
                          disabled={bulkBusy || isSelf || u.is_active}
                          title={
                            isSelf
                              ? "You can't delete your own account"
                              : u.is_active
                                ? "Deactivate the account first"
                                : undefined
                          }
                          onClick={() => {
                            setConfirmText("");
                            setPendingDelete([u.id]);
                          }}
                          className={`${rowButton} border-danger text-danger hover:bg-danger-faint`}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function AdminPage() {
  const [refreshToken, setRefreshToken] = useState(0);

  return (
    <RequireAuth>
      <RequireAdmin>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-12 sm:px-6">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="mb-1 text-2xl font-semibold tracking-tight">Admin</h1>
              <p className="text-sm text-text-dim">Search and manage user accounts.</p>
            </div>
            <div className="flex gap-4">
              <Link href="/user-guide" className="text-sm underline hover:text-text">
                User guide
              </Link>
              <Link
                href="/technical-reference"
                className="text-sm underline hover:text-text"
              >
                Technical reference
              </Link>
              <Link
                href="/admin/organizations"
                className="text-sm underline hover:text-text"
              >
                Organizations
              </Link>
              <Link href="/admin/reports" className="text-sm underline hover:text-text">
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
