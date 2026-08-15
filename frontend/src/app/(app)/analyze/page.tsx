import { UploadCard } from "@/components/UploadCard";

/* ─── How-it-works step data ─────────────────────────────────────────────── */
const STEPS = [
  {
    n: "01",
    label: "Upload",
    body: "Drop your rental agreement PDF. Personal details are redacted before anything leaves your device.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
        <path d="M10 13V5M10 5l-3.5 3.5M10 5l3.5 3.5" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M3 15h14" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" opacity="0.5" />
      </svg>
    ),
  },
  {
    n: "02",
    label: "Analyse",
    body: "Clause checks every paragraph against tenant-protection statutes and flags risky or illegal language.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
        <circle cx="9" cy="9" r="5.5" stroke="var(--accent)" strokeWidth="1.8" />
        <path d="M13.5 13.5L17 17" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" />
        <path d="M7 9h4M9 7v4" stroke="var(--accent)" strokeWidth="1.6" strokeLinecap="round" opacity="0.6" />
      </svg>
    ),
  },
  {
    n: "03",
    label: "Protect",
    body: "Review highlighted findings, understand your rights, and get an estimated recovery figure.",
    icon: (
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden>
        <path d="M10 3L4 6v5c0 3.3 2.5 6.4 6 7 3.5-.6 6-3.7 6-7V6l-6-3z" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M7.5 10.5l2 2 3-3" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

/* ─── Upload & Analyze tab ───────────────────────────────────────────────── */
export default function AnalyzePage() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col items-center px-6 py-14">

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <div className="mb-10 flex flex-col items-center text-center">
        <h1
          className="enter-1 mb-4"
          style={{
            fontSize: "clamp(2.2rem, 5.5vw, 3rem)",
            fontWeight: 650,
            letterSpacing: "-0.04em",
            lineHeight: 1.05,
            color: "var(--ink)",
          }}
        >
          Know what you&rsquo;re
          <br />
          <span style={{ color: "var(--accent)", position: "relative", display: "inline-block" }}>
            signing.
            <span
              aria-hidden
              style={{
                position: "absolute",
                bottom: "-3px",
                left: 0,
                height: "2.5px",
                borderRadius: "2px",
                background: "linear-gradient(90deg, var(--accent), var(--accent-deep))",
                animation: "underlineGrow 0.7s cubic-bezier(.16,1,.3,1) 0.55s both",
              }}
            />
          </span>
        </h1>
        <p
          className="enter-2 max-w-xs text-base font-medium leading-relaxed"
          style={{ color: "var(--ink-muted)", letterSpacing: "-0.005em" }}
        >
          Spot illegal and risky clauses in your rental agreement&nbsp;—
          in seconds, not hours.
        </p>
      </div>

      {/* ── Upload card ────────────────────────────────────────────────── */}
      <div className="enter-3 w-full">
        <UploadCard />
      </div>

      {/* ── PII trust note ─────────────────────────────────────────────── */}
      <div className="enter-4 mt-5 flex items-center gap-2">
        <span
          aria-hidden
          style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center", width: "10px", height: "10px" }}
        >
          <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "var(--sev-favorable)", animation: "statusPulse 2.4s ease-in-out infinite" }} />
          <span style={{ position: "relative", width: "5px", height: "5px", borderRadius: "50%", background: "var(--sev-favorable)", flexShrink: 0 }} />
        </span>
        <span className="text-xs" style={{ color: "var(--ink-subtle)", letterSpacing: "0.01em" }}>
          Personal information is redacted before analysis.
        </span>
      </div>

      {/* ── How it works ───────────────────────────────────────────────── */}
      <div className="enter-5 mt-14 w-full">
        <p
          className="mb-6 text-center text-[10px] font-bold uppercase tracking-[0.16em]"
          style={{ color: "var(--ink-subtle)", opacity: 0.7 }}
        >
          How it works
        </p>
        <div className="grid grid-cols-3 gap-3">
          {STEPS.map((step) => (
            <div
              key={step.n}
              className="step-card relative flex flex-col gap-3 overflow-hidden rounded-2xl p-5"
              style={{
                background: "rgba(240,238,230,0.5)",
                border: "1px solid rgba(107,107,99,0.11)",
                backdropFilter: "blur(8px)",
                WebkitBackdropFilter: "blur(8px)",
              }}
            >
              <span
                aria-hidden
                style={{ position: "absolute", top: "-8px", right: "8px", fontSize: "64px", fontWeight: 800, letterSpacing: "-0.04em", color: "var(--ink)", opacity: 0.04, lineHeight: 1, userSelect: "none", pointerEvents: "none" }}
              >
                {step.n}
              </span>
              <div
                className="flex h-8 w-8 items-center justify-center rounded-xl"
                style={{ background: "rgba(217,119,87,0.10)", border: "1px solid rgba(217,119,87,0.14)" }}
              >
                {step.icon}
              </div>
              <p className="text-sm font-semibold" style={{ color: "var(--ink)", letterSpacing: "-0.02em" }}>
                {step.label}
              </p>
              <p className="text-[11px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
