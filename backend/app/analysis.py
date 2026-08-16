import os
from app.models import AnalysisResult, AnalysisSummary, TopIssue, Severity
from app.highlight import build_highlight
from app.jobs import JobRegistry
from app.llm_service import LLMService
from app.vector_store import VectorStore

_RISK_ORDER = {Severity.illegal: 3, Severity.high: 2, Severity.medium: 1, Severity.favorable: 0}
_RISK_LABEL = {3: "Critical", 2: "High", 1: "Medium", 0: "Low"}

# Pages analyzed per LLM call. Grouping cuts request count (e.g. 16 pages / 4 = 4 calls
# instead of 8) which also cuts the number of embed round-trips — the main cost in
# Cortex mode — so larger groups analyze faster. Page markers keep highlights accurate.
# Tunable via ANALYSIS_PAGE_GROUP (4-6 is a good range); higher trades retrieval
# precision (one embedding per group) for speed.
_PAGE_GROUP = max(1, int(os.environ.get("ANALYSIS_PAGE_GROUP", "4")))

def analyze_document(file_id: str, pdf_path: str, redacted_pages: list[str],
                     llm: LLMService, embedder, store: VectorStore, registry: JobRegistry,
                     top_k: int = 6) -> AnalysisResult:
    try:
        registry.update(file_id, status="processing", progress=20, message="Loading document...")
        pages = redacted_pages or [""]
        groups = [pages[i:i + _PAGE_GROUP] for i in range(0, len(pages), _PAGE_GROUP)]
        drafts = []
        errors = 0
        last_error = None
        for gi, group in enumerate(groups):
            base = gi * _PAGE_GROUP
            first, last = base + 1, base + len(group)
            progress = 20 + int(60 * (gi + 1) / len(groups))
            registry.update(file_id, progress=progress,
                            message=f"Analyzing pages {first}-{last} of {len(pages)}...")
            # Concatenate the group's pages with page markers so the LLM can attribute
            # each finding to the correct page (keeps highlight coordinates accurate).
            marked = "\n\n".join(f"=== PAGE {base + j + 1} ===\n{txt}"
                                 for j, txt in enumerate(group) if txt.strip())
            if not marked.strip():
                continue
            # Resilience: a transient per-chunk failure (timeout/rate-limit) skips that
            # chunk instead of failing the whole document — partial results beat none.
            try:
                # Scale retrieval with the group size: one embedding now represents
                # several pages, so pull more statute candidates to keep recall up.
                k = max(top_k, 2 * len(group))
                statutes = store.search(embedder.embed(marked), k=k)
                drafts.extend(llm.analyze_chunk(marked, statutes, page_hint=first))
            except Exception as e:  # noqa: BLE001
                errors += 1
                last_error = e
                continue

        # Only hard-fail if every chunk errored (e.g. quota exhausted / bad key).
        if not drafts and errors and last_error is not None:
            raise last_error

        registry.update(file_id, progress=90, message="Extracting highlight positions...")
        highlights = [build_highlight(d, pdf_path, i) for i, d in enumerate(drafts)]

        max_sev = max((_RISK_ORDER[h.severity] for h in highlights), default=0)
        total_damages = sum(h.damages_estimate or 0 for h in highlights)
        top = sorted([h for h in highlights if h.severity != Severity.favorable],
                     key=lambda h: _RISK_ORDER[h.severity], reverse=True)[:3]
        summary = AnalysisSummary(
            overallRisk=_RISK_LABEL[max_sev],
            issuesFound=len([h for h in highlights if h.severity != Severity.favorable]),
            estimatedRecovery=f"${total_damages:,.0f}",
            topIssues=[TopIssue(title=h.category, severity=h.severity.value,
                                amount=(f"${h.damages_estimate:,.0f}" if h.damages_estimate else None))
                       for h in top],
        )
        result = AnalysisResult(documentId=file_id, analysisSummary=summary, highlights=highlights)
        registry.update(file_id, status="completed", progress=100, message="Analysis complete")
        return result
    except Exception as e:
        registry.update(file_id, status="failed", progress=0, message=f"Analysis failed: {e}")
        raise
