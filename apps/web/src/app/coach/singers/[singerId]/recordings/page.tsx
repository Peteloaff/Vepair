"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { useAuth } from "@/lib/auth-context";
import { API_BASE } from "@/lib/apiClient";
import type { CoachVoiceSession } from "@/lib/types";

function PlayableRecording({
  singerId,
  recordingId,
  sampleType,
}: {
  singerId: string;
  recordingId: string;
  sampleType: string;
}) {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  async function play() {
    if (audioUrl) return;
    setLoading(true);
    setError(false);
    try {
      const token = localStorage.getItem("vepair_access_token");
      const res = await fetch(
        `${API_BASE}/api/v1/coach/singers/${singerId}/recordings/${recordingId}/audio`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error("fetch failed");
      const blob = await res.blob();
      setAudioUrl(URL.createObjectURL(blob));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <li className="flex items-center justify-between text-sm">
      <span className="text-neutral-300">{sampleType}</span>
      {audioUrl ? (
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
    </li>
  );
}

function RecordingsContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ singerId: string }>();
  const [sessions, setSessions] = useState<CoachVoiceSession[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<CoachVoiceSession[]>(`/api/v1/coach/singers/${params.singerId}/recordings`)
      .then(setSessions)
      .catch(() =>
        setError(
          "Could not load this singer's recordings — check they've shared the recordings category with you."
        )
      );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.singerId]);

  if (error) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (sessions === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  return (
    <div className="mx-auto w-full max-w-2xl">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Recordings</h1>

      {sessions.length === 0 ? (
        <p className="text-sm text-neutral-500">No recordings yet.</p>
      ) : (
        <div className="space-y-4">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4"
            >
              <p className="mb-2 text-xs text-neutral-500">
                {new Date(session.started_at).toLocaleString()}
              </p>
              <ul className="space-y-2">
                {session.recordings.map((recording) => (
                  <PlayableRecording
                    key={recording.id}
                    singerId={params.singerId}
                    recordingId={recording.id}
                    sampleType={recording.sample_type}
                  />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8">
        <Link
          href={`/coach/singers/${params.singerId}`}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          &larr; Back to dashboard
        </Link>
      </div>
    </div>
  );
}

export default function CoachSingerRecordingsPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-6 py-10">
          <RecordingsContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
