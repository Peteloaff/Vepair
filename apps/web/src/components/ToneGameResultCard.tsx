import { forwardRef } from "react";
import { GRADE_LABEL } from "@/lib/pitchGrading";
import type { ToneGameAttempt } from "@/lib/types";

const GRADE_COLOR: Record<string, string> = {
  spot_on: "text-emerald-400",
  close: "text-amber-400",
  off: "text-red-400",
  no_pitch: "text-neutral-500",
};

const MAX_TOTAL_SCORE = 500;

export const ToneGameResultCard = forwardRef<
  HTMLDivElement,
  { attempts: ToneGameAttempt[]; totalScore: number; date: string }
>(function ToneGameResultCard({ attempts, totalScore, date }, ref) {
  return (
    <div
      ref={ref}
      style={{ width: 1080, height: 1920 }}
      className="flex flex-col bg-neutral-950 px-16 py-20"
    >
      <p className="text-3xl font-medium tracking-[0.3em] text-emerald-400">5-TONE CHALLENGE</p>

      <div className="mt-16 flex-1">
        <p className="text-2xl text-neutral-400">Total score</p>
        <p className="text-[9rem] font-bold leading-none text-neutral-50">
          {totalScore}
          <span className="text-4xl text-neutral-500">/{MAX_TOTAL_SCORE}</span>
        </p>

        <div className="mt-16 border-t border-neutral-800">
          {attempts.map((a) => (
            <div
              key={a.order_index}
              className="flex items-baseline justify-between border-b border-neutral-800 py-5"
            >
              <span className="text-3xl font-semibold text-neutral-100">{a.target_note}</span>
              <span className={`text-2xl font-medium ${GRADE_COLOR[a.grade]}`}>
                {GRADE_LABEL[a.grade]}
              </span>
              <span className="text-3xl font-semibold tabular-nums text-neutral-100">
                {a.score}
              </span>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xl text-neutral-600">
        A pitch-matching game scored on accuracy, hold time, and reaction speed against an
        equal-temperament reference tone — not a diagnosis or a medical measurement.
      </p>

      <div className="mt-6 flex items-baseline justify-between">
        <span className="text-3xl font-semibold tracking-tight text-neutral-100">VepAIr</span>
        <span className="text-2xl text-neutral-500">{date}</span>
      </div>
    </div>
  );
});
