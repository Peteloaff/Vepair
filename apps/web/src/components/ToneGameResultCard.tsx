import { forwardRef } from "react";
import { GRADE_LABEL } from "@/lib/pitchGrading";
import type { ToneGameAttempt } from "@/lib/types";

const GRADE_COLOR: Record<string, string> = {
  spot_on: "text-accent",
  close: "text-warning",
  off: "text-danger",
  no_pitch: "text-text-faint",
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
      className="flex flex-col bg-canvas px-16 py-20"
    >
      <p className="text-3xl font-medium tracking-[0.3em] text-accent">5-TONE CHALLENGE</p>

      <div className="mt-16 flex-1">
        <p className="text-2xl text-text-dim">Total score</p>
        <p className="text-[9rem] font-bold leading-none text-text">
          {totalScore}
          <span className="text-4xl text-text-faint">/{MAX_TOTAL_SCORE}</span>
        </p>

        <div className="mt-16 border-t border-border">
          {attempts.map((a) => (
            <div
              key={a.order_index}
              className="flex items-baseline justify-between border-b border-border py-5"
            >
              <span className="text-3xl font-semibold text-text">{a.target_note}</span>
              <span className={`text-2xl font-medium ${GRADE_COLOR[a.grade]}`}>
                {GRADE_LABEL[a.grade]}
              </span>
              <span className="text-3xl font-semibold tabular-nums text-text">
                {a.score}
              </span>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xl text-text-faint">
        A pitch-matching game scored on accuracy, hold time, and reaction speed against an
        equal-temperament reference tone — not a diagnosis or a medical measurement.
      </p>

      <div className="mt-6 flex items-baseline justify-between">
        <span className="text-3xl font-semibold tracking-tight text-text">VepAIr</span>
        <span className="text-2xl text-text-faint">{date}</span>
      </div>
    </div>
  );
});
