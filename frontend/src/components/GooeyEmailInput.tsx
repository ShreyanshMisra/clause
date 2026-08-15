"use client";

import { useEffect, useRef, useState } from "react";

/* Liquid "goo" email field. A coral liquid layer (field pill + submit blob +
   emitted droplets) is rendered under an SVG goo filter so the shapes merge
   like liquid; the crisp <input> and button label sit on an unfiltered layer
   on top so text stays sharp. Inspired by gooey.jakubantalik.com. */

const KEYFRAMES = `
@keyframes gooDrop1 {
  0%,100% { transform: translate(0,0) scale(0.9); opacity: 0; }
  20%     { opacity: 1; }
  55%     { transform: translate(-34px,-6px) scale(1); opacity: 1; }
  85%     { transform: translate(-8px,4px) scale(0.7); opacity: 0.6; }
}
@keyframes gooDrop2 {
  0%,100% { transform: translate(0,0) scale(0.8); opacity: 0; }
  25%     { opacity: 1; }
  60%     { transform: translate(-30px,8px) scale(0.95); opacity: 1; }
  90%     { transform: translate(-6px,-4px) scale(0.6); opacity: 0.5; }
}
@keyframes gooDrop3 {
  0%,100% { transform: translate(0,0) scale(0.7); opacity: 0; }
  30%     { opacity: 0.9; }
  65%     { transform: translate(-42px,-2px) scale(0.85); opacity: 0.9; }
}
@keyframes gooBtnBreath {
  0%,100% { transform: scale(1); }
  50%     { transform: scale(1.06); }
}
@keyframes fullRotate {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
`;

export function GooeyEmailInput({
  onSubmit,
  busy,
  error,
}: {
  onSubmit: (email: string) => void;
  busy: boolean;
  error: string | null;
}) {
  const [email, setEmail] = useState("");
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const id = "clause-gooey-kf";
    if (!document.getElementById(id)) {
      const s = document.createElement("style");
      s.id = id;
      s.textContent = KEYFRAMES;
      document.head.appendChild(s);
    }
    inputRef.current?.focus();
  }, []);

  const submit = () => {
    if (!busy && email.trim()) onSubmit(email.trim());
  };

  return (
    <div style={{ width: "100%" }}>
      {/* Hidden goo filter definition */}
      <svg
        aria-hidden
        style={{ position: "absolute", width: 0, height: 0 }}
      >
        <defs>
          <filter id="clause-goo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="7" result="blur" />
            <feColorMatrix
              in="blur"
              mode="matrix"
              values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -11"
              result="goo"
            />
            <feBlend in="SourceGraphic" in2="goo" />
          </filter>
        </defs>
      </svg>

      <div
        style={{
          position: "relative",
          height: "60px",
          transform: focused ? "scale(1.015)" : "scale(1)",
          transition: "transform 0.3s cubic-bezier(.34,1.56,.64,1)",
        }}
      >
        {/* ── Liquid layer (goo-filtered) ─────────────────────────────── */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            filter: "url(#clause-goo)",
            pointerEvents: "none",
          }}
        >
          {/* Field pill */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: "30px",
              background: focused
                ? "rgba(217,119,87,0.20)"
                : "rgba(217,119,87,0.13)",
              transition: "background 0.3s ease",
            }}
          />
          {/* Submit blob (right) — overlaps the pill so they merge */}
          <div
            style={{
              position: "absolute",
              right: "4px",
              top: "4px",
              width: "52px",
              height: "52px",
              borderRadius: "50%",
              background: "var(--accent)",
              animation: "gooBtnBreath 3s ease-in-out infinite",
            }}
          />
          {/* Emitted droplets — merge back into the blob */}
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              style={{
                position: "absolute",
                right: "18px",
                top: "22px",
                width: `${16 - i * 3}px`,
                height: `${16 - i * 3}px`,
                borderRadius: "50%",
                background: "var(--accent)",
                animation: `gooDrop${i + 1} ${3.2 + i * 0.6}s ease-in-out ${i * 0.5}s infinite`,
              }}
            />
          ))}
        </div>

        {/* ── Crisp interactive layer ─────────────────────────────────── */}
        <input
          ref={inputRef}
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="you@email.com"
          value={email}
          disabled={busy}
          onChange={(e) => setEmail(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            paddingLeft: "24px",
            paddingRight: "68px",
            borderRadius: "30px",
            border: "none",
            outline: "none",
            background: "transparent",
            color: "var(--ink)",
            fontSize: "16px",
            fontWeight: 500,
            letterSpacing: "-0.01em",
          }}
        />
        <button
          type="button"
          aria-label="Continue"
          onClick={submit}
          disabled={busy}
          style={{
            position: "absolute",
            right: "4px",
            top: "4px",
            width: "52px",
            height: "52px",
            borderRadius: "50%",
            border: "none",
            background: "transparent",
            cursor: busy ? "default" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {busy ? (
            <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden
              style={{ animation: "fullRotate 0.9s linear infinite" }}>
              <circle cx="11" cy="11" r="8" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="2.5" />
              <path d="M11 3a8 8 0 018 8" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
              <path d="M4 10h11M10 5l5 5-5 5" stroke="#fff" strokeWidth="2.2"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </button>
      </div>

      {error && (
        <p
          role="alert"
          style={{
            marginTop: "12px",
            fontSize: "13px",
            color: "var(--sev-illegal)",
            animation: "fadeIn 0.2s ease both",
          }}
        >
          {error}
        </p>
      )}
    </div>
  );
}
