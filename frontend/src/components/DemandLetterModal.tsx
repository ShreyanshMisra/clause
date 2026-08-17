"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/* ─── Keyframes injected once into <head> ────────────────────────────────── */
const KEYFRAMES = `
@keyframes dlBackdropIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes dlCardIn {
  from { opacity: 0; transform: translateY(18px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0)    scale(1);    }
}
@keyframes dlShimmer {
  0%   { background-position: -300% center; }
  100% { background-position:  300% center; }
}
@keyframes dlSpinArc {
  from { transform: rotate(0deg);   }
  to   { transform: rotate(360deg); }
}
@keyframes dlFadeSlide {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0);   }
}
`;

/* ─── Tiny spinner ───────────────────────────────────────────────────────── */
function Spinner() {
  const r = 9;
  const circ = 2 * Math.PI * r;
  return (
    <svg
      width="22" height="22" viewBox="0 0 22 22" fill="none"
      aria-hidden
      style={{ animation: "dlSpinArc 1.4s linear infinite", flexShrink: 0 }}
    >
      <circle cx="11" cy="11" r={r} stroke="rgba(255,255,255,0.22)" strokeWidth="2.5" />
      <circle
        cx="11" cy="11" r={r}
        stroke="white"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray={`${circ * 0.28} ${circ * 0.72}`}
        style={{ transformOrigin: "11px 11px" }}
      />
    </svg>
  );
}

/* ─── Section label ──────────────────────────────────────────────────────── */
function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "20px" }}>
      <p style={{
        fontSize: "10px",
        fontWeight: 600,
        letterSpacing: "0.10em",
        textTransform: "uppercase",
        color: "var(--ink-subtle)",
        marginBottom: "8px",
      }}>
        {label}
      </p>
      {children}
    </div>
  );
}

/* ─── Styled input ───────────────────────────────────────────────────────── */
function Field({
  placeholder,
  value,
  onChange,
  multiline,
}: {
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
}) {
  const [focused, setFocused] = useState(false);

  const sharedStyle: React.CSSProperties = {
    width: "100%",
    borderRadius: "14px",
    border: focused
      ? "1.5px solid var(--accent)"
      : "1.5px solid rgba(107,107,99,0.18)",
    background: focused
      ? "rgba(255,255,255,0.88)"
      : "rgba(255,255,255,0.60)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    padding: "11px 14px",
    fontSize: "14px",
    color: "var(--ink)",
    outline: "none",
    boxShadow: focused
      ? "0 0 0 3px rgba(217,119,87,0.12), 0 2px 8px rgba(20,20,19,0.06)"
      : "0 1px 4px rgba(20,20,19,0.05)",
    transition: "border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease",
    resize: "none" as const,
    fontFamily: "inherit",
    lineHeight: 1.5,
    display: "block",
    boxSizing: "border-box" as const,
    marginBottom: "8px",
  };

  if (multiline) {
    return (
      <textarea
        placeholder={placeholder}
        value={value}
        rows={2}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={sharedStyle}
      />
    );
  }

  return (
    <input
      type="text"
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      style={sharedStyle}
    />
  );
}

