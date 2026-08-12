import { forwardRef } from "react";
import { GRADE_LABEL, type ToneMatchResult } from "@/lib/pitchGrading";

const GRADE_COLOR: Record<string, string> = {
  spot_on: "text-emerald-400",
  close: "text-amber-400",
  off: "text-red-400",
  no_pitch: "text-neutral-500",
};

export const ToneMatchResultCard = forwardRef<
  HTMLDivElement,
  { result: ToneMatchResult; date: string }
>(function ToneMatchResultCard({ result, date }, ref) {
  return (
    <div ref={ref} style={{ width: 1080, height: 1920 }} className="flex flex-col bg-neutral-950 px-16 py-20">
      <p className="text-3xl font-medium tracking-[0.3em] text-emerald-400">TONE MATCH</p>

      <div className="mt-20 flex-1">
        <p className="text-2xl text-neutral-400">Target note</p>
        <p className="text-[9rem] font-bold leading-none text-neutral-50">{result.targetLabel}</p>

        <p className={`mt-20 text-6xl font-semibold ${GRADE_COLOR[result.grade]}`}>
          {GRADE_LABEL[result.grade]}
        </p>

        {result.detectedLabel && (
          <div className="mt-16 border-t border-neutral-800 pt-10">
            <div className="flex items-baseline justify-between border-b border-neutral-800 py-4">
              <span className="text-2xl text-neutral-400">You sang</span>
              <span className="text-3xl font-semibold tabular-nums text-neutral-100">
                {result.detectedLabel}
              </span>
            </div>
            {result.semitonesOff !== null && (
              <div className="flex items-baseline justify-between border-b border-neutral-800 py-4">
                <span className="text-2xl text-neutral-400">Off by</span>
                <span className="text-3xl font-semibold tabular-nums text-neutral-100">
                  {Math.abs(result.semitonesOff).toFixed(2)} semitones{" "}
                  {result.semitonesOff >= 0 ? "sharp" : "flat"}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      <p className="text-xl text-neutral-600">
        A pitch-matching practice snapshot compared to an equal-temperament reference tone —
        not a diagnosis or a medical measurement.
      </p>

      <div className="mt-6 flex items-baseline justify-between">
        <span className="text-3xl font-semibold tracking-tight text-neutral-100">VepAIr</span>
        <span className="text-2xl text-neutral-500">{date}</span>
      </div>
    </div>
  );
});
