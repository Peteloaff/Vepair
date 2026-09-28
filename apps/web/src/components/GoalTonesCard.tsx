import Link from "next/link";
import type { VocalGoal } from "@/lib/types";

export function GoalTonesCard({ goal }: { goal: VocalGoal | null }) {
  if (goal === null) {
    return <p className="text-sm text-text-faint">Could not load your target tones.</p>;
  }

  const hasAny = goal.target_low_note || goal.target_avg_note || goal.target_high_note;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span
          className={`rounded-full px-2 py-0.5 text-xs ${
            goal.source === "manual"
              ? "bg-accent/10 text-accent"
              : "bg-surface-2 text-text-dim"
          }`}
        >
          {goal.source === "manual" ? "Your target" : "AI-suggested"}
        </span>
        <Link href="/tone-match" className="text-xs text-accent hover:text-accent">
          Edit &rarr;
        </Link>
      </div>
      {hasAny ? (
        <dl className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <dt className="text-xs text-text-faint">Low</dt>
            <dd className="text-text">{goal.target_low_note ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-faint">Average</dt>
            <dd className="text-text">{goal.target_avg_note ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-faint">High</dt>
            <dd className="text-text">{goal.target_high_note ?? "—"}</dd>
          </div>
        </dl>
      ) : (
        <p className="text-sm text-text-faint">
          Record a{" "}
          <Link href="/vocal-range" className="text-accent hover:text-accent">
            vocal range test
          </Link>{" "}
          to get AI-suggested target tones, or set your own on{" "}
          <Link href="/tone-match" className="text-accent hover:text-accent">
            Tone Match
          </Link>
          .
        </p>
      )}
    </div>
  );
}
