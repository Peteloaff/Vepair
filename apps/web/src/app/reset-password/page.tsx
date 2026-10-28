"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { confirmPasswordReset, ApiError } from "@/lib/apiClient";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // The emailed link carries the token, so the person only ever types a password. The token
  // field is a fallback for a link that lost its query string.
  const tokenFromLink = searchParams.get("token") ?? "";
  const [token, setToken] = useState(tokenFromLink);
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await confirmPasswordReset(token, newPassword);
      setDone(true);
      setTimeout(() => router.replace("/login"), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <p className="rounded-lg border border-border bg-surface/60 px-3 py-3 text-sm text-text-dim">
        Password saved. Taking you to log in...
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {!tokenFromLink && (
        <div>
          <label htmlFor="token" className="mb-1 block text-xs text-text-dim">
            Code from your email
          </label>
          <input
            id="token"
            required
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-base outline-none focus:border-accent sm:text-sm"
          />
        </div>
      )}

      <div>
        <label htmlFor="newPassword" className="mb-1 block text-xs text-text-dim">
          New password
        </label>
        <input
          id="newPassword"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="w-full rounded-lg border border-border-strong bg-surface px-3 py-2 text-base outline-none focus:border-accent sm:text-sm"
        />
        <p className="mt-1 text-xs text-text-faint">At least 8 characters.</p>
      </div>

      {error && (
        <p className="rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">
          {error}{" "}
          <Link href="/forgot-password" className="underline">
            Get a new link
          </Link>
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:bg-accent-strong disabled:opacity-50"
      >
        {submitting ? "Saving..." : "Save password"}
      </button>
    </form>
  );
}

function Heading() {
  // A new team member's emailed link adds ?welcome=1.
  const welcome = useSearchParams().get("welcome") === "1";
  return (
    <>
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">
        {welcome ? "Welcome to VepAIr" : "Choose a new password"}
      </h1>
      <p className="mb-8 text-sm text-text-dim">
        {welcome
          ? "Choose a password to finish setting up your coach account."
          : "Choose a new password for your account."}
      </p>
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <Suspense fallback={null}>
          <Heading />
          <ResetPasswordForm />
        </Suspense>

        <div className="mt-6 text-xs text-text-faint">
          <Link href="/login" className="hover:text-text-dim">
            Back to log in
          </Link>
        </div>
      </div>
    </main>
  );
}
