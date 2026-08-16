"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { ChurningLoader } from "@/components/ChurningLoader";

/* ─── Keyframes injected once into <head> ────────────────────────────────── */
const KEYFRAMES = `
@keyframes orbitSpin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
@keyframes orbitSpinReverse {
  from { transform: rotate(0deg); }
  to   { transform: rotate(-360deg); }
}
@keyframes scanPulse {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50%       { opacity: 1;   transform: scale(1.08); }
}
@keyframes sheenSlide {
  0%   { transform: translateX(-120%); }
  100% { transform: translateX(220%); }
}
@keyframes msgFadeUp {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes subMsgFade {
  0%   { opacity: 0; transform: translateY(4px); }
  15%  { opacity: 1; transform: translateY(0); }
  85%  { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-4px); }
}
@keyframes dotPulse {
  0%, 100% { transform: scale(1);   opacity: 1; }
  50%       { transform: scale(1.5); opacity: 0.4; }
}
@keyframes cardEnter {
  from { opacity: 0; transform: translateY(24px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0)    scale(1); }
}
@keyframes pillEnter {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes failShake {
  0%, 100% { transform: translateX(0); }
  20%       { transform: translateX(-6px); }
  40%       { transform: translateX(6px); }
  60%       { transform: translateX(-4px); }
  80%       { transform: translateX(4px); }
}
@keyframes orbitDot {
  0%   { transform: rotate(0deg)   translateX(38px) rotate(0deg); }
  100% { transform: rotate(360deg) translateX(38px) rotate(-360deg); }
}
@keyframes orbitDotReverse {
  0%   { transform: rotate(0deg)    translateX(48px) rotate(0deg); }
  100% { transform: rotate(-360deg) translateX(48px) rotate(360deg); }
}
`;

/* ─── Rotating reassurance sub-messages ─────────────────────────────────── */
const SUB_MESSAGES = [
  "Reading every paragraph carefully…",
  "Matching clauses against tenant-protection law…",
  "Identifying unusual or one-sided language…",
  "Estimating potential recovery amounts…",
  "Checking for illegal fee structures…",
  "Reviewing notice and termination provisions…",
  "Almost there, compiling your report…",
];

/* ─── Progress bar with traveling sheen ─────────────────────────────────── */
function ProgressBar({ progress, failed }: { progress: number; failed: boolean }) {
  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "6px",
        borderRadius: "100px",
        background: "rgba(107,107,99,0.10)",
        overflow: "hidden",
      }}
    >
      {/* Fill */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          width: `${progress}%`,
          borderRadius: "inherit",
          background: failed
            ? "var(--sev-illegal)"
            : "linear-gradient(90deg, var(--accent-deep), var(--accent) 60%, #E8A47A)",
          transition: "width 0.8s cubic-bezier(.16,1,.3,1)",
          boxShadow: failed
            ? "0 0 10px rgba(229,72,77,0.35)"
            : "0 0 12px rgba(217,119,87,0.45)",
        }}
      >
        {/* Traveling sheen - only when not failed */}
        {!failed && (
          <div
            aria-hidden
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              width: "40%",
              background:
                "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.55) 50%, transparent 100%)",
              animation: "sheenSlide 1.8s ease-in-out infinite",
              borderRadius: "inherit",
            }}
          />
        )}
      </div>
    </div>
  );
}

/* ─── Rotating sub-message ───────────────────────────────────────────────── */
function SubMessage() {
  const [idx, setIdx] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const interval = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setIdx((i) => (i + 1) % SUB_MESSAGES.length);
        setVisible(true);
      }, 400);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <p
      key={idx}
      style={{
        fontSize: "13px",
        color: "var(--ink-subtle)",
        letterSpacing: "0.005em",
        lineHeight: 1.5,
        minHeight: "20px",
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(4px)",
        transition: "opacity 0.4s ease, transform 0.4s ease",
      }}
    >
      {SUB_MESSAGES[idx]}
    </p>
  );
}

