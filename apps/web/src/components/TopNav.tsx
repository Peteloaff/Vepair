"use client";

import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export function TopNav() {
  const { status, user, logout } = useAuth();

  return (
    <header className="flex items-center justify-between border-b border-neutral-800 px-4 py-3 sm:px-6 sm:py-4">
      <Link
        href="/"
        className="flex items-center gap-1.5 text-base font-semibold tracking-tight sm:gap-2 sm:text-lg"
      >
        <Image src="/brand/vepair-logo.png" alt="" width={24} height={24} priority className="sm:h-7 sm:w-7" />
        VepAIr
      </Link>
      {status === "authenticated" && (
        <div className="flex items-center gap-2.5 text-xs text-neutral-400 sm:gap-4 sm:text-sm">
          <Link href="/onboarding" className="hover:text-neutral-100">
            Profile
          </Link>
          <Link href="/help" className="hover:text-neutral-100">
            Help
          </Link>
          <Link href="/settings" className="hover:text-neutral-100">
            Settings
          </Link>
          {user?.is_admin && (
            <Link href="/admin" className="font-medium text-amber-400 hover:text-amber-300">
              Admin
            </Link>
          )}
          <span className="hidden sm:inline">{user?.email}</span>
          <button
            type="button"
            onClick={() => logout()}
            className="rounded-lg border border-neutral-700 px-2 py-1 text-xs hover:bg-neutral-800 sm:px-3 sm:py-1.5 sm:text-sm"
          >
            Log out
          </button>
        </div>
      )}
    </header>
  );
}
