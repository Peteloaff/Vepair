"use client";

import { useState } from "react";
import Link from "next/link";
import { requestPasswordReset } from "@/lib/apiClient";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await requestPasswordReset(email);
      // Always show the same confirmation, whether or not the email exists — the API
      // deliberately doesn't reveal that either, to avoid leaking account existence. This is
      // only reached once the request actually completed -- a network-level failure (blocked
      // by a browser extension, offline, DNS, etc.) never even reaches the API, so it must not
      // be treated the same as "the API responded, and we're not saying whether it existed."
      setDone(true);
    } catch {
      setError(
        "Could not reach the server. Check your connection (or try disabling browser extensions/ad blockers) and try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Reset your password</h1>
        <p className="mb-8 text-sm text-text-dim">
          We&apos;ll send a reset link if that email has an account.
        </p>

        {done ? (
          <p className="rounded-lg border border-border bg-surface/60 px-3 py-3 text-sm text-text-dim">
            If an account exists for {email}, a reset link is on its way.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <p className="rounded-lg bg-danger-faint px-3 py-2 text-sm text-danger">{error}</p>
            )}
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
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong disabled:opacity-50"
            >
              {submitting ? "Sending..." : "Send reset link"}
            </button>
          </form>
        )}

        <div className="mt-6 text-xs text-text-faint">
          <Link href="/login" className="hover:text-text-dim">
            Back to log in
          </Link>
        </div>
      </div>
    </main>
  );
}
