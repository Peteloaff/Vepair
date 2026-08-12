import { forwardRef } from "react";
import type { NumericProgress, ProgressSnapshot, RangeProgress } from "@/lib/types";

function sign(n: number): string {
  return n > 0 ? "+" : n < 0 ? "−" : "";
}

const BASIS_LABEL: Record<string, string> = {
  established_baseline: "vs. your established baseline",
  first_valid_session: "vs. your first recorded session",
};

function MetricBlock({
  label,
  start,
  now,
  delta,
  unit,
  basis,
}: {
  label: string;
  start: string;
  now: string;
  delta: string;
  unit: string;
  basis: string;
}) {
  return (
    <div className="border-b border-neutral-800 py-6">
      <div className="flex items-baseline justify-between">
        <span className="text-2xl text-neutral-400">{label}</span>
        <span className="text-xl text-neutral-600">{BASIS_LABEL[basis] ?? ""}</span>
      </div>
      <div className="mt-2 flex items-baseline justify-between">
        <div>
          <span className="text-lg text-neutral-500">START </span>
          <span className="text-3xl font-semibold text-neutral-300">{start}</span>
          <span className="mx-4 text-2xl text-neutral-600">→</span>
          <span className="text-lg text-neutral-500">NOW </span>
          <span className="text-3xl font-semibold text-neutral-50">{now}</span>
        </div>
        <span className="text-3xl font-semibold text-emerald-300">
          {delta}
          {unit}
        </span>
      </div>
    </div>
  );
}

function numericBlock(label: string, p: NumericProgress, unit: string) {
  return (
    <MetricBlock
      key={label}
      label={label}
      start={`${p.start_value}${unit}`}
      now={`${p.now_value}${unit}`}
      delta={`${sign(p.delta)}${Math.abs(p.delta)}`}
      unit={unit}
      basis={p.start_basis}
    />
  );
}

function rangeBlock(r: RangeProgress) {
  return (
    <MetricBlock
      key="range"
      label="Comfortable Range"
      start={`${r.start_low_note ?? "—"} → ${r.start_high_note ?? "—"}`}
      now={`${r.now_low_note ?? "—"} → ${r.now_high_note ?? "—"}`}
      delta={
        r.high_note_semitone_delta !== null
          ? `${sign(r.high_note_semitone_delta)}${Math.abs(r.high_note_semitone_delta)}`
          : "—"
      }
      unit={r.high_note_semitone_delta !== null ? " semitones" : ""}
      basis={r.start_basis}
    />
  );
}

export const ProgressCard = forwardRef<HTMLDivElement, { snapshot: ProgressSnapshot }>(
  function ProgressCard({ snapshot }, ref) {
    return (
      <div
        ref={ref}
        style={{ width: 1080, height: 1920 }}
        className="flex flex-col bg-neutral-950 px-16 py-20"
      >
        <p className="text-3xl font-medium tracking-[0.3em] text-emerald-400">MY PROGRESS</p>
        <p className="mt-2 text-2xl text-neutral-500">HOW HAS MY VOICE CHANGED?</p>

        {snapshot.insufficient_data ? (
          <div className="mt-24 flex flex-1 flex-col items-center justify-center text-center">
            <p className="text-4xl font-semibold text-neutral-200">BUILDING YOUR BASELINE</p>
            <p className="mt-6 text-2xl text-neutral-500">
              {snapshot.valid_session_count} valid session
              {snapshot.valid_session_count === 1 ? "" : "s"} recorded.
            </p>
            <p className="mt-2 text-2xl text-neutral-500">
              Continue using VepAIr to unlock progress comparisons.
            </p>
          </div>
        ) : (
          <div className="mt-12 flex-1">
            {snapshot.comfortable_range && rangeBlock(snapshot.comfortable_range)}
            {snapshot.pitch_stability_pct &&
              numericBlock("Pitch Stability", snapshot.pitch_stability_pct, "%")}
            {snapshot.vocal_endurance_seconds &&
              numericBlock("Vocal Endurance", snapshot.vocal_endurance_seconds, " sec")}
            {snapshot.reported_fatigue &&
              numericBlock("Reported Fatigue", snapshot.reported_fatigue, " /10")}

            <div className="mt-8 grid grid-cols-3 gap-6 text-center">
              <div>
                <p className="text-4xl font-bold text-neutral-50">{snapshot.days_tracked}</p>
                <p className="mt-1 text-xl text-neutral-500">Days Tracked</p>
              </div>
              <div>
                <p className="text-4xl font-bold text-neutral-50">{snapshot.sessions_completed}</p>
                <p className="mt-1 text-xl text-neutral-500">Sessions Completed</p>
              </div>
              <div>
                <p className="text-4xl font-bold text-neutral-50">
                  {snapshot.training_compliance_pct !== null
                    ? `${Math.round(snapshot.training_compliance_pct)}%`
                    : "—"}
                </p>
                <p className="mt-1 text-xl text-neutral-500">Training Compliance</p>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-baseline justify-between">
          <span className="text-3xl font-semibold tracking-tight text-neutral-100">VepAIr</span>
          <span className="text-2xl text-neutral-500">
            {new Date(snapshot.for_date).toLocaleDateString(undefined, {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </span>
        </div>
      </div>
    );
  }
);
