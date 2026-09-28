"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import type { Profile, TrackSetResult, VocalTrack } from "@/lib/types";

const TRACK_COPY: Record<VocalTrack, { title: string; description: string }> = {
  repair: {
    title: "Vocal Repair",
    description:
      "Focused on steadiness and comfort. Exercises stay gentle and range suggestions are paused until your recent data looks consistently stable.",
  },
  improvement: {
    title: "Vocal Improvement",
    description:
      "A step up from Repair — once it's safe for the day, exercises lean more demanding and range suggestions stretch further to help extend your comfortable range.",
  },
};

export function TrackSelector() {
  const { apiFetch } = useAuth();
  const [track, setTrack] = useState<VocalTrack | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingReason, setPendingReason] = useState<string | null>(null);

  useEffect(() => {
    // A brand-new signup has no profile row yet — that's expected, not an error. Track
    // selection must work immediately regardless (see PATCH /profile/track, which creates a
    // bare profile on first choice), so this just leaves `track` at its default (null) rather
    // than blocking the picker.
    apiFetch<Profile>("/api/v1/profile")
      .then((profile) => setTrack(profile.track))
      .catch(() => {})
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function chooseTrack(next: VocalTrack) {
    setSaving(true);
    setError(null);
    setPendingReason(null);
    try {
      const result = await apiFetch<TrackSetResult>("/api/v1/profile/track", {
        method: "PATCH",
        body: { track: next },
      });
      setTrack(result.track);
      setPendingReason(result.plan_pending_reason);
    } catch {
      setError("Could not save your track. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-text-faint">Loading...</p>;
  }

  return (
    <div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {(Object.keys(TRACK_COPY) as VocalTrack[]).map((option) => {
          const copy = TRACK_COPY[option];
          const selected = track === option;
          return (
            <button
              key={option}
              type="button"
              disabled={saving}
              onClick={() => chooseTrack(option)}
              className={`rounded-xl border p-4 text-left disabled:opacity-50 ${
                selected
                  ? "border-accent bg-accent/10"
                  : "border-border-strong hover:bg-surface-2"
              }`}
            >
              <span
                className={`text-sm font-medium ${selected ? "text-accent" : "text-text"}`}
              >
                {copy.title}
                {selected && " (selected)"}
              </span>
              <p className="mt-1 text-xs text-text-dim">{copy.description}</p>
            </button>
          );
        })}
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">{error}</p>
      )}

      {pendingReason && (
        <p className="mt-3 rounded-lg bg-warning-faint px-3 py-2 text-xs text-warning">
          {pendingReason}
        </p>
      )}

      {track && !pendingReason && (
        <p className="mt-3 text-xs text-text-faint">
          <Link href="/vocal-plan" className="text-accent hover:text-accent">
            View your 90-day plan &rarr;
          </Link>
        </p>
      )}

      <p className="mt-3 text-xs text-text-faint">
        This is a self-selected focus, not a diagnosis — VepAIr has no way to know whether you
        ever had a vocal injury. You can change it at any time. See MEDICAL_SAFETY.md.
      </p>
    </div>
  );
}
