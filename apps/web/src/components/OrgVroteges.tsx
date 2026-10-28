"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth-context";
import type { OrgVroteges as OrgVrotegesData, Team } from "@/lib/types";

const inputClass =
  "w-full rounded-xl border border-border-strong bg-surface px-3 py-2.5 text-base outline-none focus:border-accent sm:text-sm";

// For organization admins: who is connected to which coach on the team, and the three things an
// admin can do about it -- invite a Vrotégé on behalf of a coach, end a connection, or move a
// Vrotégé to another coach. An admin only ever sees an identifier and a date here, never any of a
// Vrotégé's voice data, and every new connection still needs the Vrotégé to accept.
export function OrgVroteges() {
  const { apiFetch } = useAuth();
  const [team, setTeam] = useState<Team | null>(null);
  const [data, setData] = useState<OrgVrotegesData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [inviteCoach, setInviteCoach] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteMessage, setInviteMessage] = useState("");
  const [moveTarget, setMoveTarget] = useState<Record<string, string>>({});

  async function load() {
    try {
      const [t, v] = await Promise.all([
        apiFetch<Team>("/api/v1/coach/team"),
        apiFetch<OrgVrotegesData>("/api/v1/coach/team/vroteges"),
      ]);
      setTeam(t);
      setData(v);
    } catch {
      // A member (not an admin) gets a 403 here and simply never sees this section.
      setTeam(null);
      setData(null);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!team || !data || team.my_role !== "admin") return null;

  const coaches = team.members.filter((m) => m.is_active);

  async function act(id: string, action: () => Promise<unknown>, done: string) {
    setBusy(id);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(done);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  }

  async function sendInvite(e: React.FormEvent) {
    e.preventDefault();
    const coachId = inviteCoach || coaches[0]?.coach_id;
    if (!coachId) return;
    await act(
      "invite",
      async () => {
        await apiFetch("/api/v1/coach/team/vroteges/invite", {
          method: "POST",
          body: {
            coach_id: coachId,
            singer_email: inviteEmail.trim(),
            message: inviteMessage.trim() || null,
          },
        });
        setInviteEmail("");
        setInviteMessage("");
      },
      `Invite sent to ${inviteEmail.trim()}. Nothing is shared until they accept.`
    );
  }

  const byCoach = coaches.map((c) => ({
    coach: c,
    connections: data.connections.filter((x) => x.coach_id === c.coach_id),
  }));

  return (
    <section className="mt-10 border-t border-border pt-8">
      <h2 className="mb-1 text-xl font-semibold tracking-tight">Vrotégés in your organization</h2>
      <p className="mb-5 text-sm text-text-dim">
        As an admin you can see who is connected to which coach, invite someone on a coach&apos;s
        behalf, move a Vrotégé to another coach, or end a connection. You never see any of a
        Vrotégé&apos;s voice data: that stays between them and the coach they chose, and every
        new connection needs the Vrotégé to accept.
      </p>

      {notice && (
        <p className="mb-3 rounded-xl bg-accent-faint px-3 py-2 text-sm text-accent">{notice}</p>
      )}
      {error && (
        <p className="mb-3 rounded-xl bg-danger-faint px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <form onSubmit={sendInvite} className="mb-6 rounded-2xl border border-border p-4">
        <h3 className="mb-3 text-sm font-semibold">Invite a Vrotégé for a coach</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-xs text-text-faint">
            Coach
            <select
              value={inviteCoach || coaches[0]?.coach_id || ""}
              onChange={(e) => setInviteCoach(e.target.value)}
              className={`mt-1 ${inputClass}`}
            >
              {coaches.map((c) => (
                <option key={c.coach_id} value={c.coach_id}>
                  {c.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-text-faint">
            Vrotégé&apos;s email
            <input
              required
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className={`mt-1 ${inputClass}`}
            />
          </label>
        </div>
        <label className="mt-3 block text-xs text-text-faint">
          Message (optional)
          <input
            value={inviteMessage}
            maxLength={1000}
            onChange={(e) => setInviteMessage(e.target.value)}
            className={`mt-1 ${inputClass}`}
          />
        </label>
        <button
          type="submit"
          disabled={busy === "invite"}
          className="mt-4 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-ink disabled:opacity-50"
        >
          {busy === "invite" ? "Sending..." : "Send invite"}
        </button>
        <p className="mt-2 text-xs text-text-faint">
          It uses the team&apos;s shared invite allowance and comes from the coach you pick.
        </p>
      </form>

      <div className="space-y-4">
        {byCoach.map(({ coach, connections }) => (
          <div key={coach.coach_id} className="rounded-2xl border border-border bg-surface-2 p-4">
            <p className="mb-2 font-medium">
              {coach.display_name}{" "}
              <span className="text-xs font-normal text-text-faint">
                &middot; {connections.length} {connections.length === 1 ? "Vrotégé" : "Vrotégés"}
              </span>
            </p>
            {connections.length === 0 ? (
              <p className="text-xs text-text-faint">No connected Vrotégés.</p>
            ) : (
              <ul className="space-y-2">
                {connections.map((c) => {
                  const others = coaches.filter((o) => o.coach_id !== coach.coach_id);
                  const target = moveTarget[c.access_id] ?? others[0]?.coach_id ?? "";
                  return (
                    <li
                      key={c.access_id}
                      className="rounded-xl border border-border bg-surface px-3 py-2.5"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="min-w-0">
                          <span className="block text-sm">{c.singer_label}</span>
                          {c.singer_label !== c.singer_email && (
                            <span className="block truncate text-xs text-text-faint">
                              {c.singer_email}
                            </span>
                          )}
                          {c.connected_since && (
                            <span className="block text-xs text-text-faint">
                              Connected {new Date(c.connected_since).toLocaleDateString()}
                            </span>
                          )}
                        </span>
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          {others.length > 0 && (
                            <>
                              <select
                                aria-label={`Move ${c.singer_label} to`}
                                value={target}
                                onChange={(e) =>
                                  setMoveTarget((prev) => ({ ...prev, [c.access_id]: e.target.value }))
                                }
                                className="rounded-lg border border-border-strong bg-surface px-2 py-1.5 text-base sm:text-sm"
                              >
                                {others.map((o) => (
                                  <option key={o.coach_id} value={o.coach_id}>
                                    {o.display_name}
                                  </option>
                                ))}
                              </select>
                              <button
                                type="button"
                                disabled={busy === c.access_id}
                                onClick={() => {
                                  if (
                                    window.confirm(
                                      `Move ${c.singer_label} to another coach? ${coach.display_name} loses access right away. The new coach sees nothing until ${c.singer_label} accepts their invite.`
                                    )
                                  ) {
                                    void act(
                                      c.access_id,
                                      () =>
                                        apiFetch(
                                          `/api/v1/coach/team/vroteges/${c.access_id}/move`,
                                          { method: "POST", body: { coach_id: target } }
                                        ),
                                      `${c.singer_label} was invited to their new coach.`
                                    );
                                  }
                                }}
                                className="rounded-lg border border-border-strong px-3 py-1.5 hover:bg-surface-2 disabled:opacity-50"
                              >
                                Move
                              </button>
                            </>
                          )}
                          <button
                            type="button"
                            disabled={busy === c.access_id}
                            onClick={() => {
                              if (
                                window.confirm(
                                  `End ${c.singer_label}'s connection to ${coach.display_name}? The coach loses access right away. Nothing is deleted, and ${c.singer_label} keeps their own account and data.`
                                )
                              ) {
                                void act(
                                  c.access_id,
                                  () =>
                                    apiFetch(`/api/v1/coach/team/vroteges/${c.access_id}`, {
                                      method: "DELETE",
                                    }),
                                  `${c.singer_label}'s connection was ended.`
                                );
                              }
                            }}
                            className="rounded-lg border border-danger px-3 py-1.5 text-danger hover:bg-danger-faint disabled:opacity-50"
                          >
                            End connection
                          </button>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        ))}
      </div>

      {data.pending_invites.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-2 text-sm font-semibold">Waiting for a reply</h3>
          <ul className="space-y-2">
            {data.pending_invites.map((p) => (
              <li
                key={p.invite_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border px-3 py-2.5 text-sm"
              >
                <span>
                  {p.singer_email}{" "}
                  <span className="text-xs text-text-faint">
                    &middot; invited by {p.coach_name} on {new Date(p.sent_at).toLocaleDateString()}
                  </span>
                </span>
                <button
                  type="button"
                  disabled={busy === p.invite_id}
                  onClick={() =>
                    void act(
                      p.invite_id,
                      () =>
                        apiFetch(`/api/v1/coach/team/vroteges/invites/${p.invite_id}`, {
                          method: "DELETE",
                        }),
                      "Invite cancelled."
                    )
                  }
                  className="rounded-lg border border-border-strong px-3 py-1.5 hover:bg-surface-2 disabled:opacity-50"
                >
                  Cancel invite
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
