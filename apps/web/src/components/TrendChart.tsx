"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

export interface TrendPoint {
  date: string; // ISO yyyy-mm-dd
  value: number | null;
}

const DEFAULT_WIDTH = 600;
const PAD_LEFT = 30;
const PAD_RIGHT = 12;
const PAD_TOP = 16;
const PAD_BOTTOM = 24;

function formatDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${m}/${d}`;
}

// Same convention as components/share/ProgressCard.tsx: always the raw signed delta in a
// single neutral color, never conditionally red/green by an assumed "good" direction --
// MEDICAL_SAFETY.md's "report honestly, including decline" applies here too, and not every
// metric here has an unambiguous good direction (e.g. more sleep isn't always better).
function sign(n: number): string {
  return n > 0 ? "+" : n < 0 ? "−" : "";
}

const VARIANT_CLASS = {
  card: "rounded-[20px] border border-border bg-surface p-4 shadow-card sm:p-5",
  inset: "rounded-2xl border border-border bg-surface-2 p-4",
  bare: "",
} as const;

export function TrendChart({
  title,
  color,
  points,
  yMin,
  yMax,
  yTicks,
  variant = "card",
  height = 180,
  gradient = false,
}: {
  title: string;
  color: string;
  points: TrendPoint[];
  yMin: number;
  yMax: number;
  yTicks: number[];
  variant?: keyof typeof VARIANT_CLASS;
  height?: number;
  // The signature cyan -> blue -> violet stroke instead of a single color (used on the main
  // VepAIr Score chart).
  gradient?: boolean;
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const boxRef = useRef<HTMLDivElement | null>(null);
  const uid = useId();
  const strokeId = `${uid}-stroke`;
  const areaId = `${uid}-area`;

  // Draw at the container's real pixel width so axis text keeps its true size instead of
  // scaling with the card.
  const isEmpty = points.every((p) => p.value === null);
  useEffect(() => {
    const el = boxRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      const w = Math.round(entry.contentRect.width);
      if (w > 0) setWidth(w);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [isEmpty]);

  // Belt-and-suspenders: pointerleave/mouseleave can be missed (fast pointer exits,
  // certain input devices), which would otherwise leave a stale crosshair/tooltip stuck
  // on screen pointing at a date the user isn't hovering over. While a hover is active,
  // also watch window-level pointer movement and clear it the moment the pointer is
  // outside the chart's own bounding box.
  useEffect(() => {
    if (hoverIndex === null) return;
    function handleWindowPointerMove(e: PointerEvent) {
      const box = svgRef.current?.getBoundingClientRect();
      if (!box) return;
      const outside =
        e.clientX < box.left || e.clientX > box.right || e.clientY < box.top || e.clientY > box.bottom;
      if (outside) setHoverIndex(null);
    }
    window.addEventListener("pointermove", handleWindowPointerMove);
    return () => window.removeEventListener("pointermove", handleWindowPointerMove);
  }, [hoverIndex]);

  const known = points.filter((p) => p.value !== null) as { date: string; value: number }[];

  const plotWidth = width - PAD_LEFT - PAD_RIGHT;
  const plotHeight = height - PAD_TOP - PAD_BOTTOM;
  const baseY = PAD_TOP + plotHeight;

  const xFor = (i: number) =>
    PAD_LEFT + (points.length <= 1 ? plotWidth / 2 : (i / (points.length - 1)) * plotWidth);
  const yFor = (v: number) => baseY - ((v - yMin) / (yMax - yMin)) * plotHeight;

  // Three paths: `solidPath` connects only real consecutive-day data (adjacent indices both
  // non-null); `bridgePath` connects across a skipped day so the line still reads as one
  // continuous trend instead of a series of disconnected fragments, rendered visually distinct
  // (dashed, muted) below so a gap is never mistaken for a real day-over-day data point.
  // `areaPath` fills under each unbroken run of real data only -- never under a bridged gap.
  const { solidPath, bridgePath, areaPath } = useMemo(() => {
    let solid = "";
    let bridge = "";
    let area = "";
    let lastKnownIndex: number | null = null;
    let runStartX = 0;
    let runEndX = 0;
    const closeRun = () => {
      if (lastKnownIndex !== null) area += ` L ${runEndX} ${baseY} L ${runStartX} ${baseY} Z`;
    };
    points.forEach((p, i) => {
      if (p.value === null) return;
      const x = xFor(i);
      const y = yFor(p.value);
      if (lastKnownIndex === null) {
        solid += `M ${x} ${y}`;
        area += `M ${x} ${y}`;
        runStartX = x;
      } else if (lastKnownIndex === i - 1) {
        solid += ` L ${x} ${y}`;
        area += ` L ${x} ${y}`;
      } else {
        const prevValue = points[lastKnownIndex].value as number;
        bridge += `M ${xFor(lastKnownIndex)} ${yFor(prevValue)} L ${x} ${y}`;
        solid += ` M ${x} ${y}`;
        closeRun();
        area += ` M ${x} ${y}`;
        runStartX = x;
      }
      runEndX = x;
      lastKnownIndex = i;
    });
    closeRun();
    return { solidPath: solid, bridgePath: bridge, areaPath: area };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, yMin, yMax, width, height]);

  const lastKnown = known.at(-1);
  const firstKnown = known.at(0);
  const delta =
    firstKnown && lastKnown && known.length >= 2
      ? Math.round((lastKnown.value - firstKnown.value) * 10) / 10
      : null;

  function handlePointerMove(e: React.PointerEvent<SVGSVGElement>) {
    const svgRect = e.currentTarget.getBoundingClientRect();
    const viewBoxX = ((e.clientX - svgRect.left) / svgRect.width) * width;
    const ratio = (viewBoxX - PAD_LEFT) / plotWidth;
    const idx = Math.round(ratio * (points.length - 1));
    setHoverIndex(Math.min(Math.max(idx, 0), points.length - 1));
  }

  function clearHover() {
    setHoverIndex(null);
  }

  const hovered = hoverIndex !== null ? points[hoverIndex] : null;
  const lineStroke = gradient ? `url(#${strokeId})` : color;
  const dotColor = gradient ? "var(--color-violet)" : color;

  return (
    <div className={VARIANT_CLASS[variant]}>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-medium text-text-dim">{title}</h3>
        {lastKnown && (
          <span className="text-xs text-text-faint">
            latest{" "}
            <span className="font-display text-xl text-text tabular-nums">{lastKnown.value}</span>
            {delta !== null && firstKnown && (
              <span className="ml-1.5">
                (<span className="text-text-dim">{sign(delta)}{Math.abs(delta)}</span>{" "}
                vs {formatDate(firstKnown.date)})
              </span>
            )}
          </span>
        )}
      </div>

      {known.length === 0 ? (
        <p className="py-10 text-center text-xs text-text-faint">No data in this range yet.</p>
      ) : (
        <>
          <div ref={boxRef} className="w-full">
            <svg
              ref={svgRef}
              width={width}
              height={height}
              viewBox={`0 0 ${width} ${height}`}
              className="block touch-none"
              role="img"
              aria-label={`${title} trend chart`}
              onPointerMove={handlePointerMove}
              onPointerLeave={clearHover}
              onPointerUp={clearHover}
              onPointerCancel={clearHover}
              onMouseLeave={clearHover}
            >
              <defs>
                <linearGradient
                  id={strokeId}
                  gradientUnits="userSpaceOnUse"
                  x1={PAD_LEFT}
                  y1="0"
                  x2={width - PAD_RIGHT}
                  y2="0"
                >
                  <stop offset="0" stopColor="var(--color-accent)" />
                  <stop offset="0.55" stopColor="var(--color-blue)" />
                  <stop offset="1" stopColor="var(--color-violet)" />
                </linearGradient>
                <linearGradient id={areaId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor={gradient ? "var(--color-blue)" : color} stopOpacity="0.28" />
                  <stop offset="1" stopColor={gradient ? "var(--color-blue)" : color} stopOpacity="0" />
                </linearGradient>
              </defs>

              {yTicks.map((t) => (
                <g key={t}>
                  <line
                    x1={PAD_LEFT}
                    x2={width - PAD_RIGHT}
                    y1={yFor(t)}
                    y2={yFor(t)}
                    stroke="var(--color-border)"
                    strokeWidth={1}
                  />
                  <text x={2} y={yFor(t) + 4} fontSize={11} fill="var(--color-text-faint)">
                    {t}
                  </text>
                </g>
              ))}

              <path d={areaPath} fill={`url(#${areaId})`} />
              <path
                d={bridgePath}
                fill="none"
                stroke={lineStroke}
                strokeWidth={2}
                strokeLinecap="round"
                strokeDasharray="5 5"
                opacity={0.4}
              />
              <path
                d={solidPath}
                fill="none"
                stroke={lineStroke}
                strokeWidth={gradient ? 3 : 2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {lastKnown && (
                <circle
                  cx={xFor(points.findIndex((p) => p.date === lastKnown.date))}
                  cy={yFor(lastKnown.value)}
                  r={5}
                  fill="var(--color-surface)"
                  stroke={dotColor}
                  strokeWidth={3}
                />
              )}

              {hovered && hovered.value !== null && (
                <>
                  <line
                    x1={xFor(hoverIndex!)}
                    x2={xFor(hoverIndex!)}
                    y1={PAD_TOP}
                    y2={height - PAD_BOTTOM}
                    stroke="var(--color-border-strong)"
                    strokeWidth={1}
                  />
                  <circle
                    cx={xFor(hoverIndex!)}
                    cy={yFor(hovered.value)}
                    r={4.5}
                    fill={dotColor}
                    stroke="var(--color-surface)"
                    strokeWidth={2}
                  />
                </>
              )}
            </svg>
          </div>

          <div className="relative h-0">
            {hovered && (
              <div
                className="pointer-events-none absolute -top-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-border-strong bg-surface px-2 py-1 text-xs shadow-lg"
                style={{ left: `${(xFor(hoverIndex!) / width) * 100}%` }}
              >
                <span className="text-text-faint">{formatDate(hovered.date)}: </span>
                <span className="font-medium text-text">
                  {hovered.value ?? "no data"}
                </span>
              </div>
            )}
          </div>

          {bridgePath && (
            <p className="mt-1 text-xs text-text-faint">
              <span
                className="mr-1 inline-block w-3 border-t border-dashed align-middle"
                style={{ borderColor: dotColor }}
              />
              dashed = no data recorded that day
            </p>
          )}

          <button
            type="button"
            onClick={() => setShowTable((s) => !s)}
            className="mt-3 text-xs text-text-faint hover:text-text-dim"
          >
            {showTable ? "Hide" : "View"} as table
          </button>

          {showTable && (
            <div className="mt-2 max-h-40 overflow-y-auto rounded-xl border border-border">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-surface text-text-faint">
                  <tr>
                    <th className="px-2 py-1 font-normal">Date</th>
                    <th className="px-2 py-1 font-normal">{title}</th>
                  </tr>
                </thead>
                <tbody>
                  {known
                    .slice()
                    .reverse()
                    .map((p) => (
                      <tr key={p.date} className="border-t border-border">
                        <td className="px-2 py-1 text-text-dim">{p.date}</td>
                        <td className="px-2 py-1 text-text">{p.value}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
