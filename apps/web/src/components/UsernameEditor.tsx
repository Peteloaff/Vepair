"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { ApiError, type AuthUser } from "@/lib/apiClient";

/** A self-chosen display handle, distinct from email — optional, and not used anywhere else in
 * the app yet. Lives on the Profile page since it's account identity, not a voice-training
 * answer (those live in UserProfile / ProfileInput, a separate concern). */
export function UsernameEditor() {
  const { apiFetch } = useAuth();
  const [current, setCurrent] = useState<string | null | undefined>(undefined);
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch<AuthUser>("/api/v1/auth/me")
      .then((me) => {
        setCurrent(me.username);
        setValue(me.username ?? "");
      })
      .catch(() => setCurrent(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const trimmed = value.trim();
      const updated = await apiFetch<AuthUser>("/api/v1/auth/username", {
        method: "PATCH",
        body: { username: trimmed === "" ? null : trimmed },
      });
      setCurrent(updated.username);
      setValue(updated.username ?? "");
      setSaved(true);
    } catch (err) {
      if (err instanceof ApiError && err.code === "username_taken") {
        setError("That username is already taken.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Usernames must be 3–30 characters: letters, numbers, and underscores only.");
      } else {
        setError("Could not save your username. Please try again.");
      }
    } finally {
      setSaving(false);
    }
  }

  if (current === undefined) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <label htmlFor="username" className="mb-1 block text-xs text-neutral-400">
        Username <span className="text-neutral-600">(optional)</span>
      </label>
      <div className="flex flex-wrap gap-2">
        <input
          id="username"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setSaved(false);
          }}
          placeholder="e.g. singer_pete"
          minLength={3}
          maxLength={30}
          className="w-full max-w-xs rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
      <p className="text-xs text-neutral-500">
        {current ? (
          <>
            Currently <span className="text-neutral-300">{current}</span>. Clear the field and
            save to remove it.
          </>
        ) : (
          "Letters, numbers, and underscores only — 3 to 30 characters."
        )}
      </p>
      {error && (
        <p className="rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
      )}
      {saved && (
        <p className="rounded-lg bg-emerald-950/40 px-3 py-2 text-xs text-emerald-300">Saved.</p>
      )}
    </form>
  );
}
