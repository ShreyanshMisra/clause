"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

/* ─── micro-animation keyframes injected once ───────────────────────────── */
const KEYFRAMES = `
@keyframes cardReveal {
  from { opacity: 0; transform: translateY(24px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0)    scale(1); }
}
@keyframes shimmer {
  0%   { background-position: -200% center; }
  100% { background-position:  200% center; }
}
@keyframes pulseRing {
  0%, 100% { transform: scale(1);   opacity: 0.6; }
  50%       { transform: scale(1.14); opacity: 0.15; }
}
@keyframes spinArc {
  from { stroke-dashoffset: 220; }
  to   { stroke-dashoffset: 0; }
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes docFloat {
  0%, 100% { transform: translateY(0) rotate(-3deg); }
  50%       { transform: translateY(-8px) rotate(-3deg); }
}
`;

/* ─── SVG progress ring ──────────────────────────────────────────────────── */
function ProgressRing() {
  const r = 34;
  const circ = 2 * Math.PI * r; // ~213.6
  return (
    <svg width="88" height="88" viewBox="0 0 88 88" aria-hidden>
      {/* Track */}
      <circle
        cx="44" cy="44" r={r}
        fill="none"
        stroke="var(--surface)"
        strokeWidth="5"
      />
      {/* Arc — animated via CSS */}
      <circle
        cx="44" cy="44" r={r}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="5"
        strokeLinecap="round"
        strokeDasharray={`${circ * 0.65} ${circ * 0.35}`}
        style={{
          transformOrigin: "44px 44px",
          animation: "spinArc 1.1s ease-in-out infinite alternate",
        }}
      />
    </svg>
  );
}

/* ─── Floating doc decoration ────────────────────────────────────────────── */
function FloatingDoc({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 56 72"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <rect width="56" height="72" rx="6" fill="var(--surface)" />
      <rect x="10" y="14" width="36" height="4" rx="2" fill="var(--ink-subtle)" opacity="0.35" />
      <rect x="10" y="24" width="28" height="4" rx="2" fill="var(--ink-subtle)" opacity="0.25" />
      <rect x="10" y="34" width="32" height="4" rx="2" fill="var(--ink-subtle)" opacity="0.2" />
      <rect x="10" y="44" width="20" height="4" rx="2" fill="var(--ink-subtle)" opacity="0.15" />
      <rect x="10" y="54" width="26" height="4" rx="2" fill="var(--ink-subtle)" opacity="0.1" />
      {/* red alert line */}
      <rect x="10" y="34" width="32" height="4" rx="2" fill="var(--sev-illegal)" opacity="0.45" />
    </svg>
  );
}

/* ─── Upload icon ────────────────────────────────────────────────────────── */
function UploadIcon({ dragging }: { dragging: boolean }) {
  return (
    <svg
      width="40" height="40" viewBox="0 0 40 40" fill="none"
      aria-hidden
      style={{
        transition: "transform 0.35s cubic-bezier(.34,1.56,.64,1)",
        transform: dragging ? "translateY(-5px) scale(1.12)" : "translateY(0) scale(1)",
      }}
    >
      <rect width="40" height="40" rx="12" fill="var(--accent)" opacity="0.12" />
      <path
        d="M20 26V14M20 14l-5 5M20 14l5 5"
        stroke="var(--accent)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12 28h16"
        stroke="var(--accent)"
        strokeWidth="2.2"
        strokeLinecap="round"
        opacity="0.5"
      />
    </svg>
  );
}

