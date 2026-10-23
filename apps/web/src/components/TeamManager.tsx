"use client";

import { useEffect, useState } from "react";
import { Chip, type ChipTone } from "@/components/Card";
import { ApiError } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth-context";
import type { OrgRole, Team, TeamMember } from "@/lib/types";

const STATUS: Record<TeamMember["status"], { label: string; tone: ChipTone }> = {
  active: { label: "Active", tone: "ok" },
  invited: { label: "Invited", tone: "warn" },
  deactivated: { label: "Deactivated", tone: "neutral" },
};

const inputClass =
  "w-full rounded-xl border border-border-strong bg-surface px-3 py-2.5 text-base outline-none focus:border-accent sm:text-sm";

// The team of coaches in one organization. Used by the Coach Portal's Team page (any coach sees
// it, only an organization admin can change it) and by the admin console's organization page --
// the two differ only in the base path, which both serve with the same shape.
export function TeamManager({ basePath }: { basePath: string }) {
  const { apiFetch } = useAuth();
  const [team, setTeam] = useState<Team | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<OrgRole>("member");
  const [adding, setAdding] = useState(false);

  async function load() {
    try {
      setTeam(await apiFetch<Team>(basePath));
    } catch {
      setError("Could not load the team.");
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basePath]);

  const canManage = team?.my_role === "admin";
  const activeAdmins = team?.members.filter((m) => m.org_role === "admin" && m.is_active).length ?? 0;

  async function run(id: string, action: () => Promise<unknown>, done: string) {
    setBusyId(id);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(done);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusyId(null);
    }
  }

  async function addMember(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    setError(null);
    setNotice(null);
    try {
      await apiFetch(`${basePath}/members`, {
        method: "POST",
        body: { email: email.trim(), display_name: name.trim(), org_role: role },
      });
      setNotice(`Added ${name.trim()}. We emailed ${email.trim()} a link to choose a password.`);
      setName("");
      setEmail("");
      setRole("member");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setAdding(false);
    }
  }

  function patch(member: TeamMember, body: Record<string, unknown>, done: string) {
    return run(
      member.coach_id,
      () => apiFetch(`${basePath}/members/${member.coach_id}`, { method: "PATCH", body }),
      done
    );
  }

  if (team === null) {
    return error ? (
      <p className="text-sm text-danger">{error}</p>
    ) : (
      <p className="text-sm text-text-faint">Loading...</p>
    );
  }

  return (
    <div>
      <p className="mb-4 text-sm text-text-dim">
        {team.members.length === 1 ? "1 coach" : `${team.members.length} coaches`} &middot;{" "}
        {team.invites_used_this_period} of {team.invite_quota_included} Vrotégé invites used this
        year (shared by the whole team)
      </p>

      {notice && (
        <p className="mb-3 rounded-xl bg-accent-faint px-3 py-2 text-sm text-accent">{notice}</p>
      )}
      {error && (
        <p className="mb-3 rounded-xl bg-danger-faint px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <ul className="space-y-2.5">
        {team.members.map((m) => {
          const busy = busyId === m.coach_id;
          const status = STATUS[m.status];
          return (
            <li
              key={m.coach_id}
              className="rounded-2xl border border-border bg-surface-2 px-4 py-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium">
                    {m.display_name}
                    {m.is_me && <span className="ml-1.5 text-xs text-text-faint">(you)</span>}
                  </p>
                  <p className="truncate text-xs text-text-faint">{m.email}</p>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Chip tone={m.org_role === "admin" ? "violet" : "neutral"}>
                    {m.org_role === "admin" ? "Admin" : "Member"}
                  </Chip>
                  <Chip tone={status.tone}>{status.label}</Chip>
                </div>
              </div>
              <p className="mt-1 text-xs text-text-faint">
                {m.singer_count === 1 ? "1 Vrotégé" : `${m.singer_count} Vrotégés`} (each
                coach&apos;s Vrotégés stay private to that coach)
              </p>

              {canManage && (
                <div className="mt-3 flex flex-wrap gap-2 text-sm">
                  {/* An organization always keeps one active admin (the server enforces it too). */}
                  {!(m.org_role === "admin" && m.is_active && activeAdmins <= 1) && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        patch(
                          m,
                          { org_role: m.org_role === "admin" ? "member" : "admin" },
                          `${m.display_name} is now ${m.org_role === "admin" ? "a member" : "an admin"}.`
                        )
                      }
                      className="rounded-lg border border-border-strong px-3 py-1.5 hover:bg-surface disabled:opacity-50"
                    >
                      {m.org_role === "admin" ? "Make member" : "Make admin"}
                    </button>
                  )}
                  {m.status === "invited" && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        run(
                          m.coach_id,
                          () =>
                            apiFetch(`${basePath}/members/${m.coach_id}/resend-welcome`, {
                              method: "POST",
                            }),
                          `Sent ${m.display_name} a new link.`
                        )
                      }
                      className="rounded-lg border border-border-strong px-3 py-1.5 hover:bg-surface disabled:opacity-50"
                    >
                      Resend invite
                    </button>
                  )}
                  {!m.is_me &&
                    (m.is_active ? (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          if (
                            window.confirm(
                              `Deactivate ${m.display_name}? They won't be able to log in until you reactivate them. Their Vrotégés and data are kept.`
                            )
                          ) {
                            void patch(m, { is_active: false }, `${m.display_name} was deactivated.`);
                          }
                        }}
                        className="rounded-lg border border-danger px-3 py-1.5 text-danger hover:bg-danger-faint disabled:opacity-50"
                      >
                        Deactivate
                      </button>
                    ) : (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          patch(m, { is_active: true }, `${m.display_name} was reactivated.`)
                        }
                        className="rounded-lg border border-accent px-3 py-1.5 text-accent hover:bg-accent-faint disabled:opacity-50"
                      >
                        Reactivate
                      </button>
                    ))}
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {canManage ? (
        <form onSubmit={addMember} className="mt-6 rounded-2xl border border-border p-4">
          <h3 className="mb-1 text-sm font-semibold">Add a coach</h3>
          <p className="mb-3 text-xs text-text-faint">
            They get an email with a link to choose their own password. Admins can manage the team;
            members can invite and coach their own Vrotégés.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-text-faint">
              Name
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={`mt-1 ${inputClass}`}
              />
            </label>
            <label className="text-xs text-text-faint">
              Email
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`mt-1 ${inputClass}`}
              />
            </label>
          </div>
          <label className="mt-3 block text-xs text-text-faint">
            Role
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as OrgRole)}
              className={`mt-1 ${inputClass}`}
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={adding}
            className="mt-4 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-ink disabled:opacity-50"
          >
            {adding ? "Adding..." : "Add coach"}
          </button>
        </form>
      ) : (
        <p className="mt-6 text-xs text-text-faint">
          Only an organization admin can add coaches or change roles.
        </p>
      )}
    </div>
  );
}
