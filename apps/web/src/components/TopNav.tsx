"use client";

import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export function TopNav() {
  const { status, user, logout } = useAuth();

  return (
    <header className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
      <Link href="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
        <Image src="/brand/vepair-logo.png" alt="" width={28} height={28} priority />
        VepAIr
      </Link>
      {status === "authenticated" && (
        <div className="flex items-center gap-4 text-sm text-neutral-400">
          <Link href="/onboarding" className="hover:text-neutral-100">
            Profile
          </Link>
          <Link href="/settings" className="hover:text-neutral-100">
            Settings
          </Link>
          <span className="hidden sm:inline">{user?.email}</span>
          <button
            type="button"
            onClick={() => logout()}
            className="rounded-lg border border-neutral-700 px-3 py-1.5 hover:bg-neutral-800"
          >
            Log out
          </button>
        </div>
      )}
    </header>
  );
}
