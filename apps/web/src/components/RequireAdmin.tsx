"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import type { AuthUser } from "@/lib/apiClient";

/** Backend Admin (post-Stage-12). Wrap inside <RequireAuth> — this only checks "is this
 * authenticated account an admin," not authentication itself. Mirrors RequireCoach.tsx exactly:
 * a server-truth check via GET /api/v1/admin/profile (403s for a non-admin), never a
 * client-trusted flag. */
export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { apiFetch } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "admin" | "not-admin">("loading");

  useEffect(() => {
    apiFetch<AuthUser>("/api/v1/admin/profile")
      .then(() => setStatus("admin"))
      .catch(() => setStatus("not-admin"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (status === "not-admin") {
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

  if (status === "not-admin") {
    return null;
  }

  return <>{children}</>;
}
