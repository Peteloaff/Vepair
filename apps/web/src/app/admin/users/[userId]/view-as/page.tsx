"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireAdmin } from "@/components/RequireAdmin";
import { useAuth } from "@/lib/auth-context";
import { API_BASE } from "@/lib/apiClient";
import type { AdminImpersonateResponse, CheckIn, Profile } from "@/lib/types";

/** Everything here uses a raw `fetch` with the impersonation token directly -- deliberately
 * never touching AuthContext's accessTokenRef/refreshTokenRef. Reusing the shared apiFetch
 * would mean an expired 15-minute impersonation token falls into apiFetch's normal
 * refresh-on-401 flow, which would silently mint a fresh token for the *admin's own* identity
 * (using the admin's real refresh token, still sitting in the ref) while this page keeps
 * showing "Viewing as..." — an admin session quietly re-escalating without the banner ever
 * indicating it. Keeping impersonation state fully isolated in this component removes that
 * failure mode entirely: if the token expires, requests just start failing and the page says
 * so, with an explicit re-impersonate rather than any silent fallback. */
async function impersonatedFetch<T>(token: string, path: string): Promise<T | null> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

function ViewAsContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ userId: string }>();

  const [session, setSession] = useState<AdminImpersonateResponse | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [checkinCount, setCheckinCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ending, setEnding] = useState(false);
  // Distinct from "session is null because it hasn't loaded yet" -- set once the admin
  // explicitly exits, so the page shows a clear "ended" state instead of reusing the
  // "Starting..." copy (which would otherwise look like it's stuck re-launching).
  const [ended, setEnded] = useState(false);

  async function start() {
    setError(null);
    try {
      const impersonation = await apiFetch<AdminImpersonateResponse>(
        `/api/v1/admin/users/${params.userId}/impersonate`,
        { method: "POST" }
      );
      setSession(impersonation);

      const today = new Date().toISOString().slice(0, 10);
      const from = new Date(Date.now() - 6 * 86400000).toISOString().slice(0, 10);

      const [profileData, checkinData] = await Promise.all([
        impersonatedFetch<Profile>(impersonation.access_token, "/api/v1/profile"),
        impersonatedFetch<CheckIn[]>(
          impersonation.access_token,
          `/api/v1/checkins?from_date=${from}&to_date=${today}`
        ),
      ]);
      setProfile(profileData);
      // Deliberately just a count -- whether they've been using the app -- never any of the
      // check-in's own wellness/self-report fields. This view is for account/support
      // questions (did onboarding finish, are they active), never for anything that reads as
      // a health or medical status, even in summary form.
      setCheckinCount((checkinData ?? []).length);
    } catch {
      setError("Could not start impersonation for this account.");
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.userId]);

  async function end() {
    setEnding(true);
    try {
      // Called with the admin's own token (apiFetch), not the impersonation token -- an
      // impersonation token could never call this itself, since it's a POST and impersonation
      // is read-only. Best-effort: the impersonation token expires on its own regardless.
      await apiFetch(`/api/v1/admin/users/${params.userId}/impersonate/end`, { method: "POST" });
    } catch {
      // Best-effort close-out -- the session is over either way once we clear local state below.
    } finally {
      setSession(null);
      setEnding(false);
      setEnded(true);
    }
  }

  if (error) {
    return <p className="text-sm text-red-400">{error}</p>;
  }

  if (ended) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-neutral-400">Impersonation session ended.</p>
        <Link
          href={`/admin/users/${params.userId}`}
          className="text-sm underline hover:text-neutral-200"
        >
          ← Back to account
        </Link>
      </div>
    );
  }

  if (!session) {
    return <p className="text-sm text-neutral-500">Starting impersonation session...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between rounded-xl border border-amber-800 bg-amber-950/30 px-4 py-3">
        <p className="text-sm text-amber-300">
          Viewing as <span className="font-medium">{session.user_email}</span> as an admin —
          read-only, expires automatically in {Math.round(session.expires_in / 60)} minutes.
        </p>
        <button
          type="button"
          onClick={end}
          disabled={ending}
          className="shrink-0 rounded-lg border border-amber-700 px-3 py-1.5 text-xs font-medium text-amber-300 hover:bg-amber-950/60 disabled:opacity-50"
        >
          {ending ? "Exiting..." : "Exit impersonation"}
        </button>
      </div>

      <p className="rounded-lg border border-neutral-800 bg-neutral-900/40 px-3 py-2 text-xs text-neutral-500">
        Account and engagement facts only — nothing about voice health, recovery status, or
        check-in content appears here, on purpose.
      </p>

      <section className="rounded-2xl border border-neutral-800 p-5">
        <h2 className="mb-3 text-sm font-medium text-neutral-300">Account setup</h2>
        {profile ? (
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <dt className="text-neutral-500">Practice frequency</dt>
            <dd>{profile.practice_frequency ?? "—"}</dd>
            <dt className="text-neutral-500">Musical style</dt>
            <dd>{profile.musical_style ?? "—"}</dd>
          </dl>
        ) : (
          <p className="text-sm text-neutral-500">Onboarding not completed yet.</p>
        )}
      </section>

      <section className="rounded-2xl border border-neutral-800 p-5">
        <h2 className="mb-3 text-sm font-medium text-neutral-300">Recent engagement</h2>
        <p className="text-sm text-neutral-300">
          {checkinCount} check-in{checkinCount === 1 ? "" : "s"} logged in the last 7 days.
        </p>
      </section>

      <div>
        <Link
          href={`/admin/users/${params.userId}`}
          className="text-sm underline hover:text-neutral-200"
        >
          ← Back to account
        </Link>
      </div>
    </div>
  );
}

export default function ViewAsPage() {
  return (
    <RequireAuth>
      <RequireAdmin>
        <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12">
          <ViewAsContent />
        </main>
      </RequireAdmin>
    </RequireAuth>
  );
}
