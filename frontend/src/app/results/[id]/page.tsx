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

export default function Results() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<AnalysisResult | null>(null);
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

        <button
          className="ml-auto rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--accent-deep)] hover:shadow-md active:scale-95"
          onClick={() => setLetterOpen(true)}
        >
          Generate demand letter
        </button>
      </header>

      {/* Split view */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
        {/* Left: PDF with overlaid highlights */}
        <PdfHighlights
          url={api.pdfUrl(id)}
          findings={data.highlights}
          scrollTarget={scrollTarget}
          activeId={activeId}
          onHighlightClick={focusFromHighlight}
        />

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

      {letterOpen && <DemandLetterModal fileId={id} onClose={() => setLetterOpen(false)} />}
    </main>
  );
}
