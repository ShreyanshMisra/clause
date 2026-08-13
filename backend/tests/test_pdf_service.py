from pathlib import Path
from app.pdf_service import extract_pages, search_rects

FIX = Path(__file__).parent / "fixtures" / "sample-lease.pdf"

def test_extract_pages_returns_text_and_dims():
    pages = extract_pages(str(FIX))
    assert len(pages) >= 1
    assert pages[0].width > 0 and pages[0].height > 0
    assert isinstance(pages[0].text, str) and len(pages[0].text) > 0

def test_search_rects_finds_known_word():
    pages = extract_pages(str(FIX))
    word = pages[0].text.split()[0]
    rects = search_rects(str(FIX), 1, word)
    assert len(rects) >= 1
    r = rects[0]
    assert r.x2 > r.x1 and r.y2 > r.y1 and r.pageNumber == 1
