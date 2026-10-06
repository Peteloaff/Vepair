import type { ReactNode } from "react";

// The standard content panel from the redesign: a soft-bordered, rounded surface with an
// optional title row. Used by the dashboard, Progress, and the Coach Portal.
export function Card({
  title,
  meta,
  className = "",
  children,
}: {
  title?: string;
  meta?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={`min-w-0 rounded-[20px] border border-border bg-surface p-5 shadow-card sm:p-6 ${className}`}
    >
      {title && (
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-lg font-medium tracking-tight">{title}</h2>
          {meta && <span className="text-xs text-text-faint">{meta}</span>}
        </div>
      )}
      {children}
    </section>
  );
}

const CHIP_TONES = {
  ok: "bg-ok-faint text-ok",
  warn: "bg-warning-faint text-warning",
  bad: "bg-danger-faint text-danger",
  accent: "bg-accent-faint text-accent",
  violet: "bg-violet-faint text-violet",
  neutral: "bg-surface-2 text-text-dim",
} as const;

export type ChipTone = keyof typeof CHIP_TONES;

export function Chip({ tone = "neutral", children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${CHIP_TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function StatTile({
  label,
  value,
  unit,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
}) {
  return (
    <div className="rounded-[18px] border border-border bg-surface px-4 py-3.5 shadow-card">
      <p className="text-xs text-text-faint">{label}</p>
      <p className="font-display mt-0.5 text-3xl leading-tight tracking-tight tabular-nums">
        {value}
        {unit && <small className="ml-1 text-sm text-text-faint">{unit}</small>}
      </p>
    </div>
  );
}
