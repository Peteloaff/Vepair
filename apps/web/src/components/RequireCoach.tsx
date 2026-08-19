"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/apiClient";
import type { CoachProfile } from "@/lib/types";

/** Stage 12 Phase II. Wrap inside <RequireAuth> — this only checks "is this authenticated
 * account a coach," not authentication itself. Mirrors how the backend itself decides "is a
 * coach" (app/coach_auth.py's get_current_coach): the presence of a real CoachProfile row,
 * checked server-side via GET /api/v1/coach/profile, never a client-trusted flag.
 *
 * Post-Stage-12 Part 2 (SaaS billing): get_current_coach now also 403s with
 * "coach_pro_required" when the coach's Organization isn't yet activated (see
 * app.models.Organization -- no free coach tier). That's a real coach account waiting on
 * activation, not a non-coach, so it gets its own "pending" state here instead of being
 * silently redirected home the same way a genuine non-coach is. */
export function RequireCoach({ children }: { children: React.ReactNode }) {
  const { apiFetch } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "coach" | "pending" | "not-coach">("loading");

  useEffect(() => {
    apiFetch<CoachProfile>("/api/v1/coach/profile")
      .then(() => setStatus("coach"))
      .catch((err) => {
        setStatus(err instanceof ApiError && err.code === "coach_pro_required" ? "pending" : "not-coach");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (status === "not-coach") {
      router.replace("/");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-neutral-500">Loading...</p>
      </main>
    );
  }

  if (status === "not-coach") {
    return null;
  }

  if (status === "pending") {
    return (
      <main className="flex flex-1 items-center justify-center px-6">
        <div className="max-w-sm text-center">
          <h1 className="mb-2 text-lg font-semibold text-neutral-100">
            Your account is pending activation
          </h1>
          <p className="text-sm text-neutral-400">
            Your coach account has been created, but isn&apos;t active yet. Contact us to get
            started.
          </p>
        </div>
      </main>
    );
  }

  return <>{children}</>;
}