/* ─── Main component ─────────────────────────────────────────────────────── */
export function DemandLetterModal({
  fileId,
  onClose,
  meta,
}: {
  fileId: string;
  onClose: () => void;
  meta?: { parties?: { landlord?: string; tenant?: string; property?: string } };
}) {
  // Prefill from the extracted parties — tenant sends, landlord receives — so the
  // user isn't retyping what we already parsed.
  const [sender, setSender] = useState({ name: meta?.parties?.tenant ?? "", address: "" });
  const [recipient, setRecipient] = useState({
    name: meta?.parties?.landlord ?? "",
    address: meta?.parties?.property ?? "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* Inject keyframes once */
  useEffect(() => {
    const id = "clause-dl-kf";
    if (!document.getElementById(id)) {
      const s = document.createElement("style");
      s.id = id;
      s.textContent = KEYFRAMES;
      document.head.appendChild(s);
    }
  }, []);

  /* Close on Escape */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [busy, onClose]);

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.demandLetter(fileId, sender, recipient);
      if (!res.ok) throw new Error("Failed to generate letter");
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "demand-letter.pdf";
      link.click();
      URL.revokeObjectURL(link.href);
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    /* ── Backdrop ─────────────────────────────────────────────────────────── */
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Generate demand letter"
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px",
        background: "rgba(20,18,16,0.36)",
        backdropFilter: "blur(6px)",
        WebkitBackdropFilter: "blur(6px)",
        animation: "dlBackdropIn 0.22s ease both",
      }}
    >
      {/* ── Card ──────────────────────────────────────────────────────────── */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "relative",
          width: "100%",
          maxWidth: "440px",
          borderRadius: "28px",
          overflow: "hidden",
          /* Warm glass */
          background: "rgba(250,249,245,0.80)",
          backdropFilter: "blur(32px) saturate(1.6)",
          WebkitBackdropFilter: "blur(32px) saturate(1.6)",
          border: "1.5px solid rgba(255,255,255,0.62)",
          boxShadow: [
            "0 4px 6px rgba(20,18,16,0.04)",
            "0 16px 48px rgba(20,18,16,0.14)",
            "0 40px 80px rgba(20,18,16,0.10)",
            "0 1px 0 rgba(255,255,255,0.90) inset",
          ].join(", "),
          animation: "dlCardIn 0.28s cubic-bezier(0.34,1.46,0.64,1) both",
          padding: "32px 32px 28px",
        }}
      >
        {/* Top-edge highlight sheen */}
        <div aria-hidden style={{
          position: "absolute",
          top: 0,
          left: "12%",
          right: "12%",
          height: "1px",
          background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.90) 50%, transparent)",
          pointerEvents: "none",
        }} />

        {/* Accent warm glow in upper-right corner */}
        <div aria-hidden style={{
          position: "absolute",
          top: "-30px",
          right: "-30px",
          width: "120px",
          height: "120px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(217,119,87,0.12) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "28px" }}>
          <div>
            {/* Small pill label */}
            <div style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              borderRadius: "100px",
              background: "rgba(217,119,87,0.10)",
              border: "1px solid rgba(217,119,87,0.20)",
              padding: "3px 10px 3px 7px",
              marginBottom: "8px",
            }}>
              {/* Doc icon */}
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
                <rect x="1" y="0.5" width="8" height="11" rx="1.5" fill="none" stroke="var(--accent)" strokeWidth="1.2" />
                <path d="M3 4h6M3 6.5h4" stroke="var(--accent)" strokeWidth="1.1" strokeLinecap="round" />
              </svg>
              <span style={{ fontSize: "10px", fontWeight: 600, letterSpacing: "0.06em", color: "var(--accent)", textTransform: "uppercase" }}>
                Legal document
              </span>
            </div>
            <h2 style={{
              fontSize: "20px",
              fontWeight: 700,
              letterSpacing: "-0.03em",
              color: "var(--ink)",
              lineHeight: 1.2,
              margin: 0,
            }}>
              Generate demand letter
            </h2>
            <p style={{
              marginTop: "4px",
              fontSize: "13px",
              color: "var(--ink-subtle)",
              lineHeight: 1.5,
            }}>
              Enter the parties below. A PDF will download automatically.
            </p>
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            aria-label="Close"
            disabled={busy}
            style={{
              flexShrink: 0,
              marginLeft: "12px",
              marginTop: "-2px",
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              border: "1.5px solid rgba(107,107,99,0.18)",
              background: "rgba(255,255,255,0.60)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: busy ? "not-allowed" : "pointer",
              opacity: busy ? 0.4 : 1,
              transition: "background 0.15s ease, border-color 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (!busy) {
                (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.90)";
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(107,107,99,0.30)";
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.60)";
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(107,107,99,0.18)";
            }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden>
              <path d="M1 1l8 8M9 1L1 9" stroke="var(--ink-subtle)" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* ── Divider ─────────────────────────────────────────────────────── */}
        <div style={{ height: "1px", background: "rgba(107,107,99,0.10)", marginBottom: "24px" }} />

        {/* ── Form fields ─────────────────────────────────────────────────── */}
        <FieldGroup label="Your details">
          <Field
            placeholder="Your full name"
            value={sender.name}
            onChange={(v) => setSender({ ...sender, name: v })}
          />
          <Field
            placeholder="Your address"
            value={sender.address}
            onChange={(v) => setSender({ ...sender, address: v })}
            multiline
          />
        </FieldGroup>

        <FieldGroup label="Landlord details">
          <Field
            placeholder="Landlord name"
            value={recipient.name}
            onChange={(v) => setRecipient({ ...recipient, name: v })}
          />
          <Field
            placeholder="Landlord address"
            value={recipient.address}
            onChange={(v) => setRecipient({ ...recipient, address: v })}
            multiline
          />
        </FieldGroup>

        {/* ── Error banner ────────────────────────────────────────────────── */}
        {error && (
          <div
            role="alert"
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "9px",
              borderRadius: "12px",
              padding: "11px 13px",
              background: "rgba(229,72,77,0.07)",
              border: "1px solid rgba(229,72,77,0.20)",
              marginBottom: "18px",
              animation: "dlFadeSlide 0.20s ease both",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden style={{ flexShrink: 0, marginTop: "1px" }}>
              <circle cx="7" cy="7" r="6" stroke="var(--sev-illegal)" strokeWidth="1.3" />
              <path d="M7 4v3M7 9v.5" stroke="var(--sev-illegal)" strokeWidth="1.3" strokeLinecap="round" />
            </svg>
            <p style={{ fontSize: "13px", color: "var(--sev-illegal)", lineHeight: 1.45, margin: 0 }}>
              {error}
            </p>
          </div>
        )}

        {/* ── Actions ─────────────────────────────────────────────────────── */}
        <div style={{ display: "flex", gap: "10px" }}>
          {/* Cancel */}
          <button
            onClick={onClose}
            disabled={busy}
            style={{
              flex: 1,
              borderRadius: "100px",
              border: "1.5px solid rgba(107,107,99,0.20)",
              background: "rgba(255,255,255,0.55)",
              color: "var(--ink-subtle)",
              fontSize: "14px",
              fontWeight: 500,
              padding: "11px 0",
              cursor: busy ? "not-allowed" : "pointer",
              opacity: busy ? 0.5 : 1,
              transition: "background 0.15s ease, border-color 0.15s ease, color 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (!busy) {
                const el = e.currentTarget as HTMLElement;
                el.style.background = "rgba(255,255,255,0.85)";
                el.style.color = "var(--ink)";
              }
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget as HTMLElement;
              el.style.background = "rgba(255,255,255,0.55)";
              el.style.color = "var(--ink-subtle)";
            }}
          >
            Cancel
          </button>

          {/* Generate */}
          <button
            onClick={generate}
            disabled={busy}
            style={{
              flex: 2,
              borderRadius: "100px",
              border: "none",
              background: busy
                ? "var(--accent-deep)"
                : "var(--accent)",
              color: "#fff",
              fontSize: "14px",
              fontWeight: 600,
              padding: "11px 0",
              cursor: busy ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              boxShadow: busy
                ? "none"
                : [
                    "0 2px 10px rgba(217,119,87,0.32)",
                    "0 6px 24px rgba(217,119,87,0.18)",
                    "0 1px 0 rgba(255,255,255,0.18) inset",
                  ].join(", "),
              transition: "background 0.16s ease, box-shadow 0.16s ease, transform 0.16s cubic-bezier(.34,1.56,.64,1)",
            }}
            onMouseEnter={(e) => {
              if (!busy) {
                const el = e.currentTarget as HTMLElement;
                el.style.background = "var(--accent-deep)";
                el.style.transform = "translateY(-1px)";
                el.style.boxShadow = [
                  "0 4px 16px rgba(217,119,87,0.38)",
                  "0 10px 32px rgba(217,119,87,0.20)",
                  "0 1px 0 rgba(255,255,255,0.18) inset",
                ].join(", ");
              }
            }}
            onMouseLeave={(e) => {
              if (!busy) {
                const el = e.currentTarget as HTMLElement;
                el.style.background = "var(--accent)";
                el.style.transform = "";
                el.style.boxShadow = [
                  "0 2px 10px rgba(217,119,87,0.32)",
                  "0 6px 24px rgba(217,119,87,0.18)",
                  "0 1px 0 rgba(255,255,255,0.18) inset",
                ].join(", ");
              }
            }}
          >
            {busy ? (
              <>
                <Spinner />
                <span style={{
                  background: "linear-gradient(90deg, rgba(255,255,255,0.65) 0%, #fff 40%, rgba(255,255,255,0.65) 100%)",
                  backgroundSize: "300% auto",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                  animation: "dlShimmer 1.8s linear infinite",
                }}>
                  Generating PDF…
                </span>
              </>
            ) : (
              <>
                {/* Download arrow icon */}
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
                  <path d="M7 2v7M7 9l-2.5-2.5M7 9l2.5-2.5" stroke="white" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2 12h10" stroke="white" strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
                </svg>
                Download PDF
              </>
            )}
          </button>
        </div>

        {/* Fine print */}
        <p style={{
          marginTop: "14px",
          textAlign: "center",
          fontSize: "11px",
          color: "var(--ink-subtle)",
          letterSpacing: "0.01em",
        }}>
          Generated from your uploaded lease analysis
        </p>
      </div>
    </div>
  );
}
