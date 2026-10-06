"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Card, Chip, StatTile, type ChipTone } from "@/components/Card";
import { Icon } from "@/components/icons";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { Sparkline } from "@/components/Sparkline";
import { useAuth } from "@/lib/auth-context";
import { todayLocalDate } from "@/lib/date";
import {
  COACH_SHARE_CATEGORIES,
  type CoachShareCategory,
  type CoachProfile,
  type CoachSentInvite,
  type CoachSingerListItem,
  type RecoveryStatus,
} from "@/lib/types";

const STATUS_LABEL: Record<CoachSentInvite["status"], string> = {
  pending: "Pending",
  accepted: "Accepted",
  declined: "Declined",
  revoked: "Cancelled",
};

const SCORE_STATUS: Record<RecoveryStatus, { label: string; tone: ChipTone; text: string }> = {
  green: { label: "Steady", tone: "ok", text: "text-ok" },
  yellow: { label: "Moderate", tone: "warn", text: "text-warning" },
  red: { label: "Take it easy", tone: "bad", text: "text-danger" },
  unknown: { label: "No score", tone: "neutral", text: "text-text-faint" },
};

// Short, coach-facing names -- the shared COACH_SHARE_CATEGORY_LABEL strings are written to the
// singer ("Your recovery score & trends") for the consent screen.
const CATEGORY_SHORT_LABEL: Record<CoachShareCategory, string> = {
  recovery_trends: "Recovery",
  vocal_range: "Range",
  exercise_history: "History",
  recordings: "Recordings",
};

const AVATAR_GRADIENTS = [
  "from-violet to-blue",
  "from-teal to-blue",
  "from-warning to-danger",
  "from-blue to-violet",
];

function nameFor(email: string): string {
  const local = email.split("@")[0].replace(/[._-]+/g, " ").trim();
  return local.replace(/\b\w/g, (c) => c.toUpperCase()) || email;
}

function initialsFor(email: string): string {
  const parts = nameFor(email).split(" ");
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : parts[0].slice(0, 2)).toUpperCase();
}

