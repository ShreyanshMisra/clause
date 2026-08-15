"use client";

import { useEffect, useRef, useState } from "react";

/* Pixel-grid "churning" loader: a diagonal shimmer wave sweeps across a grid of
   cells while an elapsed-time counter ticks. Inspired by the churning loader on
   beautifului.dev — a good fit for signalling active AI work. */

const COLS = 7;
const ROWS = 7;

const KEYFRAMES = `
@keyframes churnCell {
  0%, 100% { opacity: 0.12; transform: scale(0.82); }
  40%      { opacity: 1;    transform: scale(1); }
}
@keyframes churnFail {
  0%, 100% { opacity: 0.9; }
}
`;

export function ChurningLoader({ failed = false }: { failed?: boolean }) {
  const [elapsed, setElapsed] = useState(0);
  const start = useRef<number | null>(null);

  useEffect(() => {
    const id = "clause-churn-kf";
    if (!document.getElementById(id)) {
      const s = document.createElement("style");
      s.id = id;
      s.textContent = KEYFRAMES;
      document.head.appendChild(s);
    }
  }, []);

  useEffect(() => {
    if (failed) return;
    start.current = Date.now();
    const t = setInterval(() => {
      setElapsed((Date.now() - (start.current ?? Date.now())) / 1000);
    }, 100);
    return () => clearInterval(t);
  }, [failed]);

  const cells = [];
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      // Diagonal wave: delay grows along the r+c anti-diagonal.
      const delay = ((r + c) / (ROWS + COLS)) * 1.1;
      cells.push(
        <span
          key={`${r}-${c}`}
          style={{
            width: "12px",
            height: "12px",
            borderRadius: "3px",
            background: failed ? "var(--sev-illegal)" : "var(--accent)",
            opacity: failed ? 0.85 : undefined,
            animation: failed
              ? undefined
              : `churnCell 1.4s ease-in-out ${delay}s infinite`,
          }}
        />
      );
    }
  }

  return (
    <div className="flex flex-col items-center gap-5">
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${COLS}, 12px)`,
          gap: "6px",
          filter: failed ? "none" : "drop-shadow(0 4px 14px rgba(217,119,87,0.28))",
        }}
      >
        {cells}
      </div>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "13px",
          fontWeight: 600,
          letterSpacing: "0.02em",
          color: failed ? "var(--sev-illegal)" : "var(--accent-deep)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {failed ? "failed" : `${elapsed.toFixed(1)}s`}
      </span>
    </div>
  );
}
