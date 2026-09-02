"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth-context";
import { API_BASE } from "@/lib/apiClient";
import type { VoiceSessionWithRecordings } from "@/lib/types";

function PlayableRecording({
  recording,
  onDeleted,
}: {
  recording: VoiceSessionWithRecordings["recordings"][number];
  onDeleted: () => void;
}) {
  const { apiFetch } = useAuth();
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function play() {
    if (audioUrl) return;
    setLoading(true);
    setError(false);
    try {
      const token = localStorage.getItem("vepair_access_token");
      const res = await fetch(`${API_BASE}/api/v1/recordings/${recording.id}/audio`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("fetch failed");
      const blob = await res.blob();
      setAudioUrl(URL.createObjectURL(blob));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  async function remove() {
    if (
      !window.confirm(
        "Permanently delete this recording? This removes the audio and its measurements — it can't be undone, and it will no longer count toward your trends."
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      await apiFetch(`/api/v1/recordings/${recording.id}`, { method: "DELETE" });
      onDeleted();
    } catch {
      setDeleting(false);
    }
  }

  return (
    <li className="flex items-center justify-between text-sm">
      <span className="text-neutral-300">{recording.sample_type}</span>
      <div className="flex items-center gap-2">
        {!recording.audio_available ? (
          <span className="text-xs text-neutral-600">
            Audio no longer available — auto-removed under the data retention policy
          </span>
        ) : audioUrl ? (
          <audio controls autoPlay src={audioUrl} className="h-8" />
        ) : (
          <button
            type="button"
            onClick={play}
            disabled={loading}
            className="rounded-lg border border-neutral-700 px-3 py-1 text-xs hover:bg-neutral-800 disabled:opacity-50"
          >
            {loading ? "Loading..." : error ? "Retry" : "Play"}
          </button>
        )}
        <button
          type="button"
          onClick={remove}
          disabled={deleting}
          className="text-xs text-neutral-500 hover:text-red-300 disabled:opacity-50"
        >
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </li>
  );
}

function RecordingsContent() {
  const { apiFetch } = useAuth();
  const [sessions, setSessions] = useState<VoiceSessionWithRecordings[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiFetch<VoiceSessionWithRecordings[]>("/api/v1/voice-sessions");
      setSessions(data);
    } catch {
      setError("Could not load your recordings.");
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error && sessions === null) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (sessions === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  const sessionsWithRecordings = sessions.filter((s) => s.recordings.length > 0);

  return (
    <div className="mx-auto w-full max-w-2xl">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Recordings</h1>
      <p className="mb-6 text-sm text-neutral-400">
        Raw audio is automatically removed after a retention period — your measurements and
        trends are unaffected either way. Delete a recording any time to remove it, and its
        measurements, immediately.
      </p>

      {sessionsWithRecordings.length === 0 ? (
        <p className="text-sm text-neutral-500">No recordings yet.</p>
      ) : (
        <div className="space-y-4">
          {sessionsWithRecordings.map((session) => (
            <div
              key={session.id}
              className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4"
            >
              <p className="mb-2 text-xs text-neutral-500">
                {new Date(session.started_at).toLocaleString()}
              </p>
              <ul className="space-y-2">
                {session.recordings.map((recording) => (
                  <PlayableRecording key={recording.id} recording={recording} onDeleted={load} />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8">
        <Link href="/" className="text-xs text-neutral-500 hover:text-neutral-300">
          &larr; Back to dashboard
        </Link>
      </div>
    </div>
  );
}

export default function RecordingsPage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <RecordingsContent />
      </main>
    </RequireAuth>
  );
}
