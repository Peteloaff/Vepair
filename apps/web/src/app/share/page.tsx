"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { toBlob } from "html-to-image";
import { RequireAuth } from "@/components/RequireAuth";
import { TodayCard } from "@/components/share/TodayCard";
import { ProgressCard } from "@/components/share/ProgressCard";
import { useAuth } from "@/lib/auth-context";
import { todayLocalDate } from "@/lib/date";
import type { ProgressSnapshot, TodaySnapshot } from "@/lib/types";

const CARD_WIDTH = 1080;
const CARD_HEIGHT = 1920;
const PREVIEW_WIDTH = 320;

async function exportBlob(node: HTMLElement): Promise<Blob> {
  if (document.fonts?.ready) {
    await document.fonts.ready;
  }
  const blob = await toBlob(node, {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    pixelRatio: 1,
    backgroundColor: "#0a0a0a",
  });
  if (!blob) throw new Error("Could not generate image.");
  return blob;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function SharePageFlow() {
  const { apiFetch } = useAuth();
  const [today, setToday] = useState<TodaySnapshot | null>(null);
  const [progress, setProgress] = useState<ProgressSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const todayRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const date = todayLocalDate();
    Promise.all([
      apiFetch<TodaySnapshot>("/api/v1/share-progress/today", { searchParams: { date } }),
      apiFetch<ProgressSnapshot>("/api/v1/share-progress/progress", { searchParams: { date } }),
    ])
      .then(([t, p]) => {
        setToday(t);
        setProgress(p);
      })
      .catch(() => setError("Could not load your progress data."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const scale = PREVIEW_WIDTH / CARD_WIDTH;
  const activeRef = pageIndex === 0 ? todayRef : progressRef;
  const activeName = pageIndex === 0 ? "vepair-today.png" : "vepair-progress.png";

  async function handleSave() {
    if (!activeRef.current) return;
    setActionError(null);
    setBusy("save");
    try {
      const blob = await exportBlob(activeRef.current);
      downloadBlob(blob, activeName);
    } catch {
      setActionError("Could not save this image. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  async function handleShare() {
    if (!activeRef.current) return;
    setActionError(null);
    setBusy("share");
    try {
      const blob = await exportBlob(activeRef.current);
      const file = new File([blob], activeName, { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: "My VepAIr Progress" });
      } else {
        downloadBlob(blob, activeName);
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setActionError("Could not share this image. Please try Save instead.");
    } finally {
      setBusy(null);
    }
  }

  async function handleSaveBoth() {
    if (!todayRef.current || !progressRef.current) return;
    setActionError(null);
    setBusy("save-both");
    try {
      const todayBlob = await exportBlob(todayRef.current);
      downloadBlob(todayBlob, "vepair-today.png");
      const progressBlob = await exportBlob(progressRef.current);
      downloadBlob(progressBlob, "vepair-progress.png");
    } catch {
      setActionError("Could not save both images. Please try Save on each page instead.");
    } finally {
      setBusy(null);
    }
  }

  if (error) {
    return <p className="text-sm text-red-300">{error}</p>;
  }

  if (!today || !progress) {
    return <p className="text-sm text-neutral-500">Loading...</p>;
  }

  return (
    <div className="mx-auto w-full max-w-lg">
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Share My Progress</h1>
      <p className="mb-6 text-sm text-neutral-400">
        Two ready-to-post images, built entirely from your own real VepAIr data.
      </p>

      <div className="flex justify-center">
        <div
          className="overflow-hidden rounded-2xl border border-neutral-800"
          style={{ width: CARD_WIDTH * scale, height: CARD_HEIGHT * scale }}
        >
          <div style={{ width: CARD_WIDTH, transform: `scale(${scale})`, transformOrigin: "top left" }}>
            <div style={{ display: pageIndex === 0 ? "block" : "none" }}>
              <TodayCard ref={todayRef} snapshot={today} />
            </div>
            <div style={{ display: pageIndex === 1 ? "block" : "none" }}>
              <ProgressCard ref={progressRef} snapshot={progress} />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-center gap-4 text-sm">
        <button
          type="button"
          onClick={() => setPageIndex(0)}
          disabled={pageIndex === 0}
          className="rounded-lg border border-neutral-700 px-3 py-1.5 hover:bg-neutral-800 disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-neutral-500">
          {pageIndex === 0 ? "Page 1 · Today's Voice" : "Page 2 · My Progress"}
        </span>
        <button
          type="button"
          onClick={() => setPageIndex(1)}
          disabled={pageIndex === 1}
          className="rounded-lg border border-neutral-700 px-3 py-1.5 hover:bg-neutral-800 disabled:opacity-40"
        >
          Next
        </button>
      </div>

      {actionError && (
        <p className="mt-4 rounded-lg bg-red-950/50 px-3 py-2 text-center text-xs text-red-300">
          {actionError}
        </p>
      )}

      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <button
          type="button"
          onClick={handleShare}
          disabled={busy !== null}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          {busy === "share" ? "Preparing..." : "Share"}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={busy !== null}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
        >
          {busy === "save" ? "Saving..." : "Save"}
        </button>
        <button
          type="button"
          onClick={handleSaveBoth}
          disabled={busy !== null}
          className="rounded-lg border border-neutral-700 px-4 py-2 text-sm hover:bg-neutral-800 disabled:opacity-50"
        >
          {busy === "save-both" ? "Saving..." : "Save Both"}
        </button>
      </div>

      <div className="mt-8 text-center">
        <Link href="/" className="text-xs text-neutral-500 hover:text-neutral-300">
          Close
        </Link>
      </div>
    </div>
  );
}

export default function SharePage() {
  return (
    <RequireAuth>
      <main className="flex flex-1 flex-col px-6 py-10">
        <SharePageFlow />
      </main>
    </RequireAuth>
  );
}
