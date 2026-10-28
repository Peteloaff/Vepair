"use client";

import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { TeamManager } from "@/components/TeamManager";

export default function CoachTeamPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-8 sm:px-6">
          <h1 className="mb-1 text-2xl font-semibold tracking-tight">Your team</h1>
          <p className="mb-6 text-sm text-text-dim">
            The coaches in your clinic or studio. Everyone shares the same Coach Pro plan and
            invite allowance, but each coach&apos;s Vrotégés stay private to that coach — a
            Vrotégé chooses who sees their data, and that is one coach, not the whole team.
          </p>
          <TeamManager basePath="/api/v1/coach/team" renamePath="/api/v1/coach/team/organization" />
          <div className="mt-8">
            <Link href="/coach" className="text-xs text-text-faint hover:text-text-dim">
              &larr; Back to Coach Portal
            </Link>
          </div>
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
