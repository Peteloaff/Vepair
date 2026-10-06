"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      // Remember where they were headed (e.g. the invite link in a coach's email) so logging in
      // lands them there instead of on the dashboard.
      const here = window.location.pathname + window.location.search;
      router.replace(here === "/" ? "/login" : `/login?next=${encodeURIComponent(here)}`);
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="text-sm text-text-faint">Loading...</p>
      </main>
    );
  }

  if (status === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}
