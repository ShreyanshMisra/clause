from app.models import Finding, HighlightPosition, Severity, COLOR_BY_SEVERITY
from app.llm_service import FindingDraft
from app.pdf_service import search_rects

def color_for(severity: str) -> str:
    try:
        return COLOR_BY_SEVERITY[Severity(severity)]
    except ValueError:
        return "yellow"

def build_highlight(draft: FindingDraft, pdf_path: str, index: int) -> Finding:
    rects = search_rects(pdf_path, draft.page, draft.quoted_text) if draft.quoted_text else []
    position = None
    if rects:
        bounding = rects[0]
        position = HighlightPosition(
            boundingRect=bounding, rects=rects,
            pageWidth=bounding.width, pageHeight=bounding.height,
        )
    return Finding(
        id=f"f{index}",
        page=draft.page,
        quoted_text=draft.quoted_text,
        category=draft.category,
        severity=Severity(draft.severity) if draft.severity in Severity._value2member_map_ else Severity.medium,
        color=color_for(draft.severity),
        statute_citation=draft.statute_citation,
        explanation=draft.explanation,
        damages_estimate=draft.damages_estimate,
        position=position,
        legal_reasoning=draft.legal_reasoning,
        severity_rationale=draft.severity_rationale,
        recommended_action=draft.recommended_action,
        confidence=draft.confidence,
        statute_quote=draft.statute_quote,
        damages_basis=draft.damages_basis,
    )
