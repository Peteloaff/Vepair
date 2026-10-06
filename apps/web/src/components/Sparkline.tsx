// A tiny, axis-less trend line for dense lists (the coach roster). No labels or interaction --
// anything that needs reading values off uses TrendChart instead.
export function Sparkline({
  values,
  min = 0,
  max = 100,
  className = "h-8 w-20",
}: {
  values: number[];
  min?: number;
  max?: number;
  className?: string;
}) {
  const W = 100;
  const H = 32;
  if (values.length === 0) return <span className={className} />;
  const xFor = (i: number) => (values.length === 1 ? W / 2 : (i / (values.length - 1)) * W);
  const yFor = (v: number) => H - 3 - ((v - min) / (max - min || 1)) * (H - 6);
  const line = values.map((v, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(v)}`).join(" ");
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className={className}
      aria-hidden="true"
    >
      <path d={`${line} L ${W} ${H} L 0 ${H} Z`} fill="currentColor" opacity={0.15} />
      <path
        d={line}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
