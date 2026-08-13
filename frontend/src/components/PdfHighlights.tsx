"use client";

import React, { useRef, useEffect, useCallback } from "react";
import {
  PdfLoader,
  PdfHighlighter,
  AreaHighlight,
} from "react-pdf-highlighter";
import type { IHighlight, ScaledPosition, Scaled } from "react-pdf-highlighter";
import "react-pdf-highlighter/dist/style.css";

import { Finding } from "@/lib/api";
import { HIGHLIGHT_HEX } from "@/app/theme";

// The worker URL must match the pdfjs-dist version that react-pdf-highlighter
// bundles internally (4.4.168). Using unpkg mirrors the old reference pattern.
const WORKER_SRC =
  "https://unpkg.com/pdfjs-dist@4.4.168/build/pdf.worker.min.mjs";

interface Props {
  url: string;
  findings: Finding[];
  scrollToId: string | null;
}

/** Convert a Finding's raw position into a ScaledPosition for react-pdf-highlighter. */
function toScaled(r: {
  x1: number; y1: number; x2: number; y2: number;
  width: number; height: number; pageNumber: number;
}, page: number): Scaled {
  return {
    x1: r.x1,
    y1: r.y1,
    x2: r.x2,
    y2: r.y2,
    width: r.width,
    height: r.height,
    pageNumber: page,
  };
}

function findingToHighlight(f: Finding): IHighlight | null {
  if (!f.position) return null;
  const page = f.page ?? f.position.boundingRect?.pageNumber ?? 1;
  const boundingRect = toScaled(f.position.boundingRect, page);
  const rects =
    f.position.rects && f.position.rects.length > 0
      ? f.position.rects.map((r) => toScaled(r, page))
      : [boundingRect];

  const scaledPos: ScaledPosition = {
    pageNumber: page,
    boundingRect,
    rects,
    usePdfCoordinates: true,
  };

  return {
    id: f.id,
    position: scaledPos,
    content: { text: f.quoted_text },
    comment: { text: f.category, emoji: "" },
  };
}

/** Tint the highlight box by the Finding's color field. */
function getHighlightColor(finding: Finding | undefined): string {
  if (!finding) return "rgba(255, 226, 104, 0.35)";
  const hex = HIGHLIGHT_HEX[finding.color];
  if (!hex) return "rgba(255, 226, 104, 0.35)";
  // Convert hex to rgba with 0.35 opacity
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, 0.35)`;
}

export function PdfHighlights({ url, findings, scrollToId }: Props) {
  const scrollToRef = useRef<((h: IHighlight) => void) | null>(null);
  const highlights: IHighlight[] = findings
    .map(findingToHighlight)
    .filter((h): h is IHighlight => h !== null);

  const findingMap = new Map(findings.map((f) => [f.id, f]));

  // Scroll to the matching highlight whenever scrollToId changes
  useEffect(() => {
    if (!scrollToId || !scrollToRef.current) return;
    const h = highlights.find((x) => x.id === scrollToId);
    if (h) scrollToRef.current(h);
  }, [scrollToId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleScrollRef = useCallback((scrollTo: (h: IHighlight) => void) => {
    scrollToRef.current = scrollTo;
  }, []);

  return (
    <div className="relative rounded-2xl overflow-hidden shadow-md bg-[var(--surface)]"
      style={{ height: "82vh" }}>
      <PdfLoader
        url={url}
        workerSrc={WORKER_SRC}
        beforeLoad={
          <div className="flex h-full items-center justify-center text-[var(--ink-muted)]">
            Loading PDF…
          </div>
        }
        errorMessage={
          <div className="flex h-full items-center justify-center text-red-500 p-6 text-center">
            Failed to load PDF. Check that the backend is reachable and the file exists.
          </div>
        }
      >
        {(pdfDocument) => (
          <PdfHighlighter
            pdfDocument={pdfDocument}
            enableAreaSelection={() => false}
            onScrollChange={() => {}}
            scrollRef={handleScrollRef}
            onSelectionFinished={() => null}
            highlights={highlights}
            highlightTransform={(highlight, _index, setTip, hideTip, _vtS, _ss, isScrolledTo) => {
              const original = findingMap.get(highlight.id);
              const color = getHighlightColor(original);
              // AreaHighlight accepts ...otherProps spread to the underlying Rnd component;
              // we cast to any because the TS type doesn't declare style/onClick/onMouseLeave.
              const areaProps = {
                key: highlight.id,
                highlight,
                isScrolledTo,
                onChange: () => {},
                style: { backgroundColor: color },
                onClick: (e: React.MouseEvent) => {
                  e.stopPropagation();
                  if (original) {
                    setTip(highlight, () => (
                      <div className="max-w-xs rounded-xl bg-white p-4 shadow-xl text-sm">
                        <p className="font-semibold text-[var(--ink)] mb-1">{original.category}</p>
                        <p className="text-[var(--ink-muted)] line-clamp-3">{original.explanation}</p>
                        {original.statute_citation && (
                          <p className="mt-2 text-xs text-[var(--accent-deep)]">{original.statute_citation}</p>
                        )}
                      </div>
                    ));
                  }
                },
                onMouseLeave: hideTip,
              } as any;

              return <AreaHighlight {...areaProps} />;
            }}
          />
        )}
      </PdfLoader>
    </div>
  );
}
