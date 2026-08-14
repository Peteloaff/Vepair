"use client";

// Shared by AveragePitchRecorder (Tone Match's "Find your average pitch") and the Tone Match
// practice flow's "sing it back" listening phase -- both compare a live detected Hz reading
// against a target Hz and need the same "how close am I" meter.

// Meter span around the goal frequency. ON_PITCH_HZ/CLOSE_HZ are two tiers -- a genuinely
// tighter bar than the note-level goal tracking elsewhere in the app (2 Hz, not a semitone),
// with an intermediate "getting close" tier so the meter reads as continuous feedback rather
// than a flat pass/fail the moment recording starts.
const METER_RANGE_HZ = 40;
const ON_PITCH_HZ = 2;
const CLOSE_HZ = 10;

type Zone = "far" | "close" | "on";

function zoneFor(diff: number | null): Zone {
  if (diff === null) return "far";
  const abs = Math.abs(diff);
  if (abs <= ON_PITCH_HZ) return "on";
  if (abs <= CLOSE_HZ) return "close";
  return "far";
}

const ZONE_TEXT: Record<Zone, string> = {
  on: "text-emerald-400",
  close: "text-amber-400",
  far: "text-neutral-100",
};

const ZONE_NEEDLE: Record<Zone, string> = {
  on: "bg-emerald-400 motion-safe:animate-pulse shadow-[0_0_10px_1px_rgba(52,211,153,0.65)]",
  close: "bg-amber-400",
  far: "bg-neutral-300",
};

const ZONE_LABEL: Record<Zone, string> = {
  on: "On pitch",
  close: "Getting close",
  far: "",
};

export function PitchMeter({ liveHz, goalHz }: { liveHz: number | null; goalHz: number | null }) {
  if (goalHz === null) {
    return (
      <p className="font-mono text-4xl font-bold leading-none tabular-nums text-neutral-100">
        {liveHz != null ? liveHz.toFixed(1) : "—"}
        <span className="ml-1 text-base font-normal text-neutral-500">Hz</span>
      </p>
    );
  }

  const diff = liveHz != null ? liveHz - goalHz : null;
  const zone = zoneFor(diff);
  const rangeMin = goalHz - METER_RANGE_HZ;
  const rangeMax = goalHz + METER_RANGE_HZ;
  const clamped = liveHz != null ? Math.min(rangeMax, Math.max(rangeMin, liveHz)) : null;
  const positionPct = clamped != null ? ((clamped - rangeMin) / (rangeMax - rangeMin)) * 100 : null;
  const onZoneWidthPct = ((ON_PITCH_HZ * 2) / (METER_RANGE_HZ * 2)) * 100;
  const closeZoneWidthPct = ((Math.min(CLOSE_HZ, METER_RANGE_HZ) * 2) / (METER_RANGE_HZ * 2)) * 100;

  return (
    <div>
      <div className="mb-3 flex items-end justify-between">
        <div>
          <p
            className={`font-mono text-4xl font-bold leading-none tabular-nums transition-colors ${ZONE_TEXT[zone]}`}
          >
            {liveHz != null ? liveHz.toFixed(1) : "—"}
            <span className="ml-1 text-base font-normal text-neutral-500">Hz</span>
          </p>
          <p className={`mt-1 h-4 text-xs font-medium ${ZONE_TEXT[zone]}`}>
            {liveHz != null ? ZONE_LABEL[zone] : ""}
          </p>
        </div>
        <p className="text-right text-xs leading-tight text-neutral-500">
          Goal
          <br />
          <span className="font-mono text-sm text-neutral-300">{goalHz.toFixed(1)} Hz</span>
        </p>
      </div>

      <div className="relative h-3 rounded-full bg-neutral-800">
        <div
          className="absolute top-0 h-3 rounded-full bg-amber-500/20"
          style={{ left: `${50 - closeZoneWidthPct / 2}%`, width: `${closeZoneWidthPct}%` }}
        />
        <div
          className="absolute top-0 h-3 rounded-full bg-emerald-500/40"
          style={{ left: `${50 - onZoneWidthPct / 2}%`, width: `${onZoneWidthPct}%` }}
        />
        <div className="absolute left-1/2 top-1/2 h-5 w-px -translate-x-1/2 -translate-y-1/2 bg-neutral-500" />
        {positionPct != null && (
          <div
            className={`absolute top-1/2 h-6 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full transition-[left] duration-150 ${ZONE_NEEDLE[zone]}`}
            style={{ left: `${positionPct}%` }}
          />
        )}
      </div>
    </div>
  );
}
