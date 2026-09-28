import { forwardRef } from "react";
import { GRADE_LABEL, type ToneMatchResult } from "@/lib/pitchGrading";

const GRADE_COLOR: Record<string, string> = {
  spot_on: "text-accent",
  close: "text-warning",
  off: "text-danger",
  no_pitch: "text-text-faint",
};

export const ToneMatchResultCard = forwardRef<
  HTMLDivElement,
  { result: ToneMatchResult; date: string }
>(function ToneMatchResultCard({ result, date }, ref) {
  return (
    <div ref={ref} style={{ width: 1080, height: 1920 }} className="flex flex-col bg-canvas px-16 py-20">
      <p className="text-3xl font-medium tracking-[0.3em] text-accent">TONE MATCH</p>

      <div className="mt-20 flex-1">
        <p className="text-2xl text-text-dim">Target note</p>
        <p className="text-[9rem] font-bold leading-none text-text">{result.targetLabel}</p>

        <p className={`mt-20 text-6xl font-semibold ${GRADE_COLOR[result.grade]}`}>
          {GRADE_LABEL[result.grade]}
        </p>

        {result.detectedLabel && (
          <div className="mt-16 border-t border-border pt-10">
            <div className="flex items-baseline justify-between border-b border-border py-4">
              <span className="text-2xl text-text-dim">You sang</span>
              <span className="text-3xl font-semibold tabular-nums text-text">
                {result.detectedLabel}
              </span>
            </div>
            {result.semitonesOff !== null && (
              <div className="flex items-baseline justify-between border-b border-border py-4">
                <span className="text-2xl text-text-dim">Off by</span>
                <span className="text-3xl font-semibold tabular-nums text-text">
                  {Math.abs(result.semitonesOff).toFixed(2)} semitones{" "}
                  {result.semitonesOff >= 0 ? "sharp" : "flat"}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      <p className="text-xl text-text-faint">
        A pitch-matching practice snapshot compared to an equal-temperament reference tone —
        not a diagnosis or a medical measurement.
      </p>

      <div className="mt-6 flex items-baseline justify-between">
        <span className="text-3xl font-semibold tracking-tight text-text">VepAIr</span>
        <span className="text-2xl text-text-faint">{date}</span>
      </div>
    </div>
  );
});
