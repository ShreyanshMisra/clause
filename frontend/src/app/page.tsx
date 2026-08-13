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

/* ─── Page ───────────────────────────────────────────────────────────────── */
export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center px-6 py-20">

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <div className="mb-10 flex flex-col items-center text-center">
        {/* Wordmark pill */}
        <div
          className="mb-6 inline-flex items-center gap-2 rounded-full px-4 py-1.5"
          style={{
            background: "rgba(217,119,87,0.10)",
            border: "1px solid rgba(217,119,87,0.22)",
          }}
        >
          {/* Shield icon */}
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path
              d="M7 1L2 3.5v4c0 2.5 2.2 4.7 5 5 2.8-.3 5-2.5 5-5v-4L7 1z"
              fill="var(--accent)"
              opacity="0.85"
            />
          </svg>
          <span
            className="text-xs font-semibold tracking-widest uppercase"
            style={{ color: "var(--accent-deep)" }}
          >
            Clause
          </span>
        </div>

        <h1
          className="mb-3 text-5xl font-semibold tracking-tight"
          style={{ color: "var(--ink)", letterSpacing: "-0.03em", lineHeight: 1.1 }}
        >
          Know what you&rsquo;re<br />
          <span style={{ color: "var(--accent)" }}>signing.</span>
        </h1>

        <p
          className="max-w-sm text-base leading-relaxed"
          style={{ color: "var(--ink-muted)" }}
        >
          Spot illegal and risky clauses in your rental agreement — in seconds,
          not hours.
        </p>
      </div>

      {/* ── Upload card ────────────────────────────────────────────────── */}
      <div className="w-full">
        <UploadCard />
      </div>

      {/* ── PII trust note ─────────────────────────────────────────────── */}
      <div
        className="mt-5 flex items-center gap-2"
        style={{ color: "var(--ink-subtle)" }}
      >
        <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden>
          <path
            d="M6.5 1L1.5 3.25v3.5c0 2.6 2 4.7 5 5 3-0.3 5-2.4 5-5v-3.5L6.5 1z"
            stroke="var(--sev-favorable)"
            strokeWidth="1.3"
            strokeLinejoin="round"
          />
          <path
            d="M4.5 6.5l1.5 1.5 2.5-2.5"
            stroke="var(--sev-favorable)"
            strokeWidth="1.3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="text-xs" style={{ color: "var(--ink-subtle)" }}>
          Personal information is redacted before analysis — never stored.
        </span>
      </div>

      {/* ── How it works ───────────────────────────────────────────────── */}
      <div className="mt-14 w-full">
        <p
          className="mb-6 text-center text-xs font-semibold uppercase tracking-widest"
          style={{ color: "var(--ink-subtle)" }}
        >
          How it works
        </p>
        <div className="grid grid-cols-3 gap-4">
          {STEPS.map((step) => (
            <div
              key={step.n}
              className="flex flex-col gap-3 rounded-2xl p-5"
              style={{
                background: "rgba(240,238,230,0.55)",
                border: "1px solid rgba(107,107,99,0.12)",
              }}
            >
              <div className="flex items-center gap-2">
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-xl"
                  style={{ background: "rgba(217,119,87,0.10)" }}
                >
                  {step.icon}
                </div>
                <span
                  className="text-[10px] font-bold tracking-widest"
                  style={{ color: "var(--ink-subtle)", opacity: 0.6 }}
                >
                  {step.n}
                </span>
              </div>
              <p
                className="text-sm font-semibold"
                style={{ color: "var(--ink)", letterSpacing: "-0.01em" }}
              >
                {step.label}
              </p>
              <p
                className="text-xs leading-relaxed"
                style={{ color: "var(--ink-muted)" }}
              >
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
