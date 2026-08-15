"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, CaseSummary } from "@/lib/api";

const RISK_COLOR: Record<string, string> = {
  High: "var(--sev-illegal)",
  Medium: "var(--sev-high)",
  Low: "var(--sev-favorable)",
};

function timeAgo(seconds: number): string {
  const diff = Date.now() / 1000 - seconds;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function CaseCard({ c, i }: { c: CaseSummary; i: number }) {
  const risk = c.overall_risk ?? "—";
  const color = RISK_COLOR[risk] ?? "var(--ink-subtle)";
  const done = c.status === "completed";
  const href = done ? `/results/${c.id}` : `/processing?file_id=${c.id}`;

  return (
    <Link
      href={href}
      className="group relative flex flex-col gap-4 overflow-hidden rounded-2xl p-5 transition-all"
      style={{
        background: "rgba(250,249,245,0.7)",
        border: "1px solid rgba(107,107,99,0.12)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        boxShadow: "0 2px 8px rgba(20,20,19,0.04)",
        animation: `slideUp 0.5s cubic-bezier(.16,1,.3,1) ${i * 60}ms both`,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = "0 12px 32px rgba(20,20,19,0.10)"; }}
      onMouseLeave={(e) => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "0 2px 8px rgba(20,20,19,0.04)"; }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
            style={{ background: "rgba(217,119,87,0.10)", border: "1px solid rgba(217,119,87,0.16)" }}
          >
            <svg width="18" height="20" viewBox="0 0 18 20" fill="none" aria-hidden>
              <path d="M3 1h8l4 4v13a1 1 0 01-1 1H3a1 1 0 01-1-1V2a1 1 0 011-1z" stroke="var(--accent)" strokeWidth="1.5" />
              <path d="M11 1v4h4" stroke="var(--accent)" strokeWidth="1.5" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold" style={{ color: "var(--ink)", maxWidth: "180px" }}>
              {c.filename || "Lease.pdf"}
            </p>
            <p className="text-xs" style={{ color: "var(--ink-subtle)" }}>{timeAgo(c.created_at)}</p>
          </div>
        </div>
        {done ? (
          <span
            className="rounded-full px-2.5 py-1 text-[11px] font-semibold"
            style={{ background: `color-mix(in srgb, ${color} 12%, transparent)`, color }}
          >
            {risk} risk
          </span>
        ) : (
          <span
            className="rounded-full px-2.5 py-1 text-[11px] font-semibold"
            style={{ background: "rgba(217,119,87,0.10)", color: "var(--accent-deep)" }}
          >
            {c.status === "failed" ? "Failed" : "Analysing…"}
          </span>
        )}
      </div>

      {done && (
        <div className="flex items-center gap-5">
          <div>
            <p className="text-[10px] uppercase tracking-wide" style={{ color: "var(--ink-subtle)" }}>Issues</p>
            <p className="text-lg font-semibold" style={{ color: "var(--ink)" }}>{c.issues_found ?? 0}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wide" style={{ color: "var(--ink-subtle)" }}>Est. recovery</p>
            <p className="text-lg font-semibold" style={{ color: "var(--accent-deep)" }}>{c.estimated_recovery ?? "$0"}</p>
          </div>
        </div>
      )}
    </Link>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listCases().then(setCases).catch((e) => setError((e as Error).message));
  }, []);

  return (
    <main className="mx-auto w-full max-w-5xl px-6 py-12">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 style={{ fontSize: "1.9rem", fontWeight: 650, letterSpacing: "-0.03em", color: "var(--ink)" }}>
            Your cases
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
            Every lease you&rsquo;ve analysed, with its findings.
          </p>
        </div>
        <button
          type="button"
          onClick={() => router.push("/analyze")}
          className="rounded-full px-5 py-2.5 text-sm font-medium"
          style={{
            background: "var(--accent)", color: "#fff", border: "none", cursor: "pointer",
            boxShadow: "0 2px 10px rgba(217,119,87,0.28)",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "var(--accent-deep)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "var(--accent)"; }}
        >
          + New analysis
        </button>
      </div>

      {error && (
        <p className="text-sm" style={{ color: "var(--sev-illegal)" }}>{error}</p>
      )}

      {cases === null && !error && (
        <p className="text-sm" style={{ color: "var(--ink-subtle)" }}>Loading your cases…</p>
      )}

      {cases !== null && cases.length === 0 && (
        <div
          className="flex flex-col items-center gap-4 rounded-2xl py-16 text-center"
          style={{ background: "rgba(240,238,230,0.5)", border: "1px dashed rgba(107,107,99,0.2)" }}
        >
          <div
            className="flex h-14 w-14 items-center justify-center rounded-2xl"
            style={{ background: "rgba(217,119,87,0.10)", border: "1px solid rgba(217,119,87,0.16)" }}
          >
            <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden>
              <path d="M13 18V8M13 8l-4 4M13 8l4 4" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <p className="text-base font-semibold" style={{ color: "var(--ink)" }}>No cases yet</p>
            <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
              Upload your first lease to see it here.
            </p>
          </div>
          <Link
            href="/analyze"
            className="rounded-full px-5 py-2.5 text-sm font-medium"
            style={{ background: "var(--accent)", color: "#fff", boxShadow: "0 2px 10px rgba(217,119,87,0.28)" }}
          >
            Upload a lease
          </Link>
        </div>
      )}

      {cases !== null && cases.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cases.map((c, i) => <CaseCard key={c.id} c={c} i={i} />)}
        </div>
      )}
    </main>
  );
}
