"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/apiClient";

// Stage 12 Phase II (dev-only pilot). Not linked from the main consumer /signup page or nav —
// a coach account is a distinct account type from creation (see CoachSignupRequest's
// docstring backend-side), shared directly with invited pilot coaches rather than advertised.
export default function CoachSignupPage() {
  const { status, coachSignup } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [studioName, setStudioName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const justSubmittedRef = useRef(false);

  useEffect(() => {
    if (status === "authenticated" && !justSubmittedRef.current) {
      router.replace("/");
    }
  }, [status, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      justSubmittedRef.current = true;
      await coachSignup(email, password, displayName, studioName || null);
      router.replace("/coach");
    } catch (err) {
      justSubmittedRef.current = false;
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Create a coach account</h1>
        <p className="mb-8 text-sm text-text-dim">
          For vocal coaches and studios — separate from a regular VepAIr account.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="displayName" className="mb-1 block text-xs text-text-dim">
              Your name
            </label>
            <input
              id="displayName"
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </div>

          <div>
            <label htmlFor="studioName" className="mb-1 block text-xs text-text-dim">
              Studio name (optional)
            </label>
            <input
              id="studioName"
              value={studioName}
              onChange={(e) => setStudioName(e.target.value)}
              className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </div>

          <div>
            <label htmlFor="email" className="mb-1 block text-xs text-text-dim">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-xs text-text-dim">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
            />
            <p className="mt-1 text-xs text-text-faint">At least 8 characters.</p>
          </div>

          {error && (
            <p className="rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong disabled:opacity-50"
          >
            {submitting ? "Creating account..." : "Create coach account"}
          </button>
        </form>

        <p className="mt-4 text-xs text-text-faint">
          By creating an account, you agree to our{" "}
          <Link href="/terms" className="underline hover:text-text-dim">
            Terms of Service
          </Link>
          .
        </p>

        <div className="mt-6 text-xs text-text-faint">
          Not a coach?{" "}
          <Link href="/signup" className="text-text-dim hover:text-text">
            Sign up as a Vrotégé
          </Link>
        </div>
      </div>
    </main>
  );
}
