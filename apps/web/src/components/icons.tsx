import type { ReactNode } from "react";

// Small stroke-icon set used by the icon tiles, plan rows and quick links. Hand-drawn on a 24px
// grid so they share one stroke weight; kept inline (no icon-font or package) to match the
// codebase's existing dependency-free SVG usage.
const PATHS = {
  wave: <polyline points="2,12 5,12 7.5,6 10.5,18 13.5,4 16.5,20 19,9 22,12" />,
  mic: (
    <>
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
    </>
  ),
  note: (
    <>
      <path d="M9 18V5l11-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="17" cy="16" r="3" />
    </>
  ),
  lotus: (
    <>
      <path d="M12 20c-4-1-7-4-7-9 3 0 5 1 7 3 2-2 4-3 7-3 0 5-3 8-7 9z" />
      <path d="M12 14c-1.5-2-1.5-5 0-9 1.5 4 1.5 7 0 9z" />
    </>
  ),
  chart: (
    <>
      <polyline points="3,17 9,11 13,15 21,6" />
      <polyline points="15,6 21,6 21,12" />
    </>
  ),
  range: <path d="M5 20V9M9 20V4M13 20V12M17 20V7M21 20v-5" />,
  plan: (
    <>
      <rect x="4" y="5" width="16" height="15" rx="3" />
      <path d="M4 10h16M9 3v4M15 3v4" />
    </>
  ),
  game: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1" />
    </>
  ),
  rec: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="3.5" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20a6.5 6.5 0 0 1 13 0" />
      <path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5" />
    </>
  ),
  chev: <polyline points="9,6 15,12 9,18" />,
  check: (
    <>
      <circle cx="12" cy="12" r="9" />
      <polyline points="8,12.5 11,15.5 16,9" />
    </>
  ),
  alert: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5.5M12 16.5h.01" />
    </>
  ),
  flame: <path d="M12 3c.8 3.8 5 5 5 10a5 5 0 0 1-10 0c0-2 .8-3.2 2-4.2 0 2 1 3 2 3 .2-3-1.5-5 1-8.8z" />,
  chat: <path d="M4 5h16v11H10l-4 4v-4H4z" />,
  plus: <path d="M12 5v14M5 12h14" />,
  share: (
    <>
      <circle cx="6" cy="12" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <circle cx="18" cy="18" r="2.5" />
      <path d="M8.2 10.8l7.6-3.6M8.2 13.2l7.6 3.6" />
    </>
  ),
  straw: <path d="M6 21L17 4h3M8 18l3 2" />,
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof PATHS;

export function Icon({ name, className = "h-5 w-5" }: { name: IconName; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`shrink-0 ${className}`}
    >
      {PATHS[name]}
    </svg>
  );
}

const TILE_COLORS = {
  blue: "from-blue to-blue/70 shadow-blue/30",
  cyan: "from-accent to-accent/70 shadow-accent/30",
  violet: "from-violet to-violet/70 shadow-violet/30",
  teal: "from-teal to-teal/70 shadow-teal/30",
  amber: "from-warning to-warning/70 shadow-warning/30",
  coral: "from-danger to-danger/70 shadow-danger/30",
} as const;

export type TileColor = keyof typeof TILE_COLORS;

// The rounded gradient square behind an icon -- the reference design's signature "app icon" tile.
export function IconTile({
  name,
  color = "blue",
  size = "md",
}: {
  name: IconName;
  color?: TileColor;
  size?: "sm" | "md";
}) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-[14px] bg-gradient-to-br text-white shadow-lg ${
        size === "sm" ? "h-10 w-10" : "h-12 w-12"
      } ${TILE_COLORS[color]}`}
    >
      <Icon name={name} />
    </span>
  );
}
