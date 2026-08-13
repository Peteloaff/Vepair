const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export interface AuthUser {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

async function parseResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let code = "unknown_error";
    let message = res.statusText || "Request failed";
    try {
      const body = await res.json();
      if (body?.error?.code) {
        code = body.error.code;
        message = body.error.message ?? message;
      }
    } catch {
      // response body wasn't JSON — fall back to statusText above
    }
    throw new ApiError(res.status, code, message);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

function jsonRequest(path: string, method: string, body?: unknown): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export async function signup(email: string, password: string): Promise<TokenResponse> {
  const res = await jsonRequest("/api/v1/auth/signup", "POST", { email, password });
  return parseResponse<TokenResponse>(res);
}

// Stage 12 Phase II (dev-only). A coach account is a coach account from creation — see
// app.models.CoachProfile — never a self-serve upgrade on an existing singer account.
export async function coachSignup(
  email: string,
  password: string,
  displayName: string,
  studioName: string | null
): Promise<TokenResponse> {
  const res = await jsonRequest("/api/v1/auth/coach-signup", "POST", {
    email,
    password,
    display_name: displayName,
    studio_name: studioName,
  });
  return parseResponse<TokenResponse>(res);
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await jsonRequest("/api/v1/auth/login", "POST", { email, password });
  return parseResponse<TokenResponse>(res);
}

export async function refreshTokens(refreshToken: string): Promise<TokenResponse> {
  const res = await jsonRequest("/api/v1/auth/refresh", "POST", { refresh_token: refreshToken });
  return parseResponse<TokenResponse>(res);
}

export async function logout(refreshToken: string): Promise<void> {
  const res = await jsonRequest("/api/v1/auth/logout", "POST", { refresh_token: refreshToken });
  await parseResponse<void>(res);
}

export async function requestPasswordReset(email: string): Promise<void> {
  const res = await jsonRequest("/api/v1/auth/password-reset/request", "POST", { email });
  await parseResponse<void>(res);
}

export async function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  const res = await jsonRequest("/api/v1/auth/password-reset/confirm", "POST", {
    token,
    new_password: newPassword,
  });
  await parseResponse<void>(res);
}

export async function fetchMe(accessToken: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return parseResponse<AuthUser>(res);
}

// Deliberately bypasses useAuth().apiFetch: a wrong password here is a 401 that means
// "wrong password," not "expired session" — apiFetch can't tell those apart and would
// silently retry after a token refresh, then log the user out on the second 401 instead of
// surfacing invalid_password.
export async function deleteAccount(accessToken: string, password: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ password }),
  });
  await parseResponse<void>(res);
}

export { API_BASE, parseResponse };
