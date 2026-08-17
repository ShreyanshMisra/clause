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

def test_search_rects_fuzzy_matches_paraphrase():
    # Take a real run of words and corrupt it (drop a word, mangle whitespace) so the
    # exact/anchor searches miss and only the fuzzy word-run fallback can locate it.
    words = extract_pages(str(FIX))[0].text.split()
    assert len(words) >= 8
    phrase = " ".join(words[1:8])
    corrupted = "  ".join([words[1], words[2], "zznotaword", *words[4:8]])
    exact = search_rects(str(FIX), 1, phrase)
    fuzzy = search_rects(str(FIX), 1, corrupted)
    assert len(exact) >= 1
    assert len(fuzzy) >= 1  # fuzzy fallback still locates the region
    assert fuzzy[0].x2 > fuzzy[0].x1 and fuzzy[0].y2 > fuzzy[0].y1
