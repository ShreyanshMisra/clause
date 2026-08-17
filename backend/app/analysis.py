import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from app.models import AnalysisResult, AnalysisSummary, TopIssue, Severity, Metadata
from app.highlight import build_highlight
from app.jobs import JobRegistry
from app.llm_service import LLMService
from app.remedy import compute_damages, money
from app.vector_store import VectorStore

_RISK_ORDER = {Severity.illegal: 3, Severity.high: 2, Severity.medium: 1, Severity.favorable: 0}
_RISK_LABEL = {3: "Critical", 2: "High", 1: "Medium", 0: "Low"}

# Pages analyzed per LLM call. Grouping cuts request count (e.g. 16 pages / 4 = 4 calls
# instead of 16) to stay under free-tier daily quotas; page markers keep highlights accurate.
_PAGE_GROUP = max(1, int(os.environ.get("ANALYSIS_PAGE_GROUP", "2")))
# Chunks are independent, so analyze them concurrently to cut wall-clock latency on
# multi-page documents (bounded so we don't hammer the model's rate limits).
_CONCURRENCY = max(1, int(os.environ.get("ANALYSIS_CONCURRENCY", "4")))

def _apply_statutory_damages(drafts, metadata: Optional[Metadata]) -> None:
    """Override the model's damages estimate with a code-computed statutory figure
    wherever MA law fixes the remedy, using amounts from the document metadata."""
    if metadata is None:
        return
    inputs = {"security_deposit": money(metadata.securityDeposit),
              "monthly_rent": money(metadata.monthlyRent)}
    for d in drafts:
        remedy = compute_damages(d.statute_id, inputs)
        if remedy.amount is not None:
            d.damages_estimate = remedy.amount
            d.damages_basis = remedy.basis


def analyze_document(file_id: str, pdf_path: str, redacted_pages: list[str],
                     llm: LLMService, embedder, store: VectorStore, registry: JobRegistry,
                     top_k: int = 6, metadata: Optional[Metadata] = None) -> AnalysisResult:
    try:
        registry.update(file_id, status="processing", progress=20, message="Loading document...")
        pages = redacted_pages or [""]
        groups = [pages[i:i + _PAGE_GROUP] for i in range(0, len(pages), _PAGE_GROUP)]

        # Build the non-empty chunks up front (each tagged with its group index so
        # results can be reassembled in document order after concurrent execution).
        chunks = []
        for gi, group in enumerate(groups):
            base = gi * _PAGE_GROUP
            marked = "\n\n".join(f"=== PAGE {base + j + 1} ===\n{txt}"
                                 for j, txt in enumerate(group) if txt.strip())
            if marked.strip():
                chunks.append((gi, base + 1, marked))

        retrieve_k = max(top_k, int(os.environ.get("ANALYSIS_RETRIEVE_K", top_k * 3)))
        done = 0
        lock = threading.Lock()

        def analyze_one(item):
            """Retrieve statutes for one chunk and analyze it. Returns (gi, drafts, error);
            a per-chunk failure is captured, not raised, so one bad chunk can't sink the
            whole document."""
            nonlocal done
            gi, first, marked = item
            result: tuple[int, list, Optional[Exception]]
            try:
                candidates = store.search(embedder.embed(marked), k=retrieve_k, query_text=marked)
                result = (gi, llm.analyze_chunk(marked, candidates[:top_k], page_hint=first), None)
            except Exception as e:  # noqa: BLE001
                result = (gi, [], e)
            with lock:
                done += 1
                registry.update(file_id, progress=20 + int(60 * done / max(1, len(chunks))),
                                message=f"Analyzing… ({done}/{len(chunks)})")
            return result

        results = []
        if chunks:
            with ThreadPoolExecutor(max_workers=min(_CONCURRENCY, len(chunks))) as pool:
                results = list(pool.map(analyze_one, chunks))

        errors = [r[2] for r in results if r[2] is not None]
        # Reassemble drafts in document order for deterministic output.
        drafts = [d for gi, ds, _ in sorted(results, key=lambda r: r[0]) for d in ds]

        # Only hard-fail if there were chunks and every one errored (e.g. quota/bad key).
        if not drafts and errors and len(errors) == len(chunks):
            raise errors[-1]

        # Replace model-guessed damages with statutory figures where the law is fixed.
        _apply_statutory_damages(drafts, metadata)

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
