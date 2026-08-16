"use client";

import { useEffect, useRef, useState } from "react";

/* Liquid "goo" auth form: stacked email + password pills rendered under an SVG
   goo filter so the coral shapes merge like liquid, with crisp inputs on an
   unfiltered layer on top. The submit blob lives on the password row and emits
   droplets that merge back into it. Extends the original email-only field so
   the two share one visual language. Inspired by gooey.jakubantalik.com. */

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

const ROW = 60; // px height of each liquid pill
const GAP = 12; // px gap between the two pills

/* One liquid pill background - coral, brightens on focus. */
function FieldBlob({ top, focused }: { top: number; focused: boolean }) {
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top,
        height: ROW,
        borderRadius: ROW / 2,
        background: focused ? "rgba(217,119,87,0.20)" : "rgba(217,119,87,0.13)",
        transition: "background 0.3s ease",
      }}
    />
  );
}

export function GooeyAuthForm({
  onSubmit,
  busy,
  error,
}: {
  onSubmit: (email: string, password: string) => void;
  busy: boolean;
  error: string | null;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [focused, setFocused] = useState<"email" | "password" | null>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const id = "clause-gooey-kf";
    if (!document.getElementById(id)) {
      const s = document.createElement("style");
      s.id = id;
      s.textContent = KEYFRAMES;
      document.head.appendChild(s);
    }
    emailRef.current?.focus();
  }, []);

  const submit = () => {
    if (!busy && email.trim() && password) onSubmit(email.trim(), password);
  };

  const passwordTop = ROW + GAP;
  const inputBase: React.CSSProperties = {
    position: "absolute",
    left: 0,
    right: 0,
    height: ROW,
    paddingLeft: "24px",
    paddingRight: "68px",
    borderRadius: ROW / 2,
    border: "none",
    outline: "none",
    background: "transparent",
    color: "var(--ink)",
    fontSize: "16px",
    fontWeight: 500,
    letterSpacing: "-0.01em",
  };

  return (
    <div style={{ width: "100%" }}>
      {/* Hidden goo filter definition */}
      <svg aria-hidden style={{ position: "absolute", width: 0, height: 0 }}>
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
          height: ROW * 2 + GAP,
          transform: focused ? "scale(1.012)" : "scale(1)",
          transition: "transform 0.3s cubic-bezier(.34,1.56,.64,1)",
        }}
      >
        {/* ── Liquid layer (goo-filtered) ─────────────────────────────── */}
        <div
          aria-hidden
          style={{ position: "absolute", inset: 0, filter: "url(#clause-goo)", pointerEvents: "none" }}
        >
          <FieldBlob top={0} focused={focused === "email"} />
          <FieldBlob top={passwordTop} focused={focused === "password"} />

          {/* Submit blob - on the password row, overlapping its right end */}
          <div
            style={{
              position: "absolute",
              right: "4px",
              top: passwordTop + 4,
              width: "52px",
              height: "52px",
              borderRadius: "50%",
              background: "var(--accent)",
              animation: "gooBtnBreath 3s ease-in-out infinite",
            }}
          />
          {/* Emitted droplets - merge back into the blob */}
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              style={{
                position: "absolute",
                right: "18px",
                top: passwordTop + 22,
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
          ref={emailRef}
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="you@email.com"
          value={email}
          disabled={busy}
          onChange={(e) => setEmail(e.target.value)}
          onFocus={() => setFocused("email")}
          onBlur={() => setFocused(null)}
          onKeyDown={(e) => e.key === "Enter" && passwordRef.current?.focus()}
          style={{ ...inputBase, top: 0 }}
        />
        <input
          ref={passwordRef}
          type="password"
          autoComplete="current-password"
          placeholder="Password"
          value={password}
          disabled={busy}
          onChange={(e) => setPassword(e.target.value)}
          onFocus={() => setFocused("password")}
          onBlur={() => setFocused(null)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          style={{ ...inputBase, top: passwordTop }}
        />
        <button
          type="button"
          aria-label="Continue"
          onClick={submit}
          disabled={busy}
          style={{
            position: "absolute",
            right: "4px",
            top: passwordTop + 4,
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
          style={{ marginTop: "12px", fontSize: "13px", color: "var(--sev-illegal)", animation: "fadeIn 0.2s ease both" }}
        >
          {error}
        </p>
      )}
    </div>
  );
}
