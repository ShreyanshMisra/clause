from app.models import Finding, HighlightPosition, BoundingRect, Severity, COLOR_BY_SEVERITY
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
        # Bound the whole match, not just its first line: a multi-line quote spans
        # several rects, so the box must be their union. width/height stay the page
        # dimensions (the reference frame the frontend scales against).
        bounding = BoundingRect(
            x1=min(r.x1 for r in rects), y1=min(r.y1 for r in rects),
            x2=max(r.x2 for r in rects), y2=max(r.y2 for r in rects),
            width=rects[0].width, height=rects[0].height,
            pageNumber=rects[0].pageNumber,
        )
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
    )
