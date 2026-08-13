from app.models import AnalysisResult, AnalysisSummary, TopIssue, Severity
from app.highlight import build_highlight
from app.jobs import JobRegistry
from app.llm_service import LLMService
from app.vector_store import VectorStore

_RISK_ORDER = {Severity.illegal: 3, Severity.high: 2, Severity.medium: 1, Severity.favorable: 0}
_RISK_LABEL = {3: "Critical", 2: "High", 1: "Medium", 0: "Low"}

def _chunk(text: str, size: int = 3000) -> list[str]:
    return [text[i:i + size] for i in range(0, max(len(text), 1), size)] or [""]

def analyze_document(file_id: str, pdf_path: str, redacted_text: str,
                     llm: LLMService, store: VectorStore, registry: JobRegistry,
                     top_k: int = 4) -> AnalysisResult:
    registry.update(file_id, status="processing", progress=20, message="Loading document...")
    chunks = _chunk(redacted_text)
    drafts = []
    for idx, chunk in enumerate(chunks):
        progress = 20 + int(60 * (idx + 1) / len(chunks))
        registry.update(file_id, progress=progress, message=f"Analyzing chunk {idx+1}/{len(chunks)}...")
        statutes = store.search(llm.embed(chunk), k=top_k)
        drafts.extend(llm.analyze_chunk(chunk, statutes, page_hint=1))

    registry.update(file_id, progress=90, message="Extracting highlight positions...")
    highlights = [build_highlight(d, pdf_path, i) for i, d in enumerate(drafts)]

    max_sev = max((_RISK_ORDER[h.severity] for h in highlights), default=0)
    total_damages = sum(h.damages_estimate or 0 for h in highlights)
    top = sorted(highlights, key=lambda h: _RISK_ORDER[h.severity], reverse=True)[:3]
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
