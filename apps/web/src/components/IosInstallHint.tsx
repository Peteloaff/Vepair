"use client";

import { useEffect, useState } from "react";

const DISMISSED_KEY = "vepair_ios_install_hint_dismissed";

// Android Chrome offers to install VepAIr by itself; iPhone never does -- it has to be done by
// hand from Safari's Share menu. So this tells iPhone users how, once, and only when it applies:
// iOS Safari, not already installed (standalone), and not dismissed before.
export function IosInstallHint() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const ua = navigator.userAgent;
    const isIos =
      /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    const isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua);
    const standalone =
      (navigator as unknown as { standalone?: boolean }).standalone === true ||
      window.matchMedia("(display-mode: standalone)").matches;
    let dismissed = false;
    try {
      dismissed = localStorage.getItem(DISMISSED_KEY) === "1";
    } catch {
      // Storage can be blocked (private mode); showing the hint again is harmless.
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setShow(isIos && isSafari && !standalone && !dismissed);
  }, []);

  if (!show) return null;

  return (
    <div className="mb-4 flex items-start justify-between gap-3 rounded-2xl border border-border bg-surface px-4 py-3 text-sm shadow-card">
      <p className="text-text-dim">
        <span className="font-semibold text-text">Install VepAIr on your iPhone.</span> Tap the
        Share button in Safari, then <span className="text-text">Add to Home Screen</span>.
      </p>
      <button
        type="button"
        onClick={() => {
          try {
            localStorage.setItem(DISMISSED_KEY, "1");
          } catch {
            // ignore
          }
          setShow(false);
        }}
        className="shrink-0 text-xs font-semibold text-text-faint hover:text-text"
      >
        Dismiss
      </button>
    </div>
  );
}
