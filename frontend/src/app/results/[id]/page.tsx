"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { api, AnalysisResult } from "@/lib/api";
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
  const [scrollToId, setScrollToId] = useState<string | null>(null);
  // Placeholder state for demand-letter modal (wired in the next task)
  const [letterOpen, setLetterOpen] = useState(false);

  useEffect(() => {
    if (!id) return;
    api.document(id).then(setData).catch((e) => {
      console.error(e);
      setError("Could not load analysis. Is the backend running?");
    });
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
          scrollToId={scrollToId}
        />

        {/* Right: clause cards */}
        <div className="flex flex-col gap-3 overflow-y-auto" style={{ maxHeight: "82vh" }}>
          {data.highlights.length === 0 ? (
            <p className="text-center text-[var(--ink-muted)] mt-10">
              No clauses flagged.
            </p>
          ) : (
            data.highlights.map((f) => (
              <ClauseCard
                key={f.id}
                f={f}
                onClick={() => setScrollToId(f.id)}
              />
            ))
          )}
        </div>
      </div>

      {letterOpen && <DemandLetterModal fileId={id} onClose={() => setLetterOpen(false)} />}
    </main>
  );
}
