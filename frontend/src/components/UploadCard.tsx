"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

/* ─── Keyframes injected once into <head> ────────────────────────────────── */
const KEYFRAMES = `
@keyframes cardReveal {
  from { opacity: 0; transform: translateY(20px) scale(0.985); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes cardDragIn {
  from { transform: scale(1); }
  to   { transform: scale(1.012); }
}
@keyframes shimmer {
  0%   { background-position: -300% center; }
  100% { background-position:  300% center; }
}
@keyframes pulseRing {
  0%, 100% { transform: scale(1);   opacity: 0.55; }
  50%       { transform: scale(1.18); opacity: 0.12; }
}
@keyframes spinArc {
  from { stroke-dashoffset: 220; transform: rotate(0deg); }
  to   { stroke-dashoffset: 0;   transform: rotate(180deg); }
}
@keyframes fullRotate {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes docFloat {
  0%, 100% { transform: translateY(0) rotate(-4deg); }
  50%       { transform: translateY(-9px) rotate(-4deg); }
}
@keyframes haloBreath {
  0%, 100% { transform: scale(1);   opacity: 0.18; }
  50%       { transform: scale(1.28); opacity: 0.06; }
}
@keyframes iconBounce {
  0%, 100% { transform: translateY(0) scale(1); }
  50%       { transform: translateY(-6px) scale(1.08); }
}
@keyframes dropRipple {
  from { transform: scale(0.7); opacity: 0.6; }
  to   { transform: scale(2.2); opacity: 0; }
}
`;

/* ─── Animated progress spinner ─────────────────────────────────────────── */
function ProgressRing() {
  const r = 32;
  const circ = 2 * Math.PI * r;
  return (
    <svg
      width="84" height="84" viewBox="0 0 84 84"
      aria-hidden
      style={{ animation: "fullRotate 1.6s linear infinite" }}
    >
      {/* Track */}
      <circle
        cx="42" cy="42" r={r}
        fill="none"
        stroke="rgba(217,119,87,0.12)"
        strokeWidth="4.5"
      />
      {/* Arc segment */}
      <circle
        cx="42" cy="42" r={r}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="4.5"
        strokeLinecap="round"
        strokeDasharray={`${circ * 0.28} ${circ * 0.72}`}
        style={{ transformOrigin: "42px 42px" }}
      />
    </svg>
  );
}

/* ─── Decorative floating lease document ─────────────────────────────────── */
function FloatingDoc({ style }: { style?: React.CSSProperties }) {
  return (
    <svg
      viewBox="0 0 52 68"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      style={style}
    >
      {/* Paper body */}
      <rect width="52" height="68" rx="6" fill="var(--surface)" />
      {/* Top highlight edge */}
      <rect width="52" height="1.5" rx="1" fill="rgba(255,255,255,0.7)" />
      {/* Text lines */}
      <rect x="9" y="13" width="34" height="3.5" rx="1.75" fill="var(--ink-subtle)" opacity="0.3" />
      <rect x="9" y="22" width="26" height="3.5" rx="1.75" fill="var(--ink-subtle)" opacity="0.2" />
      {/* Flagged line - coral */}
      <rect x="9" y="31" width="30" height="3.5" rx="1.75" fill="var(--sev-illegal)" opacity="0.5" />
      <rect x="9" y="40" width="18" height="3.5" rx="1.75" fill="var(--ink-subtle)" opacity="0.15" />
      <rect x="9" y="49" width="24" height="3.5" rx="1.75" fill="var(--ink-subtle)" opacity="0.1" />
      {/* Flag tab */}
      <rect x="42" y="29" width="10" height="8" rx="1.5" fill="var(--sev-illegal)" opacity="0.65" />
    </svg>
  );
}

