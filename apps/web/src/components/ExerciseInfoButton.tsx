"use client";

import { useState } from "react";

interface ExerciseInfoButtonProps {
  purpose: string;
  instructions: string;
  contraindications?: string | null;
}

/** A small "ⓘ" trigger that reveals how to do an exercise — on hover for desktop (via CSS
 * group-hover, no JS needed) and on tap/toggle for touch, since hover doesn't exist there. */
export function ExerciseInfoButton({
  purpose,
  instructions,
  contraindications,
}: ExerciseInfoButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <span
      className="group relative inline-block"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        setOpen((v) => !v);
      }}
    >
      <button
        type="button"
        aria-label="Exercise info"
        className="flex h-4 w-4 items-center justify-center rounded-full border border-neutral-600 text-[10px] leading-none text-neutral-400 hover:border-neutral-400 hover:text-neutral-200"
      >
        i
      </button>
      <div
        className={`absolute left-1/2 top-full z-20 mt-1 w-56 -translate-x-1/2 rounded-lg border border-neutral-700 bg-neutral-900 p-2.5 text-left text-xs text-neutral-300 shadow-lg group-hover:block ${
          open ? "block" : "hidden"
        }`}
      >
        <p className="mb-1 text-neutral-400">{purpose}</p>
        <p>{instructions}</p>
        {contraindications && <p className="mt-1 text-amber-400">{contraindications}</p>}
      </div>
    </span>
  );
}
