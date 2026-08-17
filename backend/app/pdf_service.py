import difflib
import fitz  # PyMuPDF
from dataclasses import dataclass
from app.models import BoundingRect

@dataclass
class Page:
    number: int  # 1-based
    text: str
    width: float
    height: float

def extract_pages(pdf_path: str) -> list[Page]:
    doc = fitz.open(pdf_path)
    pages = []
    try:
        for i, p in enumerate(doc):
            rect = p.rect
            pages.append(Page(number=i + 1, text=p.get_text("text"),
                              width=rect.width, height=rect.height))
    finally:
        doc.close()
    return pages

def _normalize(s: str) -> str:
    return " ".join(s.split())

def _fuzzy_rects(page, text: str, page_number: int, w: float, h: float) -> list[BoundingRect]:
    """Last-resort locate: find the best-matching run of words on the page for `text`
    and return a single rect enclosing it. Rescues quotes that don't match verbatim
    (paraphrase, hyphenation, whitespace, or residual redaction artifacts)."""
    words = page.get_text("words")  # (x0, y0, x1, y1, word, block, line, word_no)
    target = _normalize(text).split()
    if not words or not target:
        return []
    page_tokens = [wd[4].lower() for wd in words]
    matcher = difflib.SequenceMatcher(None, page_tokens, [t.lower() for t in target])
    match = matcher.find_longest_match(0, len(page_tokens), 0, len(target))
    # Require a reasonably strong anchor so we don't highlight a stray single word.
    if match.size < max(3, len(target) // 3):
        return []
    matched = words[match.a: match.a + match.size]
    return [BoundingRect(x1=min(m[0] for m in matched), y1=min(m[1] for m in matched),
                         x2=max(m[2] for m in matched), y2=max(m[3] for m in matched),
                         width=w, height=h, pageNumber=page_number)]


def search_rects(pdf_path: str, page_number: int, text: str) -> list[BoundingRect]:
    """Return bounding rects for `text` on `page_number` (1-based).
    Tries exact, then normalized-whitespace, then a short anchor substring, then a
    fuzzy word-run match as a last resort."""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_number - 1]
        w, h = page.rect.width, page.rect.height
        norm = _normalize(text)
        candidates = [text, norm]
        if len(norm) > 40:
            candidates.append(norm[:40])
        quads = []
        for c in candidates:
            if not c.strip():
                continue
            quads = page.search_for(c)
            if quads:
                break
        if quads:
            return [BoundingRect(x1=q.x0, y1=q.y0, x2=q.x1, y2=q.y1,
                                 width=w, height=h, pageNumber=page_number) for q in quads]
        return _fuzzy_rects(page, text, page_number, w, h)
    finally:
        doc.close()
