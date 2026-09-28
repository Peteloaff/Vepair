import { forwardRef } from "react";
import type { TodaySnapshot } from "@/lib/types";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between border-b border-border py-4">
      <span className="text-2xl text-text-dim">{label}</span>
      <span className="text-3xl font-semibold tabular-nums text-text">{value}</span>
    </div>
  );
}

export const TodayCard = forwardRef<HTMLDivElement, { snapshot: TodaySnapshot }>(
  function TodayCard({ snapshot }, ref) {
    const rows: { label: string; value: string }[] = [];
    if (snapshot.comfortable_low_note && snapshot.comfortable_high_note) {
      rows.push({
        label: "Comfortable Range",
        value: `${snapshot.comfortable_low_note} → ${snapshot.comfortable_high_note}`,
      });
    }
    if (snapshot.range_span_semitones !== null) {
      rows.push({ label: "Range Span", value: `${snapshot.range_span_semitones} semitones` });
    }
    if (snapshot.pitch_stability_pct !== null) {
      rows.push({ label: "Pitch Stability", value: `${Math.round(snapshot.pitch_stability_pct)}%` });
    }
    if (snapshot.vocal_endurance_seconds !== null) {
      rows.push({
        label: "Vocal Endurance",
        value: `${snapshot.vocal_endurance_seconds.toFixed(1)} sec`,
      });
    }
    if (snapshot.reported_fatigue !== null) {
      rows.push({ label: "Reported Fatigue", value: `${snapshot.reported_fatigue} / 10` });
    }
    if (snapshot.vocal_load) {
      rows.push({
        label: "Vocal Load",
        value: snapshot.vocal_load[0].toUpperCase() + snapshot.vocal_load.slice(1),
      });
    }
    if (snapshot.measurement_confidence_label) {
      rows.push({
        label: "Measurement Confidence",
        value:
          snapshot.measurement_confidence_label[0].toUpperCase() +
          snapshot.measurement_confidence_label.slice(1),
      });
    }
    if (snapshot.training_completed_pct !== null) {
      rows.push({
        label: "Training Completed",
        value: `${Math.round(snapshot.training_completed_pct)}%`,
      });
    }

    return (
      <div
        ref={ref}
        style={{ width: 1080, height: 1920 }}
        className="flex flex-col bg-canvas px-16 py-20"
      >
        <p className="text-3xl font-medium tracking-[0.3em] text-accent">TODAY&apos;S VOICE</p>

        {snapshot.low_measurement_confidence && (
          <p className="mt-6 rounded-xl bg-warning-faint px-6 py-4 text-2xl text-warning">
            LOW MEASUREMENT CONFIDENCE
          </p>
        )}

        {snapshot.score_value !== null && (
          <div className="mt-16">
            <p className="text-2xl text-text-dim">VepAIr Score</p>
            <div className="flex items-baseline gap-4">
              <span className="text-[11rem] font-bold leading-none text-text">
                {snapshot.score_value}
              </span>
              {snapshot.score_delta !== null && (
                <span
                  className={`text-4xl font-semibold ${
                    snapshot.score_delta >= 0 ? "text-accent" : "text-warning"
                  }`}
                >
                  {snapshot.score_delta >= 0 ? "↑" : "↓"}{" "}
                  {Math.abs(snapshot.score_delta)}
                </span>
              )}
            </div>
          </div>
        )}

        <div className="mt-16 flex-1">
          {rows.map((r) => (
            <Row key={r.label} label={r.label} value={r.value} />
          ))}
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element -- plain <img> renders reliably for html-to-image's DOM capture */}
            <img src="/brand/vepair-logo.png" alt="" width={40} height={40} />
            <span className="text-3xl font-semibold tracking-tight text-text">VepAIr</span>
          </div>
          <span className="text-2xl text-text-faint">
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
