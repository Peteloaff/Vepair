"use client";

import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";

export interface WaveformHandle {
  pushChunk: (chunk: Float32Array) => void;
  reset: () => void;
}

const BAR_COUNT = 100;
const BAR_COLOR = "#34d399";
const BG_COLOR = "#0a0a0a";

export const Waveform = forwardRef<WaveformHandle, { active: boolean }>(function Waveform(
  { active },
  ref
) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const barsRef = useRef<number[]>(new Array(BAR_COUNT).fill(0));
  const rafRef = useRef<number | null>(null);

  useImperativeHandle(ref, () => ({
    pushChunk(chunk: Float32Array) {
      let peak = 0;
      for (let i = 0; i < chunk.length; i++) {
        const abs = Math.abs(chunk[i]);
        if (abs > peak) peak = abs;
      }
      barsRef.current.push(peak);
      if (barsRef.current.length > BAR_COUNT) barsRef.current.shift();
    },
    reset() {
      barsRef.current = new Array(BAR_COUNT).fill(0);
      draw();
    },
  }));

  function draw() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width, height } = canvas;
    ctx.fillStyle = BG_COLOR;
    ctx.fillRect(0, 0, width, height);

    const bars = barsRef.current;
    const barWidth = width / BAR_COUNT;
    ctx.fillStyle = BAR_COLOR;
    for (let i = 0; i < bars.length; i++) {
      const barHeight = Math.max(2, bars[i] * height);
      const x = i * barWidth;
      const y = (height - barHeight) / 2;
      ctx.fillRect(x, y, Math.max(1, barWidth - 1), barHeight);
    }
  }

  useEffect(() => {
    function loop() {
      draw();
      rafRef.current = requestAnimationFrame(loop);
    }
    if (active) {
      rafRef.current = requestAnimationFrame(loop);
    } else {
      draw();
    }
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
     
  }, [active]);

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={80}
      className="w-full rounded-lg bg-neutral-950"
      aria-hidden
    />
  );
});
