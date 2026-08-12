"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { TrackSelector } from "@/components/TrackSelector";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/apiClient";
import type { Profile, ProfileInput } from "@/lib/types";

const EMPTY_FORM: ProfileInput = {
  voice_use: "",
  is_singer: null,
  musical_style: "",
  practice_frequency: "",
  perceived_vocal_range: "",
  goals: "",
  vocal_coaching_history: "",
  under_professional_care: null,
};

function TriState({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean | null;
  onChange: (v: boolean | null) => void;
}) {
  return (
    <div>
      <span className="mb-1 block text-xs text-neutral-400">{label}</span>
      <div className="flex gap-2">
        {(
          [
            ["Yes", true],
            ["No", false],
            ["Prefer not to say", null],
          ] as const
        ).map(([text, val]) => (
          <button
            key={text}
            type="button"
            onClick={() => onChange(val)}
            className={`rounded-lg border px-3 py-1.5 text-xs ${
              value === val
                ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                : "border-neutral-700 text-neutral-400 hover:bg-neutral-800"
            }`}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

function OnboardingForm() {
  const { apiFetch } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isNewSignup = searchParams.get("new") === "1";
  const [form, setForm] = useState<ProfileInput>(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiFetch<Profile>("/api/v1/profile")
      .then((profile) => {
        setForm({
          voice_use: profile.voice_use ?? "",
          is_singer: profile.is_singer,
          musical_style: profile.musical_style ?? "",
          practice_frequency: profile.practice_frequency ?? "",
          perceived_vocal_range: profile.perceived_vocal_range ?? "",
          goals: profile.goals ?? "",
          vocal_coaching_history: profile.vocal_coaching_history ?? "",
          under_professional_care: profile.under_professional_care,
        });
      })
      .catch((err) => {
        // No profile yet is expected for a brand-new account — start from a blank form.
        if (!(err instanceof ApiError && err.code === "profile_not_found")) {
          setError("Could not load your profile.");
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function setText(key: keyof ProfileInput, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const payload: ProfileInput = {
        ...form,
        voice_use: form.voice_use || null,
        musical_style: form.musical_style || null,
        practice_frequency: form.practice_frequency || null,
        perceived_vocal_range: form.perceived_vocal_range || null,
        goals: form.goals || null,
        vocal_coaching_history: form.vocal_coaching_history || null,
      };
      await apiFetch<Profile>("/api/v1/profile", { method: "PUT", body: payload });
      setSaved(true);
    } catch {
      setError("Could not save your profile. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label htmlFor="voice_use" className="mb-1 block text-xs text-neutral-400">
          How do you mainly use your voice?
        </label>
        <select
          id="voice_use"
          value={form.voice_use ?? ""}
          onChange={(e) => setText("voice_use", e.target.value)}
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        >
          <option value="">Prefer not to say</option>
          <option value="singing">Primarily singing</option>
          <option value="speaking">Primarily speaking</option>
          <option value="both">Both, about equally</option>
          <option value="casual">Casual / occasional</option>
        </select>
      </div>

      <TriState
        label="Do you consider yourself a singer?"
        value={form.is_singer}
        onChange={(v) => setForm((f) => ({ ...f, is_singer: v }))}
      />

      <div>
        <label htmlFor="musical_style" className="mb-1 block text-xs text-neutral-400">
          Musical style(s)
        </label>
        <input
          id="musical_style"
          value={form.musical_style ?? ""}
          onChange={(e) => setText("musical_style", e.target.value)}
          placeholder="e.g. rock, metal, musical theatre"
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
      </div>

      <div>
        <label htmlFor="practice_frequency" className="mb-1 block text-xs text-neutral-400">
          How often do you typically practice or perform?
        </label>
        <select
          id="practice_frequency"
          value={form.practice_frequency ?? ""}
          onChange={(e) => setText("practice_frequency", e.target.value)}
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        >
          <option value="">Prefer not to say</option>
          <option value="daily">Daily</option>
          <option value="a_few_times_a_week">A few times a week</option>
          <option value="weekly">Weekly</option>
          <option value="rarely">Rarely</option>
          <option value="never">Never</option>
        </select>
      </div>

      <div>
        <label htmlFor="perceived_vocal_range" className="mb-1 block text-xs text-neutral-400">
          How would you describe your current vocal range?
        </label>
        <input
          id="perceived_vocal_range"
          value={form.perceived_vocal_range ?? ""}
          onChange={(e) => setText("perceived_vocal_range", e.target.value)}
          placeholder="e.g. tenor, alto, or just describe it"
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
      </div>

      <div>
        <label htmlFor="goals" className="mb-1 block text-xs text-neutral-400">
          What are your goals with VepAIr?
        </label>
        <textarea
          id="goals"
          value={form.goals ?? ""}
          onChange={(e) => setText("goals", e.target.value)}
          rows={3}
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
      </div>

      <div>
        <label
          htmlFor="vocal_coaching_history"
          className="mb-1 block text-xs text-neutral-400"
        >
          Have you worked with a vocal coach or speech therapist before?
        </label>
        <textarea
          id="vocal_coaching_history"
          value={form.vocal_coaching_history ?? ""}
          onChange={(e) => setText("vocal_coaching_history", e.target.value)}
          rows={2}
          className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
      </div>

      <TriState
        label="Are you currently under the care of a vocal coach, ENT, or speech-language pathologist?"
        value={form.under_professional_care}
        onChange={(v) => setForm((f) => ({ ...f, under_professional_care: v }))}
      />

      {error && (
        <p className="rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">{error}</p>
      )}
      {saved && (
        <p className="rounded-lg bg-emerald-950/40 px-3 py-2 text-xs text-emerald-300">
          Saved.
        </p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          type="button"
          onClick={() =>
            router.push(
              isNewSignup ? `/record?next=${encodeURIComponent("/vocal-range")}` : "/"
            )
          }
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800"
        >
          {isNewSignup ? "Done — record your baseline →" : "Done"}
        </button>
      </div>
    </form>
  );
}

export default function OnboardingPage() {
  return (
    <RequireAuth>
      <main className="mx-auto w-full max-w-lg flex-1 px-6 py-12">
        <h1 className="mb-1 text-2xl font-semibold tracking-tight">Tell us about your voice</h1>
        <p className="mb-8 text-sm text-neutral-400">
          Every question here is optional — skip anything you&apos;d rather not answer. This
          helps VepAIr personalize your baseline, not diagnose anything.
        </p>

        <section className="mb-10">
          <h2 className="mb-1 text-sm font-medium text-neutral-200">
            What brings you to VepAIr?
          </h2>
          <p className="mb-4 text-xs text-neutral-500">
            Once you&apos;ve recorded a voice sample and a vocal range test, VepAIr builds a
            90-day plan specific to your own measured range.
          </p>
          <TrackSelector />
        </section>

        <Suspense fallback={null}>
          <OnboardingForm />
        </Suspense>
      </main>
    </RequireAuth>
  );
}
