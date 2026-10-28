"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import type { OrgReport as OrgReportData, Team } from "@/lib/types";

const PERIODS = [7, 30, 90] as const;

// For organization admins: what each coach has done lately and how much their Vrotégés practiced,
// as counts only. Practice only covers Vrotégés who share their exercise history with that coach,
// and a coach's practice figures stay hidden until a few of them do, so a number never describes
// one identifiable person. No names, emails or voice data appear here.
export function OrgReport() {
  const { apiFetch } = useAuth();
  const [team, setTeam] = useState<Team | null>(null);
  const [days, setDays] = useState<number>(30);
  const [report, setReport] = useState<OrgReportData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const t = await apiFetch<Team>("/api/v1/coach/team");
        if (!cancelled) setTeam(t);
      } catch {
        if (!cancelled) setTeam(null);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isAdmin = team?.my_role === "admin";

  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await apiFetch<OrgReportData>(
          `/api/v1/coach/team/report?days=${days}`,
        );
        if (!cancelled) {
          setReport(r);
          setError(null);
        }
      } catch {
        if (!cancelled)
          setError("Couldn't load the report. Try again in a moment.");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, days]);

  if (!isAdmin) return null;

  const minGroup = report?.min_group_size ?? 1;
  const vrotegesWord = minGroup === 1 ? "Vrotégé" : "Vrotégés";
  const shown = (value: number | null) =>
    value === null ? (
      <span
        className="text-text-faint"
        title={`Shown once ${minGroup} ${vrotegesWord} shares`}
      >
        &ndash;
      </span>
    ) : (
      value
    );

  return (
    <section className="mt-10 border-t border-border pt-8">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold tracking-tight">Team activity</h2>
        <div
          role="group"
          aria-label="Report period"
          className="flex gap-1 text-sm"
        >
          {PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              aria-pressed={days === p}
              onClick={() => setDays(p)}
              className={`rounded-lg border px-3 py-1.5 ${
                days === p
                  ? "border-accent bg-accent-faint text-accent"
                  : "border-border-strong hover:bg-surface-2"
              }`}
            >
              {p} days
            </button>
          ))}
        </div>
      </div>
      <p className="mb-4 text-sm text-text-dim">
        What each coach has done and how much their Vrotégés practiced, as
        counts only. You never see names or voice data here. Practice covers
        only Vrotégés who share their exercise history with that coach, and a
        coach&apos;s practice figures appear once {minGroup} or more of them do.
        If only one Vrotégé shares with a coach, the figures are theirs alone.
      </p>

      {error && (
        <p className="mb-3 rounded-xl bg-danger-faint px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      {report && (
        <div className="overflow-x-auto rounded-2xl border border-border">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <thead className="bg-surface-2 text-xs text-text-faint">
              <tr>
                <th className="px-3 py-2 font-medium">Coach</th>
                <th className="px-3 py-2 text-right font-medium">Vrotégés</th>
                <th className="px-3 py-2 text-right font-medium">Invites</th>
                <th className="px-3 py-2 text-right font-medium">Notes</th>
                <th className="px-3 py-2 text-right font-medium">Messages</th>
                <th className="px-3 py-2 text-right font-medium">Assigned</th>
                <th className="px-3 py-2 text-right font-medium">Sessions</th>
                <th className="px-3 py-2 text-right font-medium">Practicing</th>
              </tr>
            </thead>
            <tbody>
              {report.coaches.map((c) => (
                <tr key={c.coach_id} className="border-t border-border">
                  <td className="px-3 py-2">
                    {c.display_name}
                    {!c.is_active && (
                      <span className="ml-1 text-xs text-text-faint">
                        (deactivated)
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {c.connected_vroteges}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {c.invites_sent}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {c.notes_written}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {c.messages_sent}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {c.assignments_sent}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {shown(c.practice_sessions)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {shown(c.practicing_vroteges)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-border-strong bg-surface-2 font-medium">
                <td className="px-3 py-2">Team</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {report.totals.connected_vroteges}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {report.totals.invites_sent}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {report.totals.notes_written}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {report.totals.messages_sent}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {report.totals.assignments_sent}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {report.totals.practice_sessions}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {report.totals.practicing_vroteges}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
      <p className="mt-2 text-xs text-text-faint">
        Last {days} days. A dash means no Vrotégé shares their exercise history
        with that coach. Team totals leave those coaches out.
      </p>
    </section>
  );
}