/* ─── PII protection note ────────────────────────────────────────────────── */
function PiiNote({ piiCount }: { piiCount: number | null }) {
  const hasCount = piiCount !== null && piiCount > 0;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "10px 16px",
        borderRadius: "100px",
        background: "rgba(63,163,114,0.07)",
        border: "1px solid rgba(63,163,114,0.16)",
        animation: "pillEnter 0.55s cubic-bezier(.16,1,.3,1) 0.5s both",
      }}
    >
      {/* Animated status dot */}
      <span
        aria-hidden
        style={{ position: "relative", display: "inline-flex", width: "10px", height: "10px", flexShrink: 0 }}
      >
        <span
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            background: "var(--sev-favorable)",
            animation: "dotPulse 2.4s ease-in-out infinite",
          }}
        />
        <span
          style={{
            position: "relative",
            margin: "auto",
            width: "5px",
            height: "5px",
            borderRadius: "50%",
            background: "var(--sev-favorable)",
          }}
        />
      </span>
      <span style={{ fontSize: "12px", color: "#3FA372", letterSpacing: "0.01em" }}>
        {hasCount
          ? `${piiCount} piece${piiCount === 1 ? "" : "s"} of personal information protected`
          : "Personal information is protected, never stored"}
      </span>
    </div>
  );
}

