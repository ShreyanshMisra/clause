"use client";

import React, { useRef, useEffect, useCallback } from "react";
import {
  PdfLoader,
  PdfHighlighter,
  AreaHighlight,
  Popup,
} from "react-pdf-highlighter";
import type { IHighlight, ScaledPosition, Scaled } from "react-pdf-highlighter";
import "react-pdf-highlighter/dist/style.css";

import { Finding } from "@/lib/api";
import { HIGHLIGHT_HEX, SEVERITY_COLORS } from "@/app/theme";

// The worker must match the pdfjs-dist version react-pdf-highlighter bundles (4.4.168);
// self-hosted from /public.
const WORKER_SRC = "/pdf.worker.min.mjs";

export interface ScrollTarget {
  id: string;
  nonce: number;
}

interface Props {
  url: string;
  findings: Finding[];
  scrollTarget: ScrollTarget | null;
  activeId: string | null;
  onHighlightClick: (id: string) => void;
}

/** Small card shown on hover over a highlight. */
function HoverCard({ finding }: { finding: Finding | undefined }) {
  if (!finding) return null;
  return (
    <div className="max-w-xs rounded-xl bg-white p-4 shadow-xl border border-black/5">
      <div className="flex items-center gap-2 mb-1">
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: SEVERITY_COLORS[finding.severity] }} />
        <p className="font-semibold text-[var(--ink)] text-sm">{finding.category}</p>
        <span className="ml-auto text-[10px] uppercase tracking-wide text-[var(--ink-subtle)]">
          {finding.severity}
        </span>
      </div>
      <p className="text-xs text-[var(--ink-muted)] leading-relaxed line-clamp-4">{finding.explanation}</p>
      {finding.statute_citation && (
        <p className="mt-2 text-[11px] text-[var(--accent-deep)] font-medium">{finding.statute_citation}</p>
      )}
      <p className="mt-2 text-[10px] text-[var(--ink-subtle)]">Click to view the clause →</p>
    </div>
  );
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
    // Coordinates come from PyMuPDF, whose origin is top-left (y grows downward)
    // and are page-relative (width/height = page size). That is exactly the
    // proportional model react-pdf-highlighter uses when usePdfCoordinates is
    // false. Setting it true would route through pdfjs convertToViewportRectangle,
    // which expects PDF-native bottom-left coordinates and flips every box vertically.
    usePdfCoordinates: false,
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

export function PdfHighlights({ url, findings, scrollTarget, activeId, onHighlightClick }: Props) {
  const scrollToRef = useRef<((h: IHighlight) => void) | null>(null);
  const highlights: IHighlight[] = findings
    .map(findingToHighlight)
    .filter((h): h is IHighlight => h !== null);

  const findingMap = new Map(findings.map((f) => [f.id, f]));

  // Scroll to the matching highlight whenever a scroll is requested (nonce changes even
  // if the same card is clicked twice).
  useEffect(() => {
    if (!scrollTarget || !scrollToRef.current) return;
    const h = highlights.find((x) => x.id === scrollTarget.id);
    if (h) scrollToRef.current(h);
  }, [scrollTarget?.nonce]); // eslint-disable-line react-hooks/exhaustive-deps

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
            highlightTransform={(highlight, index, setTip, hideTip, _vtS, _ss, isScrolledTo) => {
              const original = findingMap.get(highlight.id);
              const isActive = highlight.id === activeId;
              const color = getHighlightColor(original);
              // AreaHighlight spreads extra props to its Rnd; cast to any because the TS
              // type doesn't declare style/onClick.
              const areaProps = {
                highlight,
                isScrolledTo,
                onChange: () => {},
                style: {
                  backgroundColor: color,
                  cursor: "pointer",
                  transition: "outline 0.15s ease, background-color 0.15s ease",
                  outline: isActive ? `2px solid ${original ? HIGHLIGHT_HEX[original.color] : "#D97757"}` : "none",
                  outlineOffset: "1px",
                },
                onClick: () => onHighlightClick(highlight.id),
              } as unknown as React.ComponentProps<typeof AreaHighlight>;

              // Popup shows the hover card via setTip/hideTip on mouse over/out.
              return (
                <Popup
                  key={index}
                  popupContent={<HoverCard finding={original} />}
                  onMouseOver={(popupContent) => setTip(highlight, () => popupContent)}
                  onMouseOut={hideTip}
                >
                  <AreaHighlight {...areaProps} />
                </Popup>
              );
            }}
          />
        )}
      </PdfLoader>
    </div>
  );
}
