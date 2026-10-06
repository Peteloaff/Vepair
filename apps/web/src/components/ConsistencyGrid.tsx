import type { TrainingConsistency } from "@/lib/types";

const LEVEL_CLASS = [
  "bg-surface-2 border border-border",
  "bg-accent/30",
  "bg-accent/60",
  "bg-accent",
] as const;

// Shared between the singer's own /progress page and the coach's per-singer Progress tab.
// One square per day, shaded by how many sessions were completed that day (0, 1, 2, 3+).
export function ConsistencyGrid({ consistency }: { consistency: TrainingConsistency }) {
  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {consistency.days.map((d) => (
          <div
            key={d.for_date}
            title={`${d.for_date}: ${d.sessions_completed} session${d.sessions_completed === 1 ? "" : "s"}`}
            className={`h-5 w-5 rounded-md ${LEVEL_CLASS[Math.min(d.sessions_completed, 3)]}`}
          />
        ))}
      </div>
      <div className="mt-3 flex items-center gap-1.5 text-xs text-text-faint">
        <span>Less</span>
        {LEVEL_CLASS.map((c) => (
          <span key={c} className={`h-3.5 w-3.5 rounded ${c}`} />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}
