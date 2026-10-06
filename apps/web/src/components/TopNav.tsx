"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
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

type NavLink = { href: string; label: string; match?: (path: string) => boolean };

const SINGER_LINKS: NavLink[] = [
  { href: "/", label: "Home", match: (p) => p === "/" },
  { href: "/progress", label: "Progress" },
  { href: "/vocal-plan", label: "Vocal plan" },
  {
    href: "/exercises",
    label: "Exercises",
    match: (p) => p.startsWith("/exercises") || p.startsWith("/quick-routine"),
  },
  { href: "/tone-match", label: "Tone Match" },
  { href: "/recordings", label: "Recordings" },
];

function initialsFor(email: string | undefined): string {
  const local = (email ?? "").split("@")[0].replace(/[^a-zA-Z]+/g, " ").trim();
  if (!local) return "V";
  const parts = local.split(" ");
  const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : local.slice(0, 2);
  return letters.toUpperCase();
}

export function TopNav() {
  const { status, user, logout, apiFetch } = useAuth();
  const pathname = usePathname();
  // Which links to show depends on account kind. A coach-only account has no singer data, so the
  // singer links would all land on empty states; a dual-role account (coach + singer profile)
  // gets both sets. Best-effort checks -- a failure just leaves the plain singer nav.
  const [isCoach, setIsCoach] = useState(false);
  const [hasSingerProfile, setHasSingerProfile] = useState(true);

  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false;
    apiFetch("/api/v1/coach/profile")
      .then(() => {
        if (cancelled) return;
        setIsCoach(true);
        apiFetch("/api/v1/profile")
          .then(() => !cancelled && setHasSingerProfile(true))
          .catch(() => !cancelled && setHasSingerProfile(false));
      })
      .catch(() => {
        if (!cancelled) setIsCoach(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const links: NavLink[] = [];
  if (!isCoach || hasSingerProfile) links.push(...SINGER_LINKS);
  else links.push(SINGER_LINKS[0]);
  if (isCoach) {
    links.push({ href: "/coach", label: "Coach Portal", match: (p) => p.startsWith("/coach") });
  }

  return (
    <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border px-4 py-3 sm:px-6 sm:py-4">
      <Link href="/" className="text-xl font-medium tracking-tight sm:text-2xl" aria-label="VepAIr home">
        Vep<span className="text-brand">AIr</span>
      </Link>

      {status === "authenticated" && (
        <nav
          aria-label="Main"
          className="order-last -mx-4 flex w-[calc(100%+2rem)] gap-1 overflow-x-auto px-4 [scrollbar-width:none] lg:order-none lg:mx-0 lg:w-auto lg:flex-1 lg:px-0 [&::-webkit-scrollbar]:hidden"
        >
          {links.map((link) => {
            const active = link.match ? link.match(pathname) : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={`relative whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-surface hover:text-text ${
                  active ? "text-text" : "text-text-dim"
                }`}
              >
                {link.label}
                {active && (
                  <span className="bg-brand absolute inset-x-3 bottom-0.5 h-0.5 rounded-full" />
                )}
              </Link>
            );
          })}
        </nav>
      )}

      <div className="flex items-center gap-2.5 sm:gap-3">
        {status === "authenticated" && (
          <div className="flex items-center gap-2.5 text-xs text-text-dim sm:gap-3 sm:text-sm">
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
            <Link
              href="/onboarding"
              title={user?.email ? `Profile (${user.email})` : "Profile"}
              aria-label="Profile"
              className="bg-brand flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold text-accent-ink hover:opacity-90"
            >
              {initialsFor(user?.email)}
            </Link>
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
