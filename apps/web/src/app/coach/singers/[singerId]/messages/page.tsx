"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireCoach } from "@/components/RequireCoach";
import { MessageThread } from "@/components/MessageThread";
import { useAuth } from "@/lib/auth-context";
import type { CoachMessage } from "@/lib/types";

function MessagesContent() {
  const { apiFetch } = useAuth();
  const params = useParams<{ singerId: string }>();
  const [messages, setMessages] = useState<CoachMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiFetch<CoachMessage[]>(
        `/api/v1/coach/singers/${params.singerId}/messages`
      );
      setMessages(data);
    } catch {
      setError("Could not load messages with this Vrotégé.");
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.singerId]);

  async function send(body: string): Promise<CoachMessage> {
    const created = await apiFetch<CoachMessage>(
      `/api/v1/coach/singers/${params.singerId}/messages`,
      { method: "POST", body: { body } }
    );
    await load();
    return created;
  }

  if (error && messages === null) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  return (
    <div className="mx-auto w-full max-w-2xl">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Messages</h1>

      <MessageThread messages={messages} currentSender="coach" onSend={send} />

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

export default function CoachMessagesPage() {
  return (
    <RequireAuth>
      <RequireCoach>
        <main className="flex flex-1 flex-col px-6 py-10">
          <MessagesContent />
        </main>
      </RequireCoach>
    </RequireAuth>
  );
}
