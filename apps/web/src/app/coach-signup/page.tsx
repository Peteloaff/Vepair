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
        <p className="mb-8 text-sm text-neutral-400">
          For vocal coaches and studios — separate from a regular VepAIr account.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="displayName" className="mb-1 block text-xs text-neutral-400">
              Your name
            </label>
            <input
              id="displayName"
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
          </div>

          <div>
            <label htmlFor="studioName" className="mb-1 block text-xs text-neutral-400">
              Studio name (optional)
            </label>
            <input
              id="studioName"
              value={studioName}
              onChange={(e) => setStudioName(e.target.value)}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
          </div>

          <div>
            <label htmlFor="email" className="mb-1 block text-xs text-neutral-400">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-xs text-neutral-400">
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
              className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
            />
            <p className="mt-1 text-xs text-neutral-500">At least 8 characters.</p>
          </div>

          {error && (
            <p className="rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
          >
            {submitting ? "Creating account..." : "Create coach account"}
          </button>
        </form>

        <div className="mt-6 text-xs text-neutral-500">
          Not a coach?{" "}
          <Link href="/signup" className="text-neutral-300 hover:text-neutral-100">
            Sign up as a singer
          </Link>
        </div>
      </div>
    </main>
  );
}