/* ─── Upload arrow icon (idle / drag states) ─────────────────────────────── */
function UploadIcon({ dragging }: { dragging: boolean }) {
  return (
    <svg
      width="36" height="36" viewBox="0 0 36 36" fill="none"
      aria-hidden
      style={{
        transition: "transform 0.4s cubic-bezier(.34,1.56,.64,1)",
        transform: dragging ? "translateY(-6px) scale(1.15)" : "translateY(0) scale(1)",
      }}
    >
      <path
        d="M18 24V12M18 12l-5 5M18 12l5 5"
        stroke="var(--accent)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9 26h18"
        stroke="var(--accent)"
        strokeWidth="2"
        strokeLinecap="round"
        opacity="0.45"
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

  /* warmup backend */
  useEffect(() => {
    api.warmup();
  }, []);

  /* file handler - validation + upload flow */
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

  /* drag event handlers */
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
    >
      {/* ── Outer glass card ───────────────────────────────────────────── */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        style={{
          position: "relative",
          borderRadius: "28px",
          padding: "52px 44px 44px",
          overflow: "hidden",
          /* Layered glass */
          background: dragging
            ? "rgba(252,250,247,0.82)"
            : "rgba(250,249,245,0.74)",
          backdropFilter: "blur(24px) saturate(1.5)",
          WebkitBackdropFilter: "blur(24px) saturate(1.5)",
          /* Border: inner top highlight + outer ring */
          border: dragging
            ? "1.5px solid var(--accent)"
            : "1.5px solid rgba(255,255,255,0.55)",
          outline: dragging
            ? "none"
            : "1px solid rgba(107,107,99,0.14)",
          outlineOffset: "-2px",
          /* Shadows: ambient depth + key light from top */
          boxShadow: dragging
            ? `
              0 0 0 5px rgba(217,119,87,0.10),
              0 0 0 12px rgba(217,119,87,0.04),
              0 20px 60px rgba(20,20,19,0.13),
              0 1px 0 rgba(255,255,255,0.9) inset
            `
            : `
              0 4px 6px rgba(20,20,19,0.04),
              0 10px 40px rgba(20,20,19,0.09),
              0 32px 72px rgba(20,20,19,0.06),
              0 1px 0 rgba(255,255,255,0.9) inset
            `,
          /* Drag scale */
          transform: dragging ? "scale(1.012)" : "scale(1)",
          transition: [
            "border-color 0.2s ease",
            "box-shadow 0.25s ease",
            "background 0.2s ease",
            "transform 0.3s cubic-bezier(.34,1.56,.64,1)",
            "outline-color 0.2s ease",
          ].join(", "),
        }}
      >
        {/* ── Top highlight gradient (glass top-edge sheen) ──────────── */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            top: 0,
            left: "10%",
            right: "10%",
            height: "1px",
            background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.85) 50%, transparent)",
            pointerEvents: "none",
          }}
        />

        {/* ── Decorative floating docs ────────────────────────────────── */}
        <FloatingDoc
          style={{
            position: "absolute",
            top: "-14px",
            right: "-10px",
            width: "60px",
            opacity: 0.38,
            animation: "docFloat 4.2s ease-in-out infinite",
          }}
        />
        <FloatingDoc
          style={{
            position: "absolute",
            bottom: "-8px",
            left: "-8px",
            width: "38px",
            opacity: 0.18,
            animation: "docFloat 5.8s ease-in-out 1.1s infinite",
          }}
        />

        {/* ── Drag overlay radial glow ────────────────────────────────── */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "inherit",
            background: dragging
              ? "radial-gradient(ellipse 70% 60% at 50% 45%, rgba(217,119,87,0.10) 0%, transparent 80%)"
              : "transparent",
            pointerEvents: "none",
            transition: "background 0.3s ease",
          }}
        />

        {/* ── BUSY STATE ─────────────────────────────────────────────── */}
        {busy ? (
          <div
            className="flex flex-col items-center gap-6 py-6"
            style={{ animation: "fadeSlideUp 0.35s ease both" }}
          >
            {/* Spinner with pulse halo */}
            <div style={{ position: "relative", display: "inline-flex" }}>
              <div
                aria-hidden
                style={{
                  position: "absolute",
                  inset: "-16px",
                  borderRadius: "50%",
                  background: "var(--accent)",
                  animation: "pulseRing 1.8s ease-in-out infinite",
                }}
              />
              <ProgressRing />
              {/* Centre dot */}
              <div
                aria-hidden
                style={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%,-50%)",
                  width: "10px",
                  height: "10px",
                  borderRadius: "50%",
                  background: "var(--accent)",
                  opacity: 0.7,
                }}
              />
            </div>

            <div className="flex flex-col items-center gap-2">
              <p
                className="text-[15px] font-semibold"
                style={{ color: "var(--ink)", letterSpacing: "-0.02em" }}
              >
                Uploading your lease
              </p>
              {/* Shimmer sub-text */}
              <p
                className="text-sm"
                style={{
                  background: "linear-gradient(90deg, var(--ink-subtle) 0%, var(--accent) 40%, var(--accent-deep) 60%, var(--ink-subtle) 100%)",
                  backgroundSize: "300% auto",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                  animation: "shimmer 2.4s linear infinite",
                  letterSpacing: "0.005em",
                }}
              >
                Scanning for protected information…
              </p>
            </div>
          </div>
        ) : (
          /* ── IDLE / DRAG STATE ─────────────────────────────────────── */
          <div className="flex flex-col items-center gap-0">

            {/* Icon with idle halo */}
            <div
              className="mb-5"
              style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
            >
              {/* Halo - only when not dragging */}
              {!dragging && (
                <div
                  aria-hidden
                  style={{
                    position: "absolute",
                    width: "72px",
                    height: "72px",
                    borderRadius: "50%",
                    background: "radial-gradient(circle, var(--accent) 0%, transparent 70%)",
                    animation: "haloBreath 3s ease-in-out infinite",
                    pointerEvents: "none",
                  }}
                />
              )}
              {/* Icon container */}
              <div
                style={{
                  position: "relative",
                  width: "52px",
                  height: "52px",
                  borderRadius: "16px",
                  background: dragging
                    ? "rgba(217,119,87,0.16)"
                    : "rgba(217,119,87,0.10)",
                  border: "1px solid rgba(217,119,87,0.18)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "background 0.2s ease",
                }}
              >
                <UploadIcon dragging={dragging} />
              </div>
            </div>

            {/* Headline */}
            <p
              style={{
                fontSize: "17px",
                fontWeight: 600,
                letterSpacing: "-0.025em",
                color: "var(--ink)",
                lineHeight: 1.3,
              }}
            >
              {dragging ? "Release to analyse" : "Drop your lease PDF here"}
            </p>

            {/* - or - divider */}
            <div
              className="my-5 flex w-full items-center gap-4"
              style={{ maxWidth: "280px" }}
            >
              <div style={{ flex: 1, height: "1px", background: "rgba(107,107,99,0.14)" }} />
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 500,
                  letterSpacing: "0.10em",
                  textTransform: "uppercase",
                  color: "var(--ink-subtle)",
                }}
              >
                or
              </span>
              <div style={{ flex: 1, height: "1px", background: "rgba(107,107,99,0.14)" }} />
            </div>

            {/* CTA button */}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "7px",
                cursor: "pointer",
                border: "none",
                borderRadius: "100px",
                background: "var(--accent)",
                color: "#fff",
                padding: "12px 26px",
                fontSize: "14px",
                fontWeight: 500,
                letterSpacing: "-0.01em",
                boxShadow: [
                  "0 2px 10px rgba(217,119,87,0.30)",
                  "0 6px 24px rgba(217,119,87,0.16)",
                  "0 1px 0 rgba(255,255,255,0.2) inset",
                ].join(", "),
                transition: "transform 0.16s cubic-bezier(.34,1.56,.64,1), box-shadow 0.16s ease, background 0.14s ease",
                userSelect: "none",
              }}
              onMouseEnter={(e) => {
                const el = e.currentTarget as HTMLElement;
                el.style.transform = "translateY(-2px)";
                el.style.background = "var(--accent-deep)";
                el.style.boxShadow = [
                  "0 4px 16px rgba(217,119,87,0.38)",
                  "0 10px 32px rgba(217,119,87,0.18)",
                  "0 1px 0 rgba(255,255,255,0.2) inset",
                ].join(", ");
              }}
              onMouseLeave={(e) => {
                const el = e.currentTarget as HTMLElement;
                el.style.transform = "";
                el.style.background = "var(--accent)";
                el.style.boxShadow = [
                  "0 2px 10px rgba(217,119,87,0.30)",
                  "0 6px 24px rgba(217,119,87,0.16)",
                  "0 1px 0 rgba(255,255,255,0.2) inset",
                ].join(", ");
              }}
            >
              {/* PDF badge icon */}
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden>
                <rect width="15" height="15" rx="4" fill="rgba(255,255,255,0.18)" />
                <path d="M4 2.5h5l3 3V12a.5.5 0 01-.5.5h-7A.5.5 0 014 12V2.5z" fill="rgba(255,255,255,0.2)" />
                <path d="M9 2.5V5.5H12" stroke="rgba(255,255,255,0.65)" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" />
                <text x="4.5" y="11" fontSize="3.8" fontWeight="700" fill="white" letterSpacing="0.3">PDF</text>
              </svg>
              Choose a PDF file
            </button>
            {/* Visually-hidden (not display:none) file input triggered via ref.
                Safari won't open the picker for a programmatic .click() on a
                display:none input, so we keep it in the layout but invisible.
                Kept a sibling of the button to avoid the label+for+nested-input
                double-activation quirk. */}
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              tabIndex={-1}
              aria-hidden
              style={{
                position: "absolute",
                width: 1,
                height: 1,
                padding: 0,
                margin: -1,
                border: 0,
                opacity: 0,
                overflow: "hidden",
                clipPath: "inset(50%)",
                pointerEvents: "none",
              }}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handle(f);
                e.target.value = "";
              }}
            />

            {/* Constraint note */}
            <p
              className="mt-4"
              style={{ fontSize: "11px", color: "var(--ink-subtle)", letterSpacing: "0.02em" }}
            >
              PDF only &nbsp;·&nbsp; max 10 MB
            </p>
          </div>
        )}

        {/* ── Error banner ─────────────────────────────────────────────── */}
        {error && (
          <div
            role="alert"
            style={{
              marginTop: "22px",
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
              borderRadius: "14px",
              padding: "13px 15px",
              background: "rgba(229,72,77,0.07)",
              border: "1px solid rgba(229,72,77,0.20)",
              boxShadow: "0 2px 12px rgba(229,72,77,0.07)",
              animation: "fadeSlideUp 0.22s ease both",
            }}
          >
            <svg
              width="15" height="15" viewBox="0 0 15 15" fill="none"
              aria-hidden
              style={{ flexShrink: 0, marginTop: "1px" }}
            >
              <circle cx="7.5" cy="7.5" r="6.5" stroke="var(--sev-illegal)" strokeWidth="1.4" />
              <path d="M7.5 4.5v3.2M7.5 9.8v.5" stroke="var(--sev-illegal)" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
            <p style={{ fontSize: "13px", color: "var(--sev-illegal)", lineHeight: 1.45 }}>
              {error}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
