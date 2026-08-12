"use client";

import { useState } from "react";
import type { RecoveryScore, RecoveryStatus } from "@/lib/types";

const STATUS_STYLES: Record<RecoveryStatus, { ring: string; text: string; dot: string }> = {
  green: { ring: "border-emerald-800", text: "text-emerald-400", dot: "bg-emerald-400" },
  yellow: { ring: "border-amber-800", text: "text-amber-400", dot: "bg-amber-400" },
  red: { ring: "border-red-800", text: "text-red-400", dot: "bg-red-400" },
  unknown: { ring: "border-neutral-800", text: "text-neutral-500", dot: "bg-neutral-600" },
};

const CONFIDENCE_COPY: Record<string, string> = {
  insufficient: "Not enough data today to compute a score.",
  low: "Based on limited data today.",
  moderate: "Based on a moderate amount of data today.",
  high: "Based on a full picture of today's data.",
};

export function RecoveryScoreCard({ score }: { score: RecoveryScore | null }) {
  const [expanded, setExpanded] = useState(false);

  if (score === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  const styles = STATUS_STYLES[score.status];

  return (
    <div>
      <div className="flex items-center gap-4">
        <div
          className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-2 ${styles.ring}`}
        >
          <span className={`text-xl font-semibold tabular-nums ${styles.text}`}>
            {score.score_value ?? "—"}
          </span>
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${styles.dot}`} />
            <span className={`text-sm font-medium ${styles.text}`}>{score.status_label}</span>
          </div>
          <p className="mt-0.5 text-xs text-neutral-500">
            {CONFIDENCE_COPY[score.confidence_label]}
          </p>
        </div>
      </div>

      {score.safety_message && (
        <div className="mt-4 rounded-lg bg-red-950/40 px-3 py-2 text-xs text-red-300">
          {score.safety_message}
        </div>
      )}

      {score.factors.length > 0 && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="mt-4 text-xs text-emerald-400 hover:text-emerald-300"
        >
          {expanded ? "Hide" : "Why did I get this score?"}
        </button>
      )}

      {expanded && (
        <ul className="mt-3 space-y-1.5 text-sm">
          {score.factors.map((f) => (
            <li key={f.text} className="flex items-start gap-2">
              <span
                className={f.direction === "positive" ? "text-emerald-400" : "text-amber-400"}
              >
                {f.direction === "positive" ? "+" : "−"}
              </span>
              <span className="text-neutral-300">{f.text}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-4 text-xs text-neutral-600">
        This is a training/recovery indicator, not a medical score and not medical clearance —
        see MEDICAL_SAFETY.md.
      </p>
    </div>
  );
}
