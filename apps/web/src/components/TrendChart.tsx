"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export interface TrendPoint {
  date: string; // ISO yyyy-mm-dd
  value: number | null;
}

const WIDTH = 600;
const HEIGHT = 180;
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

export function TrendChart({
  title,
  color,
  points,
  yMin,
  yMax,
  yTicks,
}: {
  title: string;
  color: string;
  points: TrendPoint[];
  yMin: number;
  yMax: number;
  yTicks: number[];
}) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const svgRef = useRef<SVGSVGElement | null>(null);

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

  const plotWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
  const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;

  const xFor = (i: number) =>
    PAD_LEFT + (points.length <= 1 ? plotWidth / 2 : (i / (points.length - 1)) * plotWidth);
  const yFor = (v: number) =>
    PAD_TOP + plotHeight - ((v - yMin) / (yMax - yMin)) * plotHeight;

  const linePath = useMemo(() => {
    let d = "";
    let started = false;
    points.forEach((p, i) => {
      if (p.value === null) {
        started = false;
        return;
      }
      const x = xFor(i);
      const y = yFor(p.value);
      d += started ? ` L ${x} ${y}` : `M ${x} ${y}`;
      started = true;
    });
    return d;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, yMin, yMax]);

  const lastKnown = known.at(-1);
  const firstKnown = known.at(0);
  const delta =
    firstKnown && lastKnown && known.length >= 2
      ? Math.round((lastKnown.value - firstKnown.value) * 10) / 10
      : null;

  function handlePointerMove(e: React.PointerEvent<SVGSVGElement>) {
    const svgRect = e.currentTarget.getBoundingClientRect();
    const relXPx = e.clientX - svgRect.left;
    const viewBoxX = (relXPx / svgRect.width) * WIDTH;
    const ratio = (viewBoxX - PAD_LEFT) / plotWidth;
    const idx = Math.round(ratio * (points.length - 1));
    setHoverIndex(Math.min(Math.max(idx, 0), points.length - 1));
  }

  function clearHover() {
    setHoverIndex(null);
  }

  const hovered = hoverIndex !== null ? points[hoverIndex] : null;

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-medium text-neutral-200">{title}</h3>
        {lastKnown && (
          <span className="text-xs text-neutral-500">
            latest: <span className="text-neutral-200">{lastKnown.value}</span>
            {delta !== null && firstKnown && (
              <span className="ml-1.5">
                (<span className="text-neutral-300">{sign(delta)}{Math.abs(delta)}</span>{" "}
                vs {formatDate(firstKnown.date)})
              </span>
            )}
          </span>
        )}
      </div>

      {known.length === 0 ? (
        <p className="py-10 text-center text-xs text-neutral-600">No data in this range yet.</p>
      ) : (
        <>
          <svg
            ref={svgRef}
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="w-full touch-none"
            role="img"
            aria-label={`${title} trend chart`}
            onPointerMove={handlePointerMove}
            onPointerLeave={clearHover}
            onPointerUp={clearHover}
            onPointerCancel={clearHover}
            onMouseLeave={clearHover}
          >
            {yTicks.map((t) => (
              <g key={t}>
                <line
                  x1={PAD_LEFT}
                  x2={WIDTH - PAD_RIGHT}
                  y1={yFor(t)}
                  y2={yFor(t)}
                  stroke="#2c2c2a"
                  strokeWidth={1}
                />
                <text x={2} y={yFor(t) + 3} fontSize={9} fill="#898781">
                  {t}
                </text>
              </g>
            ))}

            <path d={linePath} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />

            {lastKnown && (
              <circle
                cx={xFor(points.findIndex((p) => p.date === lastKnown.date))}
                cy={yFor(lastKnown.value)}
                r={4}
                fill={color}
                stroke="#1a1a19"
                strokeWidth={2}
              />
            )}

            {hovered && hovered.value !== null && (
              <>
                <line
                  x1={xFor(hoverIndex!)}
                  x2={xFor(hoverIndex!)}
                  y1={PAD_TOP}
                  y2={HEIGHT - PAD_BOTTOM}
                  stroke="#52514e"
                  strokeWidth={1}
                />
                <circle
                  cx={xFor(hoverIndex!)}
                  cy={yFor(hovered.value)}
                  r={4}
                  fill={color}
                  stroke="#1a1a19"
                  strokeWidth={2}
                />
              </>
            )}

          </svg>

          <div className="relative h-0">
            {hovered && (
              <div
                className="pointer-events-none absolute -top-2 -translate-x-1/2 whitespace-nowrap rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1 text-xs shadow-lg"
                style={{ left: `${(xFor(hoverIndex!) / WIDTH) * 100}%` }}
              >
                <span className="text-neutral-500">{formatDate(hovered.date)}: </span>
                <span className="font-medium text-neutral-100">
                  {hovered.value ?? "no data"}
                </span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => setShowTable((s) => !s)}
            className="mt-3 text-xs text-neutral-500 hover:text-neutral-300"
          >
            {showTable ? "Hide" : "View"} as table
          </button>

          {showTable && (
            <div className="mt-2 max-h-40 overflow-y-auto rounded-lg border border-neutral-800">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-neutral-900 text-neutral-500">
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
                      <tr key={p.date} className="border-t border-neutral-800">
                        <td className="px-2 py-1 text-neutral-400">{p.date}</td>
                        <td className="px-2 py-1 text-neutral-200">{p.value}</td>
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
