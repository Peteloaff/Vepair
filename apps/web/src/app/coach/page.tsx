"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { useAuth } from "@/lib/auth-context";
import type { CoachProfile, CoachSentInvite, CoachSingerListItem } from "@/lib/types";

const STATUS_LABEL: Record<CoachSentInvite["status"], string> = {
  pending: "Pending",
  accepted: "Accepted",
  declined: "Declined",
  revoked: "Cancelled",
};

function CoachDashboardContent() {
  const { apiFetch, user, logout } = useAuth();
  const [profile, setProfile] = useState<CoachProfile | null>(null);
  const [singers, setSingers] = useState<CoachSingerListItem[] | null>(null);
  const [invites, setInvites] = useState<CoachSentInvite[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [profileData, singersData, invitesData] = await Promise.all([
        apiFetch<CoachProfile>("/api/v1/coach/profile"),
        apiFetch<CoachSingerListItem[]>("/api/v1/coach/singers"),
        apiFetch<CoachSentInvite[]>("/api/v1/coach/invites"),
      ]);
      setProfile(profileData);
      setSingers(singersData);
      setInvites(invitesData);
    } catch {
      setError("Could not load your coach dashboard.");
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function cancelInvite(inviteId: string) {
    await apiFetch(`/api/v1/coach/invites/${inviteId}`, { method: "DELETE" });
    void load();
  }

  if (error) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (profile === null || singers === null || invites === null) {
    return <p className="text-sm text-text-faint">Loading...</p>;
  }

  const pendingInvites = invites.filter((i) => i.status === "pending");

  return (
    <div className="mx-auto w-full max-w-2xl">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {profile.display_name}
            {profile.studio_name && (
              <span className="text-text-faint"> &middot; {profile.studio_name}</span>
            )}
          </h1>
          <p className="mt-1 text-sm text-text-dim">{user?.email}</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/coach/invite"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong"
          >
            Invite a Vrotégé
          </Link>
          <button
            type="button"
            onClick={() => logout()}
            className="rounded-lg border border-border-strong px-4 py-2 text-sm hover:bg-surface-2"
          >
            Log out
          </button>
        </div>
      </div>

      <section className="mb-8">
        <h2 className="mb-3 text-sm font-medium text-text">Your Vrotégés</h2>
        {singers.length === 0 ? (
          <p className="text-sm text-text-faint">
            No Vrotégés yet — invite one to get started.
          </p>
        ) : (
          <div className="space-y-2">
            {singers.map((singer) => (
              <Link
                key={singer.coach_access_id}
                href={`/coach/singers/${singer.singer_user_id}`}
                className="flex items-center justify-between rounded-xl border border-border bg-surface/60 p-4 hover:bg-surface"
              >
                <div>
                  <p className="text-sm font-medium text-text">{singer.singer_email}</p>
                  <p className="mt-1 text-xs text-text-faint">
                    Shared: {singer.granted_categories.join(", ") || "nothing yet"}
                  </p>
                </div>
                {singer.unread_message_count > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent px-1 text-xs font-semibold text-accent-ink">
                    {singer.unread_message_count}
                  </span>
                )}
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium text-text">Invites sent</h2>
        {pendingInvites.length === 0 ? (
          <p className="text-sm text-text-faint">No pending invites.</p>
        ) : (
          <div className="space-y-2">
            {pendingInvites.map((invite) => (
              <div
                key={invite.id}
                className="flex items-center justify-between rounded-xl border border-border bg-surface/60 p-4"
              >
                <div>
                  <p className="text-sm text-text">{invite.singer_email}</p>
                  <p className="text-xs text-text-faint">{STATUS_LABEL[invite.status]}</p>
                </div>
                <button
                  type="button"
                  onClick={() => cancelInvite(invite.id)}
                  className="text-xs text-text-faint hover:text-danger"
                >
                  Cancel
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default function CoachDashboardPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-6 py-10">
          <CoachDashboardContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
