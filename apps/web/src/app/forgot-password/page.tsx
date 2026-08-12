"use client";

import { useState } from "react";
import Link from "next/link";
import { requestPasswordReset } from "@/lib/apiClient";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await requestPasswordReset(email);
    } finally {
      // Always show the same confirmation, whether or not the email exists — the API
      // deliberately doesn't reveal that either, to avoid leaking account existence.
      setSubmitting(false);
      setDone(true);
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Reset your password</h1>
        <p className="mb-8 text-sm text-neutral-400">
          We&apos;ll send a reset link if that email has an account.
        </p>

        {done ? (
          <p className="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-3 text-sm text-neutral-300">
            If an account exists for {email}, a reset link is on its way.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
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
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
            >
              {submitting ? "Sending..." : "Send reset link"}
            </button>
          </form>
        )}

        <div className="mt-6 text-xs text-neutral-500">
          <Link href="/login" className="hover:text-neutral-300">
            Back to log in
          </Link>
        </div>
      </div>
    </main>
  );
}
