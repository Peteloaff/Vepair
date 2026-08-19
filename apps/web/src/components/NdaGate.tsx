"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import type { NdaStatus } from "@/lib/types";

/** Beta NDA click-through, gating the whole authenticated app until accepted. Mounted once in
 * the root layout (not per-page like RequireAuth/RequireAdmin) so it covers every route,
 * including the home page, which has its own auth branching and never uses <RequireAuth>. Only
 * ever activates once `status === "authenticated"` -- logged-out visitors on /login, /terms,
 * etc. are unaffected. An admin turns the whole gate off site-wide from /admin (POST
 * /api/v1/admin/site-settings, nda_required) once the beta phase ends -- no code change or
 * redeploy needed, see app/models.SiteSettings.nda_required's docstring. */
export function NdaGate({ children }: { children: React.ReactNode }) {
  const { status, apiFetch } = useAuth();
  const [nda, setNda] = useState<NdaStatus | null>(null);
  const [checked, setChecked] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    apiFetch<NdaStatus>("/api/v1/auth/nda-status")
      .then(setNda)
      .catch(() => {
        // If the check itself fails, don't lock a real user out of the app over it -- treat as
        // "nothing to accept right now" rather than showing an unrecoverable blocking screen.
        setNda({ required: false, accepted_at: null });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  if (status !== "authenticated") {
    return <>{children}</>;
  }

  if (nda === null) {
    // Deliberately no visible loading state here -- this check is near-instant, and a full-
    // screen "Loading..." on every single page navigation would be worse than the brief gap.
    return null;
  }

  if (!nda.required || nda.accepted_at !== null) {
    return <>{children}</>;
  }

  async function accept() {
    setAccepting(true);
    setError(null);
    try {
      const updated = await apiFetch<NdaStatus>("/api/v1/auth/accept-nda", { method: "POST" });
      setNda(updated);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setAccepting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-950/90 p-4">
      <div className="flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-neutral-800 bg-neutral-900">
        <div className="border-b border-neutral-800 px-6 py-4">
          <h1 className="text-lg font-semibold tracking-tight">Beta Confidentiality Notice</h1>
          <p className="mt-1 text-xs text-neutral-500">
            Please read and accept before continuing.
          </p>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5 text-sm leading-relaxed text-neutral-300">
          <section>
            <h2 className="mb-1.5 text-sm font-medium text-neutral-100">1. What this is</h2>
            <p>
              VepAIr is currently in a private beta. You&apos;re getting access to features,
              designs, and functionality that haven&apos;t been publicly released and may change
              or be removed without notice before any public launch.
            </p>
          </section>

          <section>
            <h2 className="mb-1.5 text-sm font-medium text-neutral-100">2. Confidentiality</h2>
            <p>
              Please don&apos;t share screenshots, recordings, descriptions of unreleased
              features, or other non-public details about VepAIr with anyone outside the beta
              without our permission. It&apos;s fine to talk about your own experience using it
              in general terms — this is about not publishing specifics of a product that
              hasn&apos;t launched yet.
            </p>
          </section>

          <section>
            <h2 className="mb-1.5 text-sm font-medium text-neutral-100">3. Beta software</h2>
            <p>
              Beta software can break. We&apos;ll do our best to keep your data intact, but
              during this phase it&apos;s possible that data gets reset, features change shape,
              or something doesn&apos;t work as expected. This doesn&apos;t change anything in
              the{" "}
              <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-emerald-400 underline hover:text-emerald-300">
                Terms of Service
              </a>{" "}
              — it&apos;s in addition to it, specific to the beta period.
            </p>
          </section>

          <section>
            <h2 className="mb-1.5 text-sm font-medium text-neutral-100">4. Feedback</h2>
            <p>
              If you send us feedback, bug reports, or suggestions, we can use them to improve
              VepAIr without owing you anything extra for that.
            </p>
          </section>

          <section>
            <h2 className="mb-1.5 text-sm font-medium text-neutral-100">5. How long this lasts</h2>
            <p>
              This notice applies for as long as VepAIr is in beta. It stops applying once we
              publicly launch, or whenever we turn this notice off.
            </p>
          </section>
        </div>

        <div className="border-t border-neutral-800 px-6 py-4">
          {error && <p className="mb-2 text-xs text-red-400">{error}</p>}
          <label className="mb-3 flex items-start gap-2 text-xs text-neutral-400">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              className="mt-0.5 rounded border-neutral-700 bg-neutral-900"
            />
            I have read and agree to the beta confidentiality notice above.
          </label>
          <button
            type="button"
            disabled={!checked || accepting}
            onClick={accept}
            className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {accepting ? "Saving..." : "Accept & continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
