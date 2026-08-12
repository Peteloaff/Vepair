"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/apiClient";

function InviteFormContent() {
  const { apiFetch } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiFetch("/api/v1/coach/invites", {
        method: "POST",
        body: { singer_email: email, message: message || null },
      });
      router.push("/coach");
    } catch (err) {
      if (err instanceof ApiError && err.code === "singer_not_found") {
        setError("No VepAIr account exists for this email yet — ask them to sign up first.");
      } else if (err instanceof ApiError && err.code === "invite_already_pending") {
        setError("An invite to this singer is already pending.");
      } else {
        setError("Could not send this invite. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-sm">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Invite a singer</h1>
      <p className="mb-8 text-sm text-neutral-400">
        They must already have a VepAIr account, and must explicitly accept before you see
        anything of theirs.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="email" className="mb-1 block text-xs text-neutral-400">
            Singer&apos;s email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
          />
        </div>

        <div>
          <label htmlFor="message" className="mb-1 block text-xs text-neutral-400">
            Message (optional)
          </label>
          <textarea
            id="message"
            rows={3}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
          />
        </div>

        {error && (
          <p className="rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
        )}

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
          >
            {submitting ? "Sending..." : "Send invite"}
          </button>
          <Link
            href="/coach"
            className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
          >
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}

export default function CoachInvitePage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-6 py-10">
          <InviteFormContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
