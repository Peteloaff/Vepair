"use client";

import { useState } from "react";
import type { CoachMessage } from "@/lib/types";

const MAX_MESSAGE_LENGTH = 2000;

/** Shared by both the coach's and the singer's message pages (app/coach/singers/[singerId]/
 * messages/page.tsx and the "Messages" toggle on app/coach-access/page.tsx's ConnectionCard).
 * `currentSender` decides which side of the thread is "mine" (right-aligned) — the same
 * CoachMessage rows render as the coach's own message on one page and the singer's own message
 * on the other. */
export function MessageThread({
  messages,
  currentSender,
  onSend,
  disabledReason,
}: {
  messages: CoachMessage[] | null;
  currentSender: "coach" | "singer";
  onSend: (body: string) => Promise<CoachMessage>;
  /** When set, the composer is replaced with this explanation instead (e.g. a revoked
   * connection) -- the thread above still renders normally. */
  disabledReason?: string | null;
}) {
  const [body, setBody] = useState("");
  const [lastWarning, setLastWarning] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function submit() {
    if (!body.trim()) return;
    setSending(true);
    setError(null);
    setLastWarning(null);
    try {
      const sent = await onSend(body);
      setBody("");
      if (sent.flagged_terms && sent.flagged_terms.length > 0) {
        setLastWarning(sent.flagged_terms);
      }
    } catch {
      setError("Could not send this message. Please try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div>
      <p className="mb-4 rounded-lg border border-amber-900 bg-amber-950/20 px-3 py-2 text-xs text-amber-300">
        Messages are for coaching purposes only — not a medical or clinical record.
      </p>

      <div className="mb-4 space-y-2">
        {messages === null ? (
          <p className="text-sm text-neutral-500">Loading...</p>
        ) : messages.length === 0 ? (
          <p className="text-sm text-neutral-500">No messages yet — say hello.</p>
        ) : (
          messages.map((message) => {
            const isMine = message.sender === currentSender;
            return (
              <div
                key={message.id}
                className={`flex ${isMine ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                    isMine
                      ? "bg-emerald-500 text-neutral-950"
                      : "border border-neutral-800 bg-neutral-900/60 text-neutral-200"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.body}</p>
                  <p
                    className={`mt-1 text-right text-[10px] ${
                      isMine ? "text-neutral-900/70" : "text-neutral-500"
                    }`}
                  >
                    {new Date(message.created_at).toLocaleString()}
                    {message.flagged_terms && message.flagged_terms.length > 0 && (
                      <span className="ml-1">&middot; flagged for review</span>
                    )}
                  </p>
                </div>
              </div>
            );
          })
        )}
      </div>

      {disabledReason ? (
        <p className="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-2 text-xs text-neutral-500">
          {disabledReason}
        </p>
      ) : (
        <div>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value.slice(0, MAX_MESSAGE_LENGTH))}
            rows={2}
            placeholder="Write a message..."
            className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-500"
          />
          <p className="mt-1 text-right text-xs text-neutral-600">
            {body.length}/{MAX_MESSAGE_LENGTH}
          </p>

          {lastWarning && (
            <p className="mb-2 rounded-lg bg-amber-950/30 px-3 py-2 text-xs text-amber-300">
              This message was sent, but contains language that may read as clinical (
              {lastWarning.join(", ")}).
            </p>
          )}
          {error && (
            <p className="mb-2 rounded-lg bg-red-950/50 px-3 py-2 text-xs text-red-300">
              {error}
            </p>
          )}

          <button
            type="button"
            onClick={submit}
            disabled={sending || !body.trim()}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
          >
            {sending ? "Sending..." : "Send"}
          </button>
        </div>
      )}
    </div>
  );
}
