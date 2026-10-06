"use client";

import { useId, useState } from "react";
import type { RecoveryScore, RecoveryStatus } from "@/lib/types";

const STATUS_STYLES: Record<RecoveryStatus, { chip: string; dot: string }> = {
  green: { chip: "bg-ok-faint text-ok", dot: "bg-ok" },
  yellow: { chip: "bg-warning-faint text-warning", dot: "bg-warning" },
  red: { chip: "bg-danger-faint text-danger", dot: "bg-danger" },
  unknown: { chip: "bg-surface-2 text-text-faint", dot: "bg-text-faint" },
};

// A 270-degree gauge (open at the bottom), drawn with stroke-dasharray so the filled arc is
// exactly score/100 of the track. The gradient is the brand cyan -> blue -> violet.
const RADIUS = 50;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const TRACK = CIRCUMFERENCE * 0.75;

function ScoreRing({ value }: { value: number | null }) {
  const gradientId = useId();
  const filled = value === null ? 0 : TRACK * (Math.max(0, Math.min(100, value)) / 100);
  return (
    <div className="relative h-40 w-40 shrink-0 sm:h-44 sm:w-44">
      <svg viewBox="0 0 120 120" className="h-full w-full" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} gradientUnits="userSpaceOnUse" x1="14" y1="106" x2="106" y2="14">
            <stop offset="0" stopColor="var(--color-accent)" />
            <stop offset="0.55" stopColor="var(--color-blue)" />
            <stop offset="1" stopColor="var(--color-violet)" />
          </linearGradient>
        </defs>
        <circle
          cx="60"
          cy="60"
          r={RADIUS}
          fill="none"
          stroke="var(--color-border-strong)"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${TRACK} ${CIRCUMFERENCE}`}
          transform="rotate(135 60 60)"
        />
        {filled > 0 && (
          <circle
            cx="60"
            cy="60"
            r={RADIUS}
            fill="none"
            stroke={`url(#${gradientId})`}
            strokeWidth="9"
            strokeLinecap="round"
            strokeDasharray={`${filled} ${CIRCUMFERENCE}`}
            transform="rotate(135 60 60)"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center pb-1.5">
        <span className="font-display text-5xl leading-none tracking-tight tabular-nums">
          {value ?? "—"}
        </span>
        <span className="mt-0.5 text-xs text-text-faint">of 100</span>
      </div>
    </div>
  );
}

const CONFIDENCE_COPY: Record<string, string> = {
  insufficient: "Not enough data today to compute a score.",
  low: "Based on limited data today.",
  moderate: "Based on a moderate amount of data today.",
  high: "Based on a full picture of today's data.",
};

export function RecoveryScoreCard({ score }: { score: RecoveryScore | null }) {
  const [expanded, setExpanded] = useState(false);

  if (score === null) {
    return <p className="text-sm text-text-faint">Loading...</p>;
  }

  const styles = STATUS_STYLES[score.status];

  return (
    <div>
      <div className="flex flex-wrap items-center gap-5">
        <ScoreRing value={score.score_value} />
        <div className="min-w-48 flex-1">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${styles.chip}`}
          >
            <span className={`h-2 w-2 rounded-full ${styles.dot}`} />
            {score.status_label}
          </span>
          <p className="mt-3 text-sm text-text-dim">{CONFIDENCE_COPY[score.confidence_label]}</p>
        </div>
      </div>

      {score.safety_message && (
        <div className="mt-4 rounded-lg bg-danger-faint px-3 py-2 text-xs text-danger">
          {score.safety_message}
        </div>
      )}

      {score.factors.length > 0 && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="mt-4 text-xs text-accent hover:text-accent-strong"
        >
          {expanded ? "Hide" : "Why did I get this score?"}
        </button>
      )}

      {expanded && (
        <ul className="mt-3 space-y-1.5 text-sm">
          {score.factors.map((f) => (
            <li key={f.text} className="flex items-start gap-2">
              <span
                className={f.direction === "positive" ? "text-accent" : "text-warning"}
              >
                {f.direction === "positive" ? "+" : "−"}
              </span>
              <span className="text-text-dim">{f.text}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-4 text-xs text-text-faint">
        This is a training/recovery indicator, not a medical score and not medical clearance —
        see MEDICAL_SAFETY.md.
      </p>
    </div>
  );
}