/* ─── Main component ─────────────────────────────────────────────────────── */
export function UploadCard() {
  const router = useRouter();
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  /* inject keyframes once */
  useEffect(() => {
    const id = "clause-upload-kf";
    if (!document.getElementById(id)) {
      const s = document.createElement("style");
      s.id = id;
      s.textContent = KEYFRAMES;
      document.head.appendChild(s);
    }
  }, []);

  /* warmup */
  useEffect(() => {
    api.warmup();
  }, []);

  const handle = useCallback(
    async (file: File) => {
      setError(null);
      if (file.type !== "application/pdf") {
        setError("Only PDF files are supported.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setError("File must be under 10 MB.");
        return;
      }
      setBusy(true);
      try {
        const res = await api.upload(file);
        sessionStorage.setItem("pii", JSON.stringify(res.pii_redacted));
        await api.analyze(res.file_id);
        router.push(`/processing?file_id=${res.file_id}`);
      } catch (e) {
        setError((e as Error).message);
        setBusy(false);
      }
    },
    [router]
  );

  /* drag events */
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);
  const onDragLeave = useCallback((e: React.DragEvent) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
  }, []);
  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handle(f);
    },
    [handle]
  );

  return (
    <div
      role="region"
      aria-label="Upload your lease"
      style={{ animation: "cardReveal 0.55s cubic-bezier(.16,1,.3,1) both" }}
    >
      {/* ── Glass card ─────────────────────────────────────────────────── */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        style={{
          background: "rgba(250,249,245,0.72)",
          backdropFilter: "blur(20px) saturate(1.4)",
          WebkitBackdropFilter: "blur(20px) saturate(1.4)",
          border: dragging
            ? "1.5px solid var(--accent)"
            : "1.5px solid rgba(107,107,99,0.18)",
          boxShadow: dragging
            ? "0 0 0 4px rgba(217,119,87,0.14), 0 24px 64px rgba(20,20,19,0.12)"
            : "0 8px 40px rgba(20,20,19,0.09), 0 1px 0 rgba(255,255,255,0.8) inset",
          transition: "border-color 0.25s, box-shadow 0.25s, background 0.25s",
          borderRadius: "24px",
          padding: "56px 48px 48px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* ── Corner doc decorations ──────────────────────────────────── */}
        <FloatingDoc
          className="absolute -top-3 -right-4 w-16 opacity-40"
          // @ts-expect-error style prop on SVG className component
          style={{ animation: "docFloat 4s ease-in-out infinite" }}
        />
        <FloatingDoc
          className="absolute -bottom-2 -left-3 w-10 opacity-20"
          // @ts-expect-error
          style={{ animation: "docFloat 5.5s ease-in-out infinite 0.8s" }}
        />

        {/* ── Drop overlay tint ───────────────────────────────────────── */}
        {dragging && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(ellipse at center, rgba(217,119,87,0.08) 0%, transparent 70%)",
              borderRadius: "inherit",
              pointerEvents: "none",
            }}
          />
        )}

        {busy ? (
          /* ── Uploading state ─────────────────────────────────────────── */
          <div
            className="flex flex-col items-center gap-5 py-4"
            style={{ animation: "fadeIn 0.3s ease both" }}
          >
            <div style={{ position: "relative" }}>
              {/* Pulse ring behind */}
              <div
                style={{
                  position: "absolute",
                  inset: "-12px",
                  borderRadius: "50%",
                  background: "var(--accent)",
                  animation: "pulseRing 1.6s ease-in-out infinite",
                }}
              />
              <ProgressRing />
            </div>
            <p
              className="text-base font-medium"
              style={{ color: "var(--ink-muted)" }}
            >
              Uploading your lease
            </p>
            <p
              className="text-sm"
              style={{
                color: "var(--ink-subtle)",
                background:
                  "linear-gradient(90deg, var(--ink-subtle) 0%, var(--accent) 50%, var(--ink-subtle) 100%)",
                backgroundSize: "200% auto",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                animation: "shimmer 2s linear infinite",
              }}
            >
              Scanning for protected information…
            </p>
          </div>
        ) : (
          /* ── Idle / drag state ───────────────────────────────────────── */
          <div className="flex flex-col items-center gap-0">
            {/* Icon */}
            <div className="mb-5">
              <UploadIcon dragging={dragging} />
            </div>

            {/* Headline */}
            <p
              className="text-xl font-semibold tracking-tight"
              style={{ color: "var(--ink)" }}
            >
              {dragging ? "Release to analyse" : "Drop your lease PDF here"}
            </p>

            {/* Divider row */}
            <div className="my-5 flex w-full items-center gap-3">
              <div
                className="flex-1 h-px"
                style={{ background: "rgba(107,107,99,0.15)" }}
              />
              <span
                className="text-xs font-medium tracking-widest uppercase"
                style={{ color: "var(--ink-subtle)" }}
              >
                or
              </span>
              <div
                className="flex-1 h-px"
                style={{ background: "rgba(107,107,99,0.15)" }}
              />
            </div>

            {/* CTA button */}
            <label
              htmlFor="clause-file-input"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                cursor: "pointer",
                borderRadius: "100px",
                background: "var(--accent)",
                color: "#fff",
                padding: "13px 28px",
                fontSize: "15px",
                fontWeight: 500,
                letterSpacing: "-0.01em",
                boxShadow:
                  "0 2px 12px rgba(217,119,87,0.32), 0 1px 0 rgba(255,255,255,0.18) inset",
                transition: "transform 0.15s, box-shadow 0.15s, background 0.15s",
                userSelect: "none",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)";
                (e.currentTarget as HTMLElement).style.boxShadow =
                  "0 6px 20px rgba(217,119,87,0.38), 0 1px 0 rgba(255,255,255,0.18) inset";
                (e.currentTarget as HTMLElement).style.background = "var(--accent-deep)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.transform = "";
                (e.currentTarget as HTMLElement).style.boxShadow =
                  "0 2px 12px rgba(217,119,87,0.32), 0 1px 0 rgba(255,255,255,0.18) inset";
                (e.currentTarget as HTMLElement).style.background = "var(--accent)";
              }}
            >
              {/* PDF icon */}
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
                <path
                  d="M3 2a1 1 0 011-1h5.586A1 1 0 0110.293 1.293l2.414 2.414A1 1 0 0113 4.414V14a1 1 0 01-1 1H4a1 1 0 01-1-1V2z"
                  fill="rgba(255,255,255,0.25)"
                />
                <path
                  d="M9.5 1v3.5H13"
                  stroke="rgba(255,255,255,0.7)"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <text x="4" y="12.5" fontSize="5" fontWeight="700" fill="white" letterSpacing="0.5">PDF</text>
              </svg>
              Choose a PDF file
              <input
                id="clause-file-input"
                ref={inputRef}
                type="file"
                accept="application/pdf"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handle(f);
                  // reset so re-selecting same file fires onChange
                  e.target.value = "";
                }}
              />
            </label>

            {/* Constraints note */}
            <p
              className="mt-4 text-xs"
              style={{ color: "var(--ink-subtle)" }}
            >
              PDF only · max 10 MB
            </p>
          </div>
        )}

        {/* ── Error banner ─────────────────────────────────────────────── */}
        {error && (
          <div
            role="alert"
            style={{
              marginTop: "20px",
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
              borderRadius: "12px",
              padding: "12px 14px",
              background: "rgba(229,72,77,0.08)",
              border: "1px solid rgba(229,72,77,0.22)",
              animation: "fadeIn 0.2s ease both",
            }}
          >
            {/* Error icon */}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden style={{ flexShrink: 0, marginTop: "1px" }}>
              <circle cx="8" cy="8" r="7" stroke="var(--sev-illegal)" strokeWidth="1.5" />
              <path d="M8 5v3.5M8 10.5v.5" stroke="var(--sev-illegal)" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <p className="text-sm" style={{ color: "var(--sev-illegal)", lineHeight: "1.4" }}>
              {error}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
