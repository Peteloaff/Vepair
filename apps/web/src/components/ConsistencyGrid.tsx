import type { TrainingConsistency } from "@/lib/types";

// Shared between the singer's own /progress page and the coach's per-singer Progress tab.
export function ConsistencyGrid({ consistency }: { consistency: TrainingConsistency }) {
  return (
    <div className="flex flex-wrap gap-1">
      {consistency.days.map((d) => (
        <div
          key={d.for_date}
          title={`${d.for_date}: ${d.sessions_completed} session${d.sessions_completed === 1 ? "" : "s"}`}
          className={`h-3 w-3 rounded-sm ${
            d.sessions_completed > 0 ? "bg-emerald-500" : "bg-neutral-800"
          }`}
        />
      ))}
    </div>
  );
}
