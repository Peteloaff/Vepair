import type { Baseline, BaselineSummary } from "@/lib/types";

const METRIC_DISPLAY: Record<string, { label: string; unit: string; decimals: number }> = {
  f0_mean_hz: { label: "Average pitch", unit: "Hz", decimals: 0 },
  pitch_stability_semitones: { label: "Pitch stability", unit: "st", decimals: 2 },
  jitter_percent: { label: "Jitter", unit: "%", decimals: 2 },
  shimmer_percent: { label: "Shimmer", unit: "%", decimals: 2 },
  hnr_db: { label: "Vocal clarity (HNR)", unit: "dB", decimals: 1 },
};

const CONFIDENCE_COPY: Record<string, string> = {
  insufficient: "Not enough sessions yet to establish a baseline.",
  building: "Your baseline is still building — a few more sessions will sharpen it.",
  developing: "Your baseline is developing a clearer picture of your normal voice.",
  established: "Your baseline is well established from your recent sessions.",
};

function confidenceColor(label: string): string {
  if (label === "established") return "text-emerald-400";
  if (label === "developing") return "text-emerald-300";
  if (label === "building") return "text-amber-400";
  return "text-neutral-500";
}

function BaselineStat({ baseline }: { baseline: Baseline }) {
  const meta = METRIC_DISPLAY[baseline.metric_name];
  if (!meta || baseline.median_value === null) return null;
  return (
    <div>
      <dt className="text-xs text-neutral-500">{meta.label}</dt>
      <dd className="text-neutral-200">
        {baseline.median_value.toFixed(meta.decimals)}
        {meta.unit}
      </dd>
    </div>
  );
}

export function VocalBaseline({ summary }: { summary: BaselineSummary | null }) {
  if (summary === null) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  if (summary.usable_session_count === 0) {
    return (
      <p className="text-sm text-neutral-500">
        Record a few sustained-vowel samples to start building your personal vocal baseline —
        it&apos;s compared only against your own voice over time, never anyone else&apos;s.
      </p>
    );
  }

  const displayedMetrics = summary.voice_baselines.filter((b) => METRIC_DISPLAY[b.metric_name]);

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span
          className={`text-sm font-medium ${confidenceColor(summary.voice_confidence_label)}`}
        >
          {summary.voice_confidence_label[0].toUpperCase() +
            summary.voice_confidence_label.slice(1)}{" "}
          ({summary.voice_confidence_pct}%)
        </span>
        <span className="text-xs text-neutral-500">
          {summary.usable_session_count} usable session
          {summary.usable_session_count === 1 ? "" : "s"}
        </span>
      </div>
      <p className="mb-4 text-xs text-neutral-500">
        {CONFIDENCE_COPY[summary.voice_confidence_label]}
      </p>
      {displayedMetrics.length > 0 && (
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          {displayedMetrics.map((b) => (
            <BaselineStat key={b.metric_name} baseline={b} />
          ))}
        </dl>
      )}
      <p className="mt-4 text-xs text-neutral-600">
        These numbers describe your own recent recordings, not a clinical reference range — see
        MEDICAL_SAFETY.md.
      </p>
    </div>
  );
}
