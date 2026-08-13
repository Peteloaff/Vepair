"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  ApiError,
  API_BASE,
  type AuthUser,
  type TokenResponse,
  coachSignup as apiCoachSignup,
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
  parseResponse,
  refreshTokens,
  signup as apiSignup,
} from "./apiClient";

const ACCESS_KEY = "vepair_access_token";
const REFRESH_KEY = "vepair_refresh_token";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface ApiFetchOptions {
  method?: string;
  body?: unknown;
  searchParams?: Record<string, string>;
}

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  coachSignup: (
    email: string,
    password: string,
    displayName: string,
    studioName: string | null
  ) => Promise<void>;
  logout: () => Promise<void>;
  apiFetch: <T>(path: string, options?: ApiFetchOptions) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  // Refs mirror the tokens for use inside apiFetch, which must always see the latest
  // values even when called from a stale closure (e.g. a component that hasn't re-rendered).
  const accessTokenRef = useRef<string | null>(null);
  const refreshTokenRef = useRef<string | null>(null);

  const persistTokens = useCallback((tokens: TokenResponse) => {
    accessTokenRef.current = tokens.access_token;
    refreshTokenRef.current = tokens.refresh_token;
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    setUser(tokens.user);
    setStatus("authenticated");
  }, []);

  const clearSession = useCallback(() => {
    accessTokenRef.current = null;
    refreshTokenRef.current = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  useEffect(() => {
    const storedAccess = localStorage.getItem(ACCESS_KEY);
    const storedRefresh = localStorage.getItem(REFRESH_KEY);

    if (!storedAccess || !storedRefresh) {
      // Reading localStorage is only possible client-side, so this bootstrap check must
      // live in an effect — there's no way to know auth status during the initial render.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStatus("unauthenticated");
      return;
    }

    accessTokenRef.current = storedAccess;
    refreshTokenRef.current = storedRefresh;

    fetchMe(storedAccess)
      .then((me) => {
        setUser(me);
        setStatus("authenticated");
      })
      .catch(async () => {
        // Access token expired or invalid — try a silent refresh before giving up.
        try {
          const tokens = await refreshTokens(storedRefresh);
          persistTokens(tokens);
        } catch {
          clearSession();
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signup = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiSignup(email, password);
      persistTokens(tokens);
    },
    [persistTokens]
  );

  const coachSignup = useCallback(
    async (
      email: string,
      password: string,
      displayName: string,
      studioName: string | null
    ) => {
      const tokens = await apiCoachSignup(email, password, displayName, studioName);
      persistTokens(tokens);
    },
    [persistTokens]
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiLogin(email, password);
      persistTokens(tokens);
    },
    [persistTokens]
  );

  const logout = useCallback(async () => {
    const rt = refreshTokenRef.current;
    if (rt) {
      try {
        await apiLogout(rt);
      } catch {
        // best-effort: clear local session regardless of whether the server call succeeded
      }
    }
    clearSession();
    router.push("/login");
  }, [clearSession, router]);

  const apiFetch = useCallback(
    async <T,>(path: string, options: ApiFetchOptions = {}): Promise<T> => {
      const { method = "GET", body, searchParams } = options;

      const url = new URL(`${API_BASE}${path}`);
      if (searchParams) {
        for (const [key, value] of Object.entries(searchParams)) {
          url.searchParams.set(key, value);
        }
      }

      const isFormData = body instanceof FormData;
      const doFetch = (token: string) =>
        fetch(url.toString(), {
          method,
          headers: {
            Authorization: `Bearer ${token}`,
            // FormData sets its own multipart Content-Type (with boundary) — the browser
            // only does that correctly when we don't set the header ourselves.
            ...(body !== undefined && !isFormData ? { "Content-Type": "application/json" } : {}),
          },
          body: body !== undefined ? (isFormData ? body : JSON.stringify(body)) : undefined,
        });

      let token = accessTokenRef.current;
      if (!token) {
        clearSession();
        router.push("/login");
        throw new ApiError(401, "missing_token", "Not authenticated");
      }

      let res = await doFetch(token);

      if (res.status === 401) {
        const rt = refreshTokenRef.current;
        if (!rt) {
          clearSession();
          router.push("/login");
          throw new ApiError(401, "session_expired", "Your session has expired.");
        }
        try {
          const tokens = await refreshTokens(rt);
          persistTokens(tokens);
          token = tokens.access_token;
          res = await doFetch(token);
        } catch {
          clearSession();
          router.push("/login");
          throw new ApiError(401, "session_expired", "Your session has expired.");
        }
      }

      return parseResponse<T>(res);
    },
    [clearSession, persistTokens, router]
  );

  return (
    <AuthContext.Provider
      value={{ status, user, login, signup, coachSignup, logout, apiFetch }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
