"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

const THEME_KEY = "vepair_theme";

export type Theme = "light" | "dark" | "system";
type ResolvedTheme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

// Mirrors the inline no-flash script in layout.tsx exactly -- same key, same system-preference
// fallback -- so the class the browser paints before hydration never disagrees with what this
// provider settles on once it runs.
function resolveAndApply(theme: Theme): ResolvedTheme {
  const resolved: ResolvedTheme =
    theme === "system"
      ? window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : theme;
  document.documentElement.classList.toggle("dark", resolved === "dark");
  return resolved;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  // Defaults matching the inline script's own default (system/dark) until the mount effect
  // below reconciles with whatever's actually stored -- avoids a mismatched initial value that
  // would itself cause a flash on top of the one the inline script already prevents.
  const [theme, setThemeState] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("dark");

  useEffect(() => {
    let stored: Theme | null = null;
    try {
      stored = localStorage.getItem(THEME_KEY) as Theme | null;
    } catch {
      // Private browsing / blocked storage -- fall back to system, same as a first-time visit.
    }
    const initial = stored ?? "system";
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setThemeState(initial);
    setResolvedTheme(resolveAndApply(initial));

    if (initial !== "system") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setResolvedTheme(resolveAndApply("system"));
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  const setTheme = useCallback((next: Theme) => {
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // Best-effort -- the choice still applies for this page load even if it can't persist.
    }
    setThemeState(next);
    setResolvedTheme(resolveAndApply(next));
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
