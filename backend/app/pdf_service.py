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

def search_rects(pdf_path: str, page_number: int, text: str) -> list[BoundingRect]:
    """Return bounding rects for `text` on `page_number` (1-based).
    Tries exact, then normalized-whitespace, then a short anchor substring."""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_number - 1]
        w, h = page.rect.width, page.rect.height
        candidates = [text, _normalize(text)]
        norm = _normalize(text)
        if len(norm) > 40:
            candidates.append(norm[:40])
        quads = []
        for c in candidates:
            if not c.strip():
                continue
            quads = page.search_for(c)
            if quads:
                break
        return [BoundingRect(x1=q.x0, y1=q.y0, x2=q.x1, y2=q.y1,
                             width=w, height=h, pageNumber=page_number) for q in quads]
    finally:
        doc.close()
