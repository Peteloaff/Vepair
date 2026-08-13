"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import type { CoachProfile } from "@/lib/types";

/** Stage 12 Phase II. Wrap inside <RequireAuth> — this only checks "is this authenticated
 * account a coach," not authentication itself. Mirrors how the backend itself decides "is a
 * coach" (app/coach_auth.py's get_current_coach): the presence of a real CoachProfile row,
 * checked server-side via GET /api/v1/coach/profile, never a client-trusted flag. */
export function RequireCoach({ children }: { children: React.ReactNode }) {
  const { apiFetch } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "coach" | "not-coach">("loading");

  useEffect(() => {
    apiFetch<CoachProfile>("/api/v1/coach/profile")
      .then(() => setStatus("coach"))
      .catch(() => setStatus("not-coach"));
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

  return <>{children}</>;
}
