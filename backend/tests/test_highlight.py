from app.highlight import build_highlight, color_for
from app.llm_service import FindingDraft
from pathlib import Path

FIX = str(Path(__file__).parent / "fixtures" / "sample-lease.pdf")

def test_color_for_maps_severity():
    assert color_for("illegal") == "red"
    assert color_for("favorable") == "green"

def test_build_highlight_resolves_position_for_present_text():
    from app.pdf_service import extract_pages
    word = extract_pages(FIX)[0].text.split()[0]
    draft = FindingDraft(quoted_text=word, page=1, category="X", severity="high",
                         statute_citation="c.186", explanation="e", damages_estimate=None)
    fh = build_highlight(draft, FIX, index=0)
    assert fh.color == "orange"
    assert fh.position is not None
    assert len(fh.position.rects) >= 1

def test_union_rect_encloses_all_rects():
    from app.models import BoundingRect
    from app.highlight import union_rect
    rects = [
        BoundingRect(x1=10, y1=20, x2=100, y2=30, width=612, height=792, pageNumber=1),
        BoundingRect(x1=5, y1=32, x2=80, y2=44, width=612, height=792, pageNumber=1),
    ]
    u = union_rect(rects)
    assert (u.x1, u.y1, u.x2, u.y2) == (5, 20, 100, 44)  # encloses both lines
    assert (u.width, u.height) == (612, 792)             # page dims preserved


def test_build_highlight_degrades_when_text_absent():
    draft = FindingDraft(quoted_text="zzz_not_in_document_zzz", page=1, category="X",
                         severity="medium", statute_citation=None, explanation="e",
                         damages_estimate=None)
    fh = build_highlight(draft, FIX, index=1)
    assert fh.position is None
