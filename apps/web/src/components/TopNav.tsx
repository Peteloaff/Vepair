"use client";

import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";

// Cycles light -> dark -> system -> light. A single click-through button rather than a
// dropdown -- this header is already a dense single-row flex layout at every breakpoint, and a
// popover would add a second interaction surface (click-outside, z-index) for a control this
// small. The icon always reflects what's actually applied right now (resolvedTheme); "system"
// is conveyed via the aria-label/title, not a third icon, since at a glance the user only needs
// to know what they're looking at, not which mode produced it.
function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme();

  function cycle() {
    setTheme(theme === "light" ? "dark" : theme === "dark" ? "system" : "light");
  }

  const label =
    theme === "system" ? `Theme: System (${resolvedTheme})` : `Theme: ${theme}`;

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={label}
      title={`${label} — click to change`}
      className="flex h-7 w-7 items-center justify-center rounded-lg border border-border-strong text-text-dim hover:bg-surface-2 hover:text-text sm:h-8 sm:w-8"
    >
      {resolvedTheme === "dark" ? (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm0 14a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zm8-6a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM4 10a1 1 0 01-1 1H2a1 1 0 110-2h1a1 1 0 011 1zm11.66-6.66a1 1 0 010 1.41l-.7.71a1 1 0 11-1.42-1.42l.71-.7a1 1 0 011.41 0zM6.46 14.54a1 1 0 010 1.41l-.71.71a1 1 0 11-1.41-1.42l.7-.7a1 1 0 011.42 0zm9.2 1.41a1 1 0 01-1.41 0l-.71-.71a1 1 0 111.42-1.41l.7.7a1 1 0 010 1.42zM5.75 5.75a1 1 0 01-1.41 0l-.71-.71a1 1 0 011.42-1.41l.7.7a1 1 0 010 1.42zM10 6a4 4 0 100 8 4 4 0 000-8z" />
        </svg>
      ) : (
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path d="M17.293 13.293a8 8 0 01-10.586-10.586 8.002 8.002 0 1010.586 10.586z" />
        </svg>
      )}
    </button>
  );
}

export function TopNav() {
  const { status, user, logout } = useAuth();

  return (
    <header className="flex items-center justify-between border-b border-border px-4 py-3 sm:px-6 sm:py-4">
      <Link
        href="/"
        className="flex items-center gap-1.5 text-base font-semibold tracking-tight sm:gap-2 sm:text-lg"
      >
        <Image src="/brand/vepair-logo.png" alt="" width={24} height={24} priority className="sm:h-7 sm:w-7" />
        VepAIr
      </Link>
      <div className="flex items-center gap-2.5 sm:gap-4">
        {status === "authenticated" && (
          <div className="flex items-center gap-2.5 text-xs text-text-dim sm:gap-4 sm:text-sm">
            <Link href="/onboarding" className="hover:text-text">
              Profile
            </Link>
            <Link href="/help" className="hover:text-text">
              Help
            </Link>
            <Link href="/settings" className="hover:text-text">
              Settings
            </Link>
            {user?.is_admin && (
              <Link href="/admin" className="font-medium text-warning hover:opacity-80">
                Admin
              </Link>
            )}
            <span className="hidden sm:inline">{user?.email}</span>
            <button
              type="button"
              onClick={() => logout()}
              className="rounded-lg border border-border-strong px-2 py-1 text-xs hover:bg-surface-2 sm:px-3 sm:py-1.5 sm:text-sm"
            >
              Log out
            </button>
          </div>
        )}
        <ThemeToggle />
      </div>
    </header>
  );
}
