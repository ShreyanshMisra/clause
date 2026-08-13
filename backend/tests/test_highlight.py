from app.highlight import build_highlight, color_for
from app.llm_service import FindingDraft
from app.models import Severity
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

def test_build_highlight_degrades_when_text_absent():
    draft = FindingDraft(quoted_text="zzz_not_in_document_zzz", page=1, category="X",
                         severity="medium", statute_citation=None, explanation="e",
                         damages_estimate=None)
    fh = build_highlight(draft, FIX, index=1)
    assert fh.position is None