/* ─── Inner Processing component (uses useSearchParams) ──────────────────── */
function Processing() {
  const params = useSearchParams();
  const router = useRouter();
  const fileId = params.get("file_id")!;

  const [progress, setProgress] = useState(10);
  const [message, setMessage] = useState("Starting analysis…");
  const [failed, setFailed] = useState(false);
  const [piiCount, setPiiCount] = useState<number | null>(null);

  /* Read PII count from sessionStorage once */
  useEffect(() => {
    const readPii = () => {
      try {
        const raw = sessionStorage.getItem("pii");
        if (raw) {
          const obj: Record<string, number> = JSON.parse(raw);
          const total = Object.values(obj).reduce((s, n) => s + n, 0);
          if (total > 0) setPiiCount(total);
        }
      } catch {
        /* ignore */
      }
    };
    readPii();
  }, []);

  /* Inject keyframes once */
  const kfInjected = useRef(false);
  useEffect(() => {
    if (kfInjected.current) return;
    kfInjected.current = true;
    const id = "clause-processing-kf";
    if (!document.getElementById(id)) {
      const s = document.createElement("style");
      s.id = id;
      s.textContent = KEYFRAMES;
      document.head.appendChild(s);
    }
  }, []);

  /* Polling loop */
  useEffect(() => {
    let active = true;
    const tick = async () => {
      try {
        const s = await api.status(fileId);
        if (!active) return;
        setProgress(s.progress);
        setMessage(s.message);
        if (s.status === "completed") {
          router.push(`/results/${fileId}`);
          return;
        }
        if (s.status === "failed") {
          setFailed(true);
          setMessage("Analysis failed. Please try again.");
          return;
        }
      } catch {
        /* tolerate cold-start blips - continue polling */
      }
      if (active) setTimeout(tick, 1000);
    };
    tick();
    return () => {
      active = false;
    };
  }, [fileId, router]);

  return (
    <main
      className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center px-6"
      style={{ gap: "20px" }}
    >
      {/* ── Glass card ─────────────────────────────────────────────────── */}
      <div
        style={{
          width: "100%",
          borderRadius: "28px",
          padding: "48px 44px 44px",
          position: "relative",
          overflow: "hidden",
          /* Layered glass */
          background: "rgba(250,249,245,0.74)",
          backdropFilter: "blur(24px) saturate(1.5)",
          WebkitBackdropFilter: "blur(24px) saturate(1.5)",
          /* Border */
          border: "1.5px solid rgba(255,255,255,0.55)",
          outline: "1px solid rgba(107,107,99,0.14)",
          outlineOffset: "-2px",
          /* Shadow */
          boxShadow: [
            "0 4px 6px rgba(20,20,19,0.04)",
            "0 10px 40px rgba(20,20,19,0.09)",
            "0 32px 72px rgba(20,20,19,0.06)",
            "0 1px 0 rgba(255,255,255,0.9) inset",
          ].join(", "),
          animation: "cardEnter 0.65s cubic-bezier(.16,1,.3,1) both",
        }}
      >
        {/* Top-edge sheen */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            top: 0,
            left: "10%",
            right: "10%",
            height: "1px",
            background:
              "linear-gradient(90deg, transparent, rgba(255,255,255,0.85) 50%, transparent)",
            pointerEvents: "none",
          }}
        />

        {/* Subtle inner glow - bottom right */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            bottom: "-30px",
            right: "-30px",
            width: "180px",
            height: "180px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(217,119,87,0.09) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />

        {/* ── Content ─────────────────────────────────────────────────── */}
        <div className="flex flex-col items-center gap-8">

          {/* Churning pixel-grid loader */}
          <ChurningLoader failed={failed} />

          {/* Text block */}
          <div className="flex w-full flex-col items-center gap-2 text-center">
            {/* Wordmark label */}
            <p
              style={{
                fontSize: "10px",
                fontWeight: 700,
                letterSpacing: "0.16em",
                textTransform: "uppercase",
                color: "var(--accent)",
                opacity: 0.7,
                marginBottom: "2px",
              }}
            >
              Clause
            </p>

            {/* Primary backend message */}
            <p
              key={message}
              style={{
                fontSize: "17px",
                fontWeight: 600,
                letterSpacing: "-0.025em",
                color: failed ? "var(--sev-illegal)" : "var(--ink)",
                lineHeight: 1.35,
                animation: "msgFadeUp 0.35s ease both",
              }}
            >
              {message}
            </p>

            {/* Rotating secondary message - only while running */}
            {!failed && <SubMessage />}
          </div>

          {/* Progress bar + percentage */}
          <div className="flex w-full flex-col gap-2">
            <ProgressBar progress={progress} failed={failed} />
            <div className="flex items-center justify-between">
              <span
                style={{ fontSize: "11px", color: "var(--ink-subtle)", letterSpacing: "0.02em" }}
              >
                {failed ? "Error" : progress < 100 ? "Analysing" : "Complete"}
              </span>
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: failed ? "var(--sev-illegal)" : "var(--accent-deep)",
                  letterSpacing: "-0.01em",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {progress}%
              </span>
            </div>
          </div>

          {/* Start over - only on failure so the user is never stranded */}
          {failed && (
            <button
              type="button"
              onClick={() => router.push("/")}
              style={{
                borderRadius: "100px",
                background: "var(--accent)",
                color: "#fff",
                border: "none",
                cursor: "pointer",
                padding: "10px 24px",
                fontSize: "14px",
                fontWeight: 600,
                boxShadow: "0 2px 10px rgba(217,119,87,0.28)",
                transition: "background 0.15s ease",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--accent-deep)"; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--accent)"; }}
            >
              Start over
            </button>
          )}

          {/* Divider */}
          <div
            aria-hidden
            style={{
              width: "100%",
              height: "1px",
              background: "rgba(107,107,99,0.10)",
            }}
          />

          {/* Step indicators */}
          <div className="flex w-full items-center justify-center gap-6">
            {[
              { label: "Upload", done: true },
              { label: "Analysis", done: progress >= 90 },
              { label: "Report", done: false },
            ].map((step, i) => (
              <div key={step.label} className="flex items-center gap-2">
                {i > 0 && (
                  <div
                    aria-hidden
                    style={{
                      width: "20px",
                      height: "1px",
                      background: step.done
                        ? "var(--accent)"
                        : "rgba(107,107,99,0.18)",
                      transition: "background 0.6s ease",
                    }}
                  />
                )}
                <div className="flex flex-col items-center gap-1">
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: step.done
                        ? "var(--accent)"
                        : "rgba(107,107,99,0.20)",
                      boxShadow: step.done
                        ? "0 0 8px rgba(217,119,87,0.45)"
                        : "none",
                      transition: "background 0.6s ease, box-shadow 0.6s ease",
                    }}
                  />
                  <span
                    style={{
                      fontSize: "9px",
                      fontWeight: 600,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      color: step.done ? "var(--accent-deep)" : "var(--ink-subtle)",
                      opacity: step.done ? 1 : 0.55,
                      transition: "color 0.6s ease, opacity 0.6s ease",
                    }}
                  >
                    {step.label}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── PII note pill - below card ──────────────────────────────────── */}
      <PiiNote piiCount={piiCount} />
    </main>
  );
}

/* ─── Page export with required Suspense boundary ────────────────────────── */
export default function Page() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center">
          <p
            style={{
              fontSize: "14px",
              color: "var(--ink-subtle)",
              letterSpacing: "0.01em",
            }}
          >
            Loading…
          </p>
        </main>
      }
    >
      <Processing />
    </Suspense>
  );
}
