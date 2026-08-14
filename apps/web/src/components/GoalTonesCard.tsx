import Link from "next/link";
import type { VocalGoal } from "@/lib/types";

export function GoalTonesCard({ goal }: { goal: VocalGoal | null }) {
  if (goal === null) {
    return <p className="text-sm text-neutral-500">Could not load your target tones.</p>;
  }

  const hasAny = goal.target_low_note || goal.target_avg_note || goal.target_high_note;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span
          className={`rounded-full px-2 py-0.5 text-xs ${
            goal.source === "manual"
              ? "bg-emerald-500/10 text-emerald-300"
              : "bg-neutral-800 text-neutral-400"
          }`}
        >
          {goal.source === "manual" ? "Your target" : "AI-suggested"}
        </span>
        <Link href="/tone-match" className="text-xs text-emerald-400 hover:text-emerald-300">
          Edit &rarr;
        </Link>
      </div>
      {hasAny ? (
        <dl className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <dt className="text-xs text-neutral-500">Low</dt>
            <dd className="text-neutral-200">{goal.target_low_note ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500">Average</dt>
            <dd className="text-neutral-200">{goal.target_avg_note ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-neutral-500">High</dt>
            <dd className="text-neutral-200">{goal.target_high_note ?? "—"}</dd>
          </div>
        </dl>
      ) : (
        <p className="text-sm text-neutral-500">
          Record a{" "}
          <Link href="/vocal-range" className="text-emerald-400 hover:text-emerald-300">
            vocal range test
          </Link>{" "}
          to get AI-suggested target tones, or set your own on{" "}
          <Link href="/tone-match" className="text-emerald-400 hover:text-emerald-300">
            Tone Match
          </Link>
          .
        </p>
      )}
    </div>
  );
}
