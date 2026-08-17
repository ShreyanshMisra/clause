"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { api, AnalysisResult } from "@/lib/api";
import type { ScrollTarget } from "@/components/PdfHighlights";
import { ClauseCard } from "@/components/ClauseCard";
import { DemandLetterModal } from "@/components/DemandLetterModal";

// PdfHighlights touches the DOM (pdfjs + react-pdf-highlighter); disable SSR.
const PdfHighlights = dynamic(
  () => import("@/components/PdfHighlights").then((m) => ({ default: m.PdfHighlights })),
  { ssr: false, loading: () => <PdfPlaceholder /> }
);

function PdfPlaceholder() {
  return (
    <div
      className="rounded-2xl bg-[var(--surface)] flex items-center justify-center text-[var(--ink-muted)]"
      style={{ height: "82vh" }}
    >
      Loading PDF viewer…
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-[var(--ink-subtle)] mb-0.5">{label}</p>
      <p className="text-2xl font-semibold text-[var(--ink)]">{value}</p>
    </div>
  );
}

function MetaField({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] uppercase tracking-wide text-[var(--ink-subtle)]">{label}</p>
      <p className="truncate text-sm font-medium text-[var(--ink)]" title={value}>{value || "—"}</p>
    </div>
  );
}

function MetaBar({ meta }: { meta: AnalysisResult["documentMetadata"] }) {
  const p = meta?.parties;
  // Only render once the model has filled in at least one field.
  const hasAny = !!(p?.landlord || p?.tenant || p?.property || meta?.monthlyRent ||
    meta?.leaseTerm || meta?.securityDeposit);
  if (!hasAny) return null;
  return (
    <section className="mb-6 grid grid-cols-2 gap-4 rounded-2xl bg-[var(--surface)]/60 p-4 backdrop-blur-sm border border-white/40 sm:grid-cols-3 lg:grid-cols-6">
      <MetaField label="Landlord" value={p?.landlord ?? ""} />
      <MetaField label="Tenant" value={p?.tenant ?? ""} />
      <MetaField label="Property" value={p?.property ?? ""} />
      <MetaField label="Monthly rent" value={meta?.monthlyRent ?? ""} />
      <MetaField label="Lease term" value={meta?.leaseTerm ?? ""} />
      <MetaField label="Security deposit" value={meta?.securityDeposit ?? ""} />
    </section>
  );
}

export default function Results() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [scrollTarget, setScrollTarget] = useState<ScrollTarget | null>(null);
  const [letterOpen, setLetterOpen] = useState(false);
  const nonce = useRef(0);
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  useEffect(() => {
    if (!id) return;
    api.document(id).then(setData).catch((e) => {
      console.error(e);
      setError("Could not load analysis. Is the backend running?");
    });
  }, [id]);

  // Load the owner-scoped PDF as a blob URL (see api.pdfObjectUrl), and revoke
  // it on unmount so we don't leak object URLs.
  useEffect(() => {
    if (!id) return;
    let url: string | null = null;
    api.pdfObjectUrl(id).then((u) => { url = u; setPdfUrl(u); }).catch((e) => console.error(e));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [id]);

  // Clicking a clause card → focus it and snap the PDF to its highlight.
  const focusFromCard = useCallback((fid: string) => {
    setActiveId(fid);
    nonce.current += 1;
    setScrollTarget({ id: fid, nonce: nonce.current });
  }, []);

  // Clicking a highlight → focus it and scroll its clause card into view.
  const focusFromHighlight = useCallback((fid: string) => {
    setActiveId(fid);
    cardRefs.current.get(fid)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, []);

  // Download the analysis itself as a PDF report.
  const downloadReport = useCallback(async () => {
    try {
      const res = await api.report(id);
      if (!res.ok) return;
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "clause-report.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore — download is best-effort */
    }
  }, [id]);

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center p-10">
        <p className="text-red-500 text-center">{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center p-10">
        <div className="text-center">
          <div className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-[var(--accent)] border-r-transparent mb-4" />
          <p className="text-[var(--ink-muted)]">Loading results…</p>
        </div>
      </main>
    );
  }

  const s = data.analysisSummary;

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Back to dashboard */}
      <Link
        href="/dashboard"
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium transition-colors"
        style={{ color: "var(--ink-muted)" }}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Dashboard
      </Link>

      {/* Summary header */}
      <header className="mb-6 flex flex-wrap items-center gap-6 rounded-3xl bg-[var(--surface)]/70 p-6 backdrop-blur-sm border border-white/40 shadow-sm">
        <Stat label="Overall risk" value={s.overallRisk} />
        <div className="h-10 w-px bg-[var(--ink-subtle)]/20 hidden sm:block" />
        <Stat label="Issues found" value={String(s.issuesFound)} />
        <div className="h-10 w-px bg-[var(--ink-subtle)]/20 hidden sm:block" />
        <Stat label="Est. recovery" value={s.estimatedRecovery} />

        <div className="ml-auto flex items-center gap-3">
          <button
            className="rounded-full border border-[var(--ink-subtle)]/30 px-5 py-3 text-sm font-semibold text-[var(--ink-muted)] transition hover:bg-black/5 active:scale-95"
            onClick={downloadReport}
          >
            Download report
          </button>
          <button
            disabled={s.issuesFound === 0}
            title={s.issuesFound === 0 ? "No issues to demand remedy for." : undefined}
            className="rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--accent-deep)] hover:shadow-md active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-[var(--accent)] disabled:hover:shadow-sm disabled:active:scale-100"
            onClick={() => { if (s.issuesFound > 0) setLetterOpen(true); }}
          >
            Generate demand letter
          </button>
        </div>
      </header>

      {/* Document metadata (parties / rent / term / deposit) */}
      <MetaBar meta={data.documentMetadata} />

      {/* Split view */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
        {/* Left: PDF with overlaid highlights */}
        {pdfUrl ? (
          <PdfHighlights
            url={pdfUrl}
            findings={data.highlights}
            scrollTarget={scrollTarget}
            activeId={activeId}
            onHighlightClick={focusFromHighlight}
          />
        ) : (
          <PdfPlaceholder />
        )}

        {/* Right: clause cards */}
        <div className="flex flex-col gap-3 overflow-y-auto pr-1" style={{ maxHeight: "82vh" }}>
          {data.highlights.length === 0 ? (
            <p className="text-center text-[var(--ink-muted)] mt-10">
              No clauses flagged.
            </p>
          ) : (
            data.highlights.map((f) => (
              <div
                key={f.id}
                ref={(el) => {
                  if (el) cardRefs.current.set(f.id, el);
                  else cardRefs.current.delete(f.id);
                }}
              >
                <ClauseCard
                  f={f}
                  active={activeId === f.id}
                  onClick={() => focusFromCard(f.id)}
                />
              </div>
            ))
          )}
        </div>
      </div>

      {letterOpen && (
        <DemandLetterModal fileId={id} meta={data.documentMetadata} onClose={() => setLetterOpen(false)} />
      )}
    </main>
  );
}