function Avatar({ email, size = "md" }: { email: string; size?: "md" | "lg" }) {
  let hash = 0;
  for (const ch of email) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br font-semibold text-white ${
        AVATAR_GRADIENTS[hash % AVATAR_GRADIENTS.length]
      } ${size === "lg" ? "h-12 w-12 text-base" : "h-9 w-9 text-xs"}`}
    >
      {initialsFor(email)}
    </span>
  );
}

function lastPracticeLabel(date: string | null, today: string): string {
  if (!date) return "No sessions yet";
  if (date === today) return "Today";
  const days = Math.round(
    (new Date(`${today}T00:00:00`).getTime() - new Date(`${date}T00:00:00`).getTime()) / 86_400_000
  );
  if (days === 1) return "Yesterday";
  return `${days} days ago`;
}

function CoachDashboardContent() {
  const { apiFetch } = useAuth();
  const [profile, setProfile] = useState<CoachProfile | null>(null);
  const [singers, setSingers] = useState<CoachSingerListItem[] | null>(null);
  const [invites, setInvites] = useState<CoachSentInvite[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const today = todayLocalDate();

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

  const selected = useMemo(
    () => singers?.find((s) => s.singer_user_id === selectedId) ?? singers?.[0] ?? null,
    [singers, selectedId]
  );

  if (error) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (profile === null || singers === null || invites === null) {
    return <p className="text-sm text-text-faint">Loading...</p>;
  }

  const pendingInvites = invites.filter((i) => i.status === "pending");
  const practicedToday = singers.filter((s) => s.last_practice_date === today).length;
  const needALook = singers.filter(
    (s) => s.score_status === "yellow" || s.score_status === "red"
  ).length;
  const unreadTotal = singers.reduce((sum, s) => sum + s.unread_message_count, 0);

  return (
    <div className="mx-auto w-full max-w-6xl">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-normal tracking-tight sm:text-4xl">Coach Portal</h1>
          <p className="mt-1 text-sm text-text-dim">
            {profile.display_name}
            {profile.studio_name && <> &middot; {profile.studio_name}</>}
          </p>
        </div>
        <Link
          href="/coach/invite"
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-br from-violet to-blue px-4 py-2.5 text-sm font-semibold text-white hover:opacity-90"
        >
          <Icon name="plus" className="h-4 w-4" />
          Invite a Vrotégé
        </Link>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Vrotégés" value={singers.length} />
        <StatTile label="Practiced today" value={practicedToday} />
        <StatTile label="Need a look" value={needALook} />
        <StatTile label="Unread messages" value={unreadTotal} />
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="grid content-start gap-4 lg:col-span-7">
          <Card title="Your Vrotégés" meta={singers.length > 0 ? "Select one for details" : undefined}>
            {singers.length === 0 ? (
              <p className="text-sm text-text-faint">
                No Vrotégés yet — invite one to get started.
              </p>
            ) : (
              <div className="-mx-2">
                <div className="hidden grid-cols-[minmax(0,2fr)_minmax(0,1.5fr)_minmax(0,1.1fr)_minmax(0,0.8fr)] gap-3 px-3 pb-2 text-xs uppercase tracking-wider text-text-faint sm:grid">
                  <span>Vrotégé</span>
                  <span>Score</span>
                  <span>Last practice</span>
                  <span>Streak</span>
                </div>
                {singers.map((singer) => {
                  const isSelected = singer.singer_user_id === selected?.singer_user_id;
                  const status = singer.score_status ? SCORE_STATUS[singer.score_status] : null;
                  return (
                    <button
                      key={singer.coach_access_id}
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => setSelectedId(singer.singer_user_id)}
                      className={`grid w-full grid-cols-2 items-center gap-3 rounded-2xl border px-3 py-3 text-left transition-colors hover:bg-surface-2 sm:grid-cols-[minmax(0,2fr)_minmax(0,1.5fr)_minmax(0,1.1fr)_minmax(0,0.8fr)] ${
                        isSelected ? "border-violet/60 bg-surface-2" : "border-transparent"
                      }`}
                    >
                      <span className="col-span-2 flex min-w-0 items-center gap-3 sm:col-span-1">
                        <Avatar email={singer.singer_email} />
                        <span className="min-w-0">
                          <span className="block truncate font-medium">
                            {nameFor(singer.singer_email)}
                          </span>
                          <span className="block truncate text-xs text-text-faint">
                            {singer.singer_email}
                          </span>
                        </span>
                      </span>
                      <span className="flex items-center gap-2.5">
                        {singer.score_value !== null && status ? (
                          <>
                            <span className={`font-display text-xl tabular-nums ${status.text}`}>
                              {Math.round(singer.score_value)}
                            </span>
                            {singer.score_trend && singer.score_trend.length > 1 && (
                              <Sparkline values={singer.score_trend} className={`h-7 w-16 ${status.text}`} />
                            )}
                          </>
                        ) : (
                          <span className="text-xs text-text-faint">
                            {singer.granted_categories.includes("recovery_trends")
                              ? "No score yet"
                              : "Not shared"}
                          </span>
                        )}
                      </span>
                      <span className="text-sm text-text-dim">
                        {singer.granted_categories.includes("exercise_history")
                          ? lastPracticeLabel(singer.last_practice_date, today)
                          : "Not shared"}
                      </span>
                      <span className="flex items-center gap-2 text-sm text-text-dim">
                        {singer.current_streak_days !== null && singer.current_streak_days > 0 && (
                          <Icon name="flame" className="h-4 w-4 text-warning" />
                        )}
                        <span className="tabular-nums">{singer.current_streak_days ?? "—"}</span>
                        {singer.unread_message_count > 0 && (
                          <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-violet-faint px-2 py-0.5 text-xs font-semibold text-violet">
                            <Icon name="chat" className="h-3 w-3" />
                            {singer.unread_message_count}
                          </span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </Card>

          <Card title="Invites sent" meta={`${pendingInvites.length} pending`}>
            {pendingInvites.length === 0 ? (
              <p className="text-sm text-text-faint">No pending invites.</p>
            ) : (
              <ul className="space-y-2">
                {pendingInvites.map((invite) => (
                  <li
                    key={invite.id}
                    className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-surface-2 px-3.5 py-3"
                  >
                    <span className="min-w-40 flex-1 text-sm">{invite.singer_email}</span>
                    <Chip tone="warn">{STATUS_LABEL[invite.status]}</Chip>
                    <button
                      type="button"
                      onClick={() => cancelInvite(invite.id)}
                      className="rounded-lg border border-border-strong px-3 py-1.5 text-xs font-semibold hover:bg-surface"
                    >
                      Cancel
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="lg:col-span-5">
          {selected ? (
            <SingerPanel singer={selected} today={today} />
          ) : (
            <Card title="Vrotégé details">
              <p className="text-sm text-text-faint">
                Once someone accepts your invite, their snapshot shows up here.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function SingerPanel({ singer, today }: { singer: CoachSingerListItem; today: string }) {
  const status = singer.score_status ? SCORE_STATUS[singer.score_status] : null;
  const base = `/coach/singers/${singer.singer_user_id}`;
  const actions = [
    { href: base, label: "Overview" },
    { href: `${base}/assign`, label: "Assign exercises" },
    { href: `${base}/notes`, label: "Notes" },
    { href: `${base}/messages`, label: "Messages" },
    { href: `${base}/progress`, label: "Progress" },
    { href: `${base}/recordings`, label: "Recordings" },
  ];
  return (
    <Card className="lg:sticky lg:top-4">
      <div className="mb-4 flex items-center gap-3.5">
        <Avatar email={singer.singer_email} size="lg" />
        <div className="min-w-0">
          <h2 className="truncate text-xl font-medium tracking-tight">
            {nameFor(singer.singer_email)}
          </h2>
          <p className="truncate text-xs text-text-faint">{singer.singer_email}</p>
        </div>
      </div>

      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-faint">
        What they share
      </p>
      <div className="mb-5 flex flex-wrap gap-1.5">
        {COACH_SHARE_CATEGORIES.map((category) => {
          const shared = singer.granted_categories.includes(category);
          return (
            <span
              key={category}
              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                shared ? "bg-accent-faint text-accent" : "bg-surface-2 text-text-faint line-through"
              }`}
            >
              {CATEGORY_SHORT_LABEL[category]}
            </span>
          );
        })}
      </div>

      {singer.score_value !== null && status ? (
        <div className="mb-5 rounded-2xl border border-border bg-surface-2 p-4">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-sm text-text-dim">VepAIr Score</span>
            <Chip tone={status.tone}>
              {Math.round(singer.score_value)} &middot; {status.label}
            </Chip>
          </div>
          {singer.score_trend && singer.score_trend.length > 1 && (
            <Sparkline values={singer.score_trend} className={`h-14 w-full ${status.text}`} />
          )}
        </div>
      ) : (
        <p className="mb-5 rounded-2xl bg-surface-2 px-4 py-3 text-sm text-text-faint">
          {singer.granted_categories.includes("recovery_trends")
            ? "No score yet — they haven't checked in recently."
            : "Recovery trends aren't shared, so their score and check-ins stay private."}
        </p>
      )}

      {singer.granted_categories.includes("exercise_history") && (
        <p className="mb-5 text-sm text-text-dim">
          Last practice: {lastPracticeLabel(singer.last_practice_date, today)}
          {singer.current_streak_days ? ` · ${singer.current_streak_days}-day streak` : ""}
        </p>
      )}

      <div className="grid grid-cols-2 gap-2">
        {actions.map((a, i) => (
          <Link
            key={a.href}
            href={a.href}
            className={`rounded-xl px-3 py-2.5 text-center text-sm font-semibold ${
              i === 0
                ? "bg-gradient-to-br from-violet to-blue text-white hover:opacity-90"
                : "border border-border-strong hover:bg-surface-2"
            }`}
          >
            {a.label}
            {a.label === "Messages" && singer.unread_message_count > 0
              ? ` (${singer.unread_message_count})`
              : ""}
          </Link>
        ))}
      </div>
    </Card>
  );
}

export default function CoachDashboardPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-4 py-8 sm:px-6">
          <CoachDashboardContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
