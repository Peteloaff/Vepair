"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import type { ConsentStatus } from "@/lib/types";

export function NotificationsConsent() {
  const { apiFetch } = useAuth();
  const [granted, setGranted] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ConsentStatus>("/api/v1/consent/notifications")
      .then((status) => setGranted(status.granted))
      .catch(() => {})
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function choose(value: boolean) {
    setSaving(true);
    setError(null);
    try {
      const status = await apiFetch<ConsentStatus>("/api/v1/consent/notifications", {
        method: "PUT",
        body: { granted: value },
      });
      setGranted(status.granted);
    } catch {
      setError("Could not save your choice. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  return (
    <div>
      <span className="mb-1 block text-xs text-neutral-400">
        Would you like to receive notifications and updates from VepAIr? If you opt in, we may
        use your contact information to reach you — see PRIVACY.md. You can change this any
        time.
      </span>
      <div className="flex gap-2">
        {(
          [
            ["Yes", true],
            ["No", false],
          ] as const
        ).map(([text, val]) => (
          <button
            key={text}
            type="button"
            disabled={saving}
            onClick={() => choose(val)}
            className={`rounded-lg border px-3 py-1.5 text-xs disabled:opacity-50 ${
              granted === val
                ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                : "border-neutral-700 text-neutral-400 hover:bg-neutral-800"
            }`}
          >
            {text}
          </button>
        ))}
      </div>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
    </div>
  );
}
