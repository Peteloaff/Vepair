"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { confirmPasswordReset, ApiError } from "@/lib/apiClient";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") ?? "");
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
      <p className="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-3 text-sm text-neutral-300">
        Password updated. Redirecting to log in...
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="token" className="mb-1 block text-xs text-neutral-400">
          Reset token
        </label>
        <input
          id="token"
          required
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
        <p className="mt-1 text-xs text-neutral-500">
          Paste the token from the reset email (dev: check the API server log).
        </p>
      </div>

      <div>
        <label htmlFor="newPassword" className="mb-1 block text-xs text-neutral-400">
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
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
      </div>

      {error && (
        <p className="rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
      >
        {submitting ? "Updating..." : "Update password"}
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Set a new password</h1>
        <p className="mb-8 text-sm text-neutral-400">
          Enter the reset token you received and choose a new password.
        </p>

        <Suspense fallback={null}>
          <ResetPasswordForm />
        </Suspense>

        <div className="mt-6 text-xs text-neutral-500">
          <Link href="/login" className="hover:text-neutral-300">
            Back to log in
          </Link>
        </div>
      </div>
    </main>
  );
}
