# Clause Lite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cheap-to-host demo that ingests a rental-lease PDF, flags illegal/risky clauses by RAG against Massachusetts landlord-tenant statutes, renders exact-overlay highlights + a clause list, and generates a downloadable demand letter.

**Architecture:** Two deployables — a FastAPI backend (Render free) doing PDF parsing, PII redaction, Gemini analysis, and Snowflake vector search behind a swappable interface; and a fresh Next.js frontend (Vercel) with a warm coral/cream/slate design and `react-pdf-highlighter`. Job state is ephemeral (in-memory + `/tmp`).

**Tech Stack:** Python 3.11, FastAPI, PyMuPDF (`fitz`), google-generativeai (Gemini Flash + embeddings), snowflake-connector-python, WeasyPrint, pytest. Next.js 15 (App Router), TypeScript, TailwindCSS, `react-pdf-highlighter`, `pdfjs-dist`.

**Reference:** `old_reference/Clause_frontend-main/` holds the old TS API types (`src/lib/api.ts`) and `public/sample-lease.pdf`. Read-only; deleted at the very end.

**Working directory:** `/Users/shreyansh/Desktop/clause`. Backend in `backend/`, frontend in `frontend/`.

---

## Conventions used across all tasks

- **Backend package root:** `backend/app/`. Tests in `backend/tests/`. Run from `backend/` with the venv active.
- **Type parity:** Pydantic model field names below are the single source of truth; the frontend TS interfaces (Task 20) mirror them exactly.
- **LLM injectability:** `LLMService` is a class holding a client object. Real code passes a Gemini client; tests pass a fake client with the same method names. No test calls a real API.
- **Commit after every task.** Use the message shown in the final step.

---

## Phase 0 — Scaffolding

### Task 0.1: Backend project skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py` (empty)
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/pytest.ini`
- Create: `backend/.env.example`

- [ ] **Step 1: Write `requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
python-multipart==0.0.12
pydantic==2.9.2
PyMuPDF==1.24.13
google-generativeai==0.8.3
snowflake-connector-python==3.12.3
weasyprint==63.0
python-dotenv==1.0.1
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 3: Write `.env.example`**

```
GEMINI_API_KEY=your_key
VECTOR_BACKEND=local
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=CLAUSE_WH
SNOWFLAKE_DATABASE=CLAUSE_DB
SNOWFLAKE_SCHEMA=PUBLIC
ALLOWED_ORIGINS=http://localhost:3000
```

- [ ] **Step 4: Create venv and install**

Run:
```bash
cd backend && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```
Expected: installs cleanly. (On macOS, WeasyPrint needs `brew install pango gdk-pixbuf libffi` — install if the import later fails.)

- [ ] **Step 5: Verify pytest runs**

Run: `cd backend && source .venv/bin/activate && pytest -q`
Expected: "no tests ran" (exit 0/5), no import errors.

- [ ] **Step 6: Commit**

```bash
git add backend/ && git commit -m "chore: backend skeleton and deps"
```

---

### Task 0.2: Frontend project skeleton

**Files:**
- Create: `frontend/` (via create-next-app)
- Modify: `frontend/.env.local`

- [ ] **Step 1: Scaffold Next.js**

Run:
```bash
cd /Users/shreyansh/Desktop/clause && npx create-next-app@latest frontend --typescript --tailwind --app --eslint --src-dir --import-alias "@/*" --no-turbopack --yes
```
Expected: `frontend/` created.

- [ ] **Step 2: Install runtime deps**

Run:
```bash
cd frontend && npm install react-pdf-highlighter pdfjs-dist react-hot-toast
```

- [ ] **Step 3: Write `frontend/.env.local`**

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 4: Verify dev server boots**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/ && git commit -m "chore: next.js frontend skeleton"
```

---

## Phase 1 — Backend domain models & PDF/PII services (TDD)

### Task 1: Pydantic models

**Files:**
- Create: `backend/app/models.py`
- Test: `backend/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_models.py
from app.models import Finding, HighlightPosition, BoundingRect, Severity, COLOR_BY_SEVERITY

def test_color_by_severity_maps_all():
    assert COLOR_BY_SEVERITY[Severity.illegal] == "red"
    assert COLOR_BY_SEVERITY[Severity.high] == "orange"
    assert COLOR_BY_SEVERITY[Severity.medium] == "yellow"
    assert COLOR_BY_SEVERITY[Severity.favorable] == "green"

def test_finding_serializes_camel_fields():
    pos = HighlightPosition(
        boundingRect=BoundingRect(x1=1, y1=2, x2=3, y2=4, width=612, height=792, pageNumber=1),
        rects=[BoundingRect(x1=1, y1=2, x2=3, y2=4, width=612, height=792, pageNumber=1)],
        pageWidth=612, pageHeight=792,
    )
    f = Finding(id="f1", page=1, quoted_text="x", category="Deposit",
                severity=Severity.illegal, color="red", statute_citation="M.G.L. c.186",
                explanation="why", damages_estimate=100.0, position=pos)
    assert f.model_dump()["position"]["boundingRect"]["pageNumber"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL (ImportError: app.models).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/models.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class Severity(str, Enum):
    illegal = "illegal"
    high = "high"
    medium = "medium"
    favorable = "favorable"

COLOR_BY_SEVERITY = {
    Severity.illegal: "red",
    Severity.high: "orange",
    Severity.medium: "yellow",
    Severity.favorable: "green",
}

class BoundingRect(BaseModel):
    x1: float; y1: float; x2: float; y2: float
    width: float; height: float; pageNumber: int

class HighlightPosition(BaseModel):
    boundingRect: BoundingRect
    rects: list[BoundingRect]
    pageWidth: float
    pageHeight: float

class Finding(BaseModel):
    id: str
    page: int
    quoted_text: str
    category: str
    severity: Severity
    color: str
    statute_citation: Optional[str] = None
    explanation: str
    damages_estimate: Optional[float] = None
    position: Optional[HighlightPosition] = None

class Parties(BaseModel):
    landlord: str = ""
    tenant: str = ""
    property: str = ""

class Metadata(BaseModel):
    parties: Parties = Parties()
    monthlyRent: str = ""
    leaseTerm: str = ""
    securityDeposit: str = ""

class DeidentificationSummary(BaseModel):
    redactedEntities: dict[str, int] = {}
    encryptionStatus: str = "disabled"

class TopIssue(BaseModel):
    title: str
    severity: str
    amount: Optional[str] = None

class AnalysisSummary(BaseModel):
    overallRisk: str = "Low"
    issuesFound: int = 0
    estimatedRecovery: str = "$0"
    topIssues: list[TopIssue] = []

class AnalysisResult(BaseModel):
    documentId: str
    documentMetadata: Metadata = Metadata()
    deidentificationSummary: DeidentificationSummary = DeidentificationSummary()
    analysisSummary: AnalysisSummary = AnalysisSummary()
    highlights: list[Finding] = []

class JobStatus(BaseModel):
    file_id: str
    status: str  # uploaded | processing | metadata_extracted | completed | failed
    progress: int = 0
    message: str = ""
    filename: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat: pydantic domain models"
```

---

### Task 2: PDF service (text + word boxes + rect search)

**Files:**
- Create: `backend/app/pdf_service.py`
- Test: `backend/tests/test_pdf_service.py`
- Fixture: copy sample PDF → `backend/tests/fixtures/sample-lease.pdf`

- [ ] **Step 1: Copy the fixture**

Run:
```bash
mkdir -p backend/tests/fixtures && cp old_reference/Clause_frontend-main/public/sample-lease.pdf backend/tests/fixtures/sample-lease.pdf
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_pdf_service.py
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
    # pick a word that exists on page 1
    word = pages[0].text.split()[0]
    rects = search_rects(str(FIX), 1, word)
    assert len(rects) >= 1
    r = rects[0]
    assert r.x2 > r.x1 and r.y2 > r.y1 and r.pageNumber == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_pdf_service.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 4: Write minimal implementation**

```python
# backend/app/pdf_service.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_pdf_service.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/pdf_service.py backend/tests/test_pdf_service.py backend/tests/fixtures/
git commit -m "feat: pdf text extraction and rect search"
```

---

### Task 3: PII redaction service

**Files:**
- Create: `backend/app/pii_service.py`
- Test: `backend/tests/test_pii_service.py`

Note: keep it simple (regex-based) per spec §2. Original text is NOT mutated — callers keep the original for coordinate mapping and pass a copy of the text here.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_pii_service.py
from app.pii_service import redact

def test_redacts_email_phone_and_reports_counts():
    text = "Contact john@example.com or 415-555-1234 for questions."
    result = redact(text)
    assert "john@example.com" not in result.redacted_text
    assert "415-555-1234" not in result.redacted_text
    assert result.summary.get("email") == 1
    assert result.summary.get("phone") == 1

def test_no_pii_leaves_text_unchanged():
    text = "The tenant shall pay rent monthly."
    result = redact(text)
    assert result.redacted_text == text
    assert sum(result.summary.values()) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pii_service.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/pii_service.py
import re
from dataclasses import dataclass, field

@dataclass
class RedactionResult:
    redacted_text: str
    summary: dict = field(default_factory=dict)

_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}
_PLACEHOLDER = {"email": "[EMAIL]", "phone": "[PHONE]", "ssn": "[SSN]"}

def redact(text: str) -> RedactionResult:
    summary: dict[str, int] = {}
    out = text
    for kind, pattern in _PATTERNS.items():
        matches = pattern.findall(out)
        if matches:
            summary[kind] = len(matches)
            out = pattern.sub(_PLACEHOLDER[kind], out)
    return RedactionResult(redacted_text=out, summary=summary)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pii_service.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/pii_service.py backend/tests/test_pii_service.py
git commit -m "feat: regex PII redaction"
```

---

## Phase 2 — Vector store (interface + Local + Snowflake)

### Task 4: VectorStore interface + LocalVectorStore

**Files:**
- Create: `backend/app/vector_store.py`
- Test: `backend/tests/test_vector_store.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_vector_store.py
from app.vector_store import LocalVectorStore, Statute

def test_local_store_seed_and_search_orders_by_similarity():
    store = LocalVectorStore()
    store.seed([
        Statute(id="a", chapter="186", section="15B", title="Deposits", text="security deposit",
                embedding=[1.0, 0.0, 0.0]),
        Statute(id="b", chapter="186", section="14", title="Entry", text="quiet enjoyment",
                embedding=[0.0, 1.0, 0.0]),
    ])
    results = store.search([0.9, 0.1, 0.0], k=2)
    assert results[0].id == "a"
    assert len(results) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vector_store.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/vector_store.py
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional, Protocol

@dataclass
class Statute:
    id: str
    chapter: str
    section: str
    title: str
    text: str
    embedding: Optional[list[float]] = None

class VectorStore(Protocol):
    def seed(self, statutes: list[Statute]) -> None: ...
    def search(self, embedding: list[float], k: int) -> list[Statute]: ...

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

class LocalVectorStore:
    def __init__(self) -> None:
        self._items: list[Statute] = []

    def seed(self, statutes: list[Statute]) -> None:
        self._items = list(statutes)

    def search(self, embedding: list[float], k: int) -> list[Statute]:
        scored = sorted(self._items,
                        key=lambda s: _cosine(embedding, s.embedding or []),
                        reverse=True)
        return scored[:k]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vector_store.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/vector_store.py backend/tests/test_vector_store.py
git commit -m "feat: vector store interface and local backend"
```

---

### Task 5: SnowflakeVectorStore + factory

**Files:**
- Modify: `backend/app/vector_store.py`
- Test: `backend/tests/test_vector_store_factory.py`

The Snowflake class is exercised only via a fake connection in tests (no live Snowflake). A `get_vector_store()` factory picks the backend from `VECTOR_BACKEND`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_vector_store_factory.py
from app.vector_store import get_vector_store, LocalVectorStore, SnowflakeVectorStore

def test_factory_returns_local_by_default(monkeypatch):
    monkeypatch.setenv("VECTOR_BACKEND", "local")
    assert isinstance(get_vector_store(), LocalVectorStore)

def test_snowflake_search_builds_cosine_query():
    captured = {}
    class FakeCursor:
        def execute(self, sql, params=None):
            captured["sql"] = sql; captured["params"] = params
        def fetchall(self):
            return [("a", "186", "15B", "Deposits", "security deposit text")]
        def close(self): pass
    class FakeConn:
        def cursor(self): return FakeCursor()
    store = SnowflakeVectorStore(conn_factory=lambda: FakeConn())
    results = store.search([0.1, 0.2, 0.3], k=3)
    assert "VECTOR_COSINE_SIMILARITY" in captured["sql"]
    assert results[0].id == "a" and results[0].title == "Deposits"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vector_store_factory.py -v`
Expected: FAIL (ImportError: SnowflakeVectorStore).

- [ ] **Step 3: Add implementation to `vector_store.py`**

```python
# append to backend/app/vector_store.py
import os
from typing import Callable

class SnowflakeVectorStore:
    def __init__(self, conn_factory: Callable[[], object], dim: int = 768,
                 table: str = "STATUTES") -> None:
        self._conn_factory = conn_factory
        self._dim = dim
        self._table = table

    def seed(self, statutes: list[Statute]) -> None:
        conn = self._conn_factory()
        cur = conn.cursor()
        try:
            for s in statutes:
                vec = "[" + ",".join(str(x) for x in (s.embedding or [])) + "]"
                cur.execute(
                    f"INSERT INTO {self._table} (id, chapter, section, title, text, embedding) "
                    f"SELECT %s, %s, %s, %s, %s, {vec}::VECTOR(FLOAT, {self._dim})",
                    (s.id, s.chapter, s.section, s.title, s.text),
                )
        finally:
            cur.close()

    def search(self, embedding: list[float], k: int) -> list[Statute]:
        vec = "[" + ",".join(str(x) for x in embedding) + "]"
        sql = (
            f"SELECT id, chapter, section, title, text FROM {self._table} "
            f"ORDER BY VECTOR_COSINE_SIMILARITY(embedding, {vec}::VECTOR(FLOAT, {self._dim})) "
            f"DESC LIMIT %s"
        )
        conn = self._conn_factory()
        cur = conn.cursor()
        try:
            cur.execute(sql, (k,))
            rows = cur.fetchall()
            return [Statute(id=r[0], chapter=r[1], section=r[2], title=r[3], text=r[4]) for r in rows]
        finally:
            cur.close()

def _default_snowflake_conn():
    import snowflake.connector
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=os.environ.get("SNOWFLAKE_DATABASE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA"),
    )

def get_vector_store() -> VectorStore:
    backend = os.environ.get("VECTOR_BACKEND", "local").lower()
    if backend == "snowflake":
        return SnowflakeVectorStore(conn_factory=_default_snowflake_conn)
    return LocalVectorStore()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vector_store_factory.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/vector_store.py backend/tests/test_vector_store_factory.py
git commit -m "feat: snowflake vector store and backend factory"
```

---

## Phase 3 — LLM service, highlighting, orchestration

### Task 6: LLMService (Gemini wrappers, injectable client)

**Files:**
- Create: `backend/app/llm_service.py`
- Test: `backend/tests/test_llm_service.py`

`LLMService` takes a `client` with methods `generate_json(prompt) -> dict` and `embed(text) -> list[float]`. The real client (Task 10 wiring) wraps `google.generativeai`. Tests pass a fake.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_llm_service.py
from app.llm_service import LLMService

class FakeClient:
    def __init__(self, payload): self.payload = payload; self.calls = []
    def generate_json(self, prompt):
        self.calls.append(prompt); return self.payload
    def embed(self, text): return [0.1, 0.2, 0.3]

def test_extract_metadata_maps_fields():
    client = FakeClient({"parties": {"landlord": "L", "tenant": "T", "property": "P"},
                         "monthlyRent": "$1000", "leaseTerm": "12mo", "securityDeposit": "$1500"})
    svc = LLMService(client)
    md = svc.extract_metadata("some redacted text")
    assert md.parties.landlord == "L" and md.monthlyRent == "$1000"

def test_analyze_chunk_returns_finding_drafts():
    client = FakeClient({"findings": [
        {"quoted_text": "no return of deposit", "page": 2, "category": "Deposit",
         "severity": "illegal", "statute_citation": "M.G.L. c.186 s.15B",
         "explanation": "deposits must be returned", "damages_estimate": 1500}
    ]})
    svc = LLMService(client)
    drafts = svc.analyze_chunk("chunk", [], page_hint=2)
    assert drafts[0].severity == "illegal" and drafts[0].damages_estimate == 1500

def test_embed_delegates_to_client():
    svc = LLMService(FakeClient({}))
    assert svc.embed("hi") == [0.1, 0.2, 0.3]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_service.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/llm_service.py
from dataclasses import dataclass
from typing import Optional
from app.models import Metadata, Parties
from app.vector_store import Statute

@dataclass
class FindingDraft:
    quoted_text: str
    page: int
    category: str
    severity: str
    statute_citation: Optional[str]
    explanation: str
    damages_estimate: Optional[float]

_META_PROMPT = (
    "Extract lease metadata as JSON with keys parties{{landlord,tenant,property}}, "
    "monthlyRent, leaseTerm, securityDeposit. Use empty strings if unknown.\n\nDOCUMENT:\n{text}"
)

_ANALYZE_PROMPT = (
    "You are a Massachusetts tenant-rights attorney. Given a lease CHUNK and relevant STATUTES, "
    "return JSON {{\"findings\": [ ... ]}} where each finding has quoted_text (verbatim from the "
    "chunk), page (integer), category, severity (one of illegal|high|medium|favorable), "
    "statute_citation, explanation, damages_estimate (number or null). Only flag real issues. "
    "Default page to {page_hint}.\n\nSTATUTES:\n{statutes}\n\nCHUNK:\n{chunk}"
)

class LLMService:
    def __init__(self, client) -> None:
        self._client = client

    def embed(self, text: str) -> list[float]:
        return self._client.embed(text)

    def extract_metadata(self, text: str) -> Metadata:
        data = self._client.generate_json(_META_PROMPT.format(text=text[:8000]))
        p = data.get("parties", {}) or {}
        return Metadata(
            parties=Parties(landlord=p.get("landlord", ""), tenant=p.get("tenant", ""),
                            property=p.get("property", "")),
            monthlyRent=data.get("monthlyRent", ""),
            leaseTerm=data.get("leaseTerm", ""),
            securityDeposit=data.get("securityDeposit", ""),
        )

    def analyze_chunk(self, chunk: str, statutes: list[Statute], page_hint: int = 1) -> list[FindingDraft]:
        statute_text = "\n".join(f"- {s.chapter} s.{s.section} {s.title}: {s.text}" for s in statutes)
        data = self._client.generate_json(
            _ANALYZE_PROMPT.format(statutes=statute_text, chunk=chunk, page_hint=page_hint))
        out = []
        for f in data.get("findings", []):
            out.append(FindingDraft(
                quoted_text=f.get("quoted_text", ""),
                page=int(f.get("page", page_hint) or page_hint),
                category=f.get("category", "General"),
                severity=f.get("severity", "medium"),
                statute_citation=f.get("statute_citation"),
                explanation=f.get("explanation", ""),
                damages_estimate=f.get("damages_estimate"),
            ))
        return out

    def draft_demand_letter(self, findings: list[FindingDraft], metadata: Metadata,
                            sender: dict, recipient: dict) -> str:
        issues = "\n".join(f"- {f.category} ({f.severity}): {f.explanation} "
                           f"[{f.statute_citation}]" for f in findings)
        prompt = (
            "Draft the BODY (HTML paragraphs only, no <html>/<head>) of a firm but professional "
            "demand letter from a Massachusetts tenant to a landlord citing these issues and "
            "requesting remedy within 30 days.\n\n"
            f"SENDER: {sender}\nRECIPIENT: {recipient}\nISSUES:\n{issues}"
        )
        data = self._client.generate_json(prompt)
        return data.get("html", "") if isinstance(data, dict) else str(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_service.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm_service.py backend/tests/test_llm_service.py
git commit -m "feat: gemini-backed LLM service with injectable client"
```

---

### Task 7: Highlight builder

**Files:**
- Create: `backend/app/highlight.py`
- Test: `backend/tests/test_highlight.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_highlight.py
from app.highlight import build_highlight, color_for
from app.llm_service import FindingDraft
from app.models import Severity
from pathlib import Path

FIX = str(Path(__file__).parent / "fixtures" / "sample-lease.pdf")

def test_color_for_maps_severity():
    assert color_for("illegal") == "red"
    assert color_for("favorable") == "green"

def test_build_highlight_resolves_position_for_present_text():
    # use a word known to be on page 1
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
    assert fh.position is None  # graceful: finding kept, no rects
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_highlight.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/highlight.py
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
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_highlight.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/highlight.py backend/tests/test_highlight.py
git commit -m "feat: highlight builder with graceful degradation"
```

---

### Task 8: Analysis orchestrator + job registry

**Files:**
- Create: `backend/app/jobs.py`
- Create: `backend/app/analysis.py`
- Test: `backend/tests/test_analysis.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_analysis.py
from pathlib import Path
from app.jobs import JobRegistry
from app.analysis import analyze_document
from app.vector_store import LocalVectorStore, Statute

FIX = str(Path(__file__).parent / "fixtures" / "sample-lease.pdf")

class FakeClient:
    def embed(self, text): return [1.0, 0.0, 0.0]
    def generate_json(self, prompt):
        # first word of page 1 so search_for resolves a rect
        from app.pdf_service import extract_pages
        word = extract_pages(FIX)[0].text.split()[0]
        return {"findings": [{"quoted_text": word, "page": 1, "category": "Deposit",
                              "severity": "illegal", "statute_citation": "c.186 s.15B",
                              "explanation": "deposit issue", "damages_estimate": 1500}]}

def test_analyze_document_produces_result_and_progress():
    from app.llm_service import LLMService
    registry = JobRegistry()
    registry.create("fid", filename="sample-lease.pdf")
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="Deposits",
                        text="deposit", embedding=[1.0, 0.0, 0.0])])
    result = analyze_document("fid", FIX, redacted_text="chunk text",
                              llm=LLMService(FakeClient()), store=store, registry=registry)
    assert result.analysisSummary.issuesFound >= 1
    assert registry.get("fid").status == "completed"
    assert registry.get("fid").progress == 100
    assert result.highlights[0].color == "red"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_analysis.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write `jobs.py`**

```python
# backend/app/jobs.py
from threading import Lock
from app.models import JobStatus

class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, JobStatus] = {}
        self._lock = Lock()

    def create(self, file_id: str, filename: str = "") -> None:
        with self._lock:
            self._jobs[file_id] = JobStatus(file_id=file_id, status="uploaded",
                                            progress=0, message="Uploaded", filename=filename)

    def update(self, file_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs[file_id]
            self._jobs[file_id] = job.model_copy(update=fields)

    def get(self, file_id: str) -> JobStatus | None:
        return self._jobs.get(file_id)
```

- [ ] **Step 4: Write `analysis.py`**

```python
# backend/app/analysis.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_analysis.py -v`
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/jobs.py backend/app/analysis.py backend/tests/test_analysis.py
git commit -m "feat: analysis orchestrator and job registry"
```

---

### Task 9: Demand-letter PDF service

**Files:**
- Create: `backend/app/letter_service.py`
- Test: `backend/tests/test_letter_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_letter_service.py
from app.letter_service import render_letter_pdf

def test_render_letter_returns_pdf_bytes():
    pdf = render_letter_pdf("<p>Dear Landlord, please return my deposit.</p>",
                            title="Demand Letter")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_letter_service.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/letter_service.py
from weasyprint import HTML

_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; color: #141413; margin: 1in; line-height: 1.5; }}
  h1 {{ color: #CC785C; font-size: 20px; }}
</style></head>
<body><h1>{title}</h1>{body}</body></html>"""

def render_letter_pdf(body_html: str, title: str = "Demand Letter") -> bytes:
    html = _TEMPLATE.format(title=title, body=body_html)
    return HTML(string=html).write_pdf()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_letter_service.py -v`
Expected: PASS (1 passed). (If WeasyPrint import fails on macOS, install system libs: `brew install pango gdk-pixbuf libffi`.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/letter_service.py backend/tests/test_letter_service.py
git commit -m "feat: weasyprint demand-letter rendering"
```

---

## Phase 4 — Gemini client, API layer, seed corpus

### Task 10: Real Gemini client adapter

**Files:**
- Create: `backend/app/gemini_client.py`
- Test: `backend/tests/test_gemini_client.py`

Wraps `google.generativeai` into the `generate_json`/`embed` interface `LLMService` expects. Tests verify JSON parsing/robustness with a stubbed model, not a live call.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_gemini_client.py
from app.gemini_client import GeminiClient

class FakeResp:
    def __init__(self, text): self.text = text

class FakeModel:
    def __init__(self, text): self._text = text
    def generate_content(self, prompt): return FakeResp(self._text)

def test_generate_json_parses_fenced_block():
    client = GeminiClient(model=FakeModel('```json\n{"a": 1}\n```'), embed_fn=lambda t: [0.0])
    assert client.generate_json("p") == {"a": 1}

def test_generate_json_returns_empty_on_garbage():
    client = GeminiClient(model=FakeModel("not json at all"), embed_fn=lambda t: [0.0])
    assert client.generate_json("p") == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gemini_client.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/gemini_client.py
import json, os, re
from typing import Callable, Optional

_FENCE = re.compile(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", re.DOTALL)

class GeminiClient:
    def __init__(self, model=None, embed_fn: Optional[Callable[[str], list]] = None) -> None:
        self._model = model
        self._embed_fn = embed_fn

    @classmethod
    def from_env(cls) -> "GeminiClient":
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash")
        def embed_fn(text: str) -> list:
            r = genai.embed_content(model="models/text-embedding-004", content=text)
            return r["embedding"]
        return cls(model=model, embed_fn=embed_fn)

    def embed(self, text: str) -> list:
        return self._embed_fn(text)

    def generate_json(self, prompt: str) -> dict:
        raw = self._model.generate_content(prompt).text or ""
        m = _FENCE.search(raw)
        candidate = m.group(1) if m else raw.strip()
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {"findings": parsed}
        except json.JSONDecodeError:
            return {}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gemini_client.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/gemini_client.py backend/tests/test_gemini_client.py
git commit -m "feat: gemini client adapter with robust json parsing"
```

---

### Task 11: FastAPI app + endpoints

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/state.py`
- Test: `backend/tests/test_api.py`

`state.py` holds process-wide singletons (job registry, vector store, llm, temp dir) so tests can monkeypatch them. Endpoints mirror the spec.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api.py
from pathlib import Path
from fastapi.testclient import TestClient
import app.state as state
from app.main import app
from app.vector_store import LocalVectorStore, Statute
from app.llm_service import LLMService

FIX = Path(__file__).parent / "fixtures" / "sample-lease.pdf"

class FakeClient:
    def embed(self, text): return [1.0, 0.0, 0.0]
    def generate_json(self, prompt):
        if "metadata" in prompt.lower():
            return {"parties": {"landlord": "L", "tenant": "T", "property": "P"},
                    "monthlyRent": "$1000", "leaseTerm": "12mo", "securityDeposit": "$1500"}
        from app.pdf_service import extract_pages
        word = extract_pages(str(FIX))[0].text.split()[0]
        return {"findings": [{"quoted_text": word, "page": 1, "category": "Deposit",
                              "severity": "illegal", "statute_citation": "c.186",
                              "explanation": "e", "damages_estimate": 1500}]}

def setup_module(module):
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="Deposits",
                        text="deposit", embedding=[1.0, 0.0, 0.0])])
    state.vector_store = store
    state.llm = LLMService(FakeClient())

def test_full_flow_upload_analyze_results():
    client = TestClient(app)
    with open(FIX, "rb") as f:
        up = client.post("/upload", files={"file": ("sample-lease.pdf", f, "application/pdf")})
    assert up.status_code == 200
    fid = up.json()["file_id"]
    assert "pii_redacted" in up.json()

    an = client.post("/analyze", json={"file_id": fid})
    assert an.status_code == 200

    st = client.get(f"/status/{fid}")
    assert st.status_code == 200 and st.json()["status"] in ("processing", "completed")

    doc = client.get(f"/document/{fid}")
    assert doc.status_code == 200
    assert doc.json()["analysisSummary"]["issuesFound"] >= 1

def test_pdf_endpoint_serves_bytes():
    client = TestClient(app)
    with open(FIX, "rb") as f:
        fid = client.post("/upload", files={"file": ("s.pdf", f, "application/pdf")}).json()["file_id"]
    r = client.get(f"/pdf/{fid}")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write `state.py`**

```python
# backend/app/state.py
import os, tempfile
from app.jobs import JobRegistry
from app.vector_store import get_vector_store
from app.llm_service import LLMService

TMP_DIR = os.path.join(tempfile.gettempdir(), "clause")
os.makedirs(TMP_DIR, exist_ok=True)

registry = JobRegistry()
vector_store = get_vector_store()
llm: LLMService | None = None  # set in main on startup or by tests

results: dict[str, "object"] = {}          # file_id -> AnalysisResult
redacted_text: dict[str, str] = {}          # file_id -> redacted text
metadata_store: dict[str, "object"] = {}    # file_id -> Metadata

def pdf_path(file_id: str) -> str:
    return os.path.join(TMP_DIR, f"{file_id}.pdf")
```

- [ ] **Step 4: Write `main.py`**

```python
# backend/app/main.py
import os, uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import app.state as state
from app.pdf_service import extract_pages
from app.pii_service import redact
from app.analysis import analyze_document
from app.letter_service import render_letter_pdf

app = FastAPI(title="Clause Lite")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def _init_llm():
    if state.llm is None:
        from app.gemini_client import GeminiClient
        state.llm = LLMServiceFromEnv()

def LLMServiceFromEnv():
    from app.gemini_client import GeminiClient
    from app.llm_service import LLMService
    return LLMService(GeminiClient.from_env())

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "File exceeds 10MB")
    file_id = uuid.uuid4().hex
    with open(state.pdf_path(file_id), "wb") as f:
        f.write(data)
    pages = extract_pages(state.pdf_path(file_id))
    if len(pages) > 15:
        raise HTTPException(400, "Document exceeds 15 pages for this demo")
    full_text = "\n".join(p.text for p in pages)
    red = redact(full_text)
    state.redacted_text[file_id] = red.redacted_text
    state.registry.create(file_id, filename=file.filename)
    return {"file_id": file_id, "filename": file.filename, "size": len(data),
            "pii_redacted": red.summary,
            "message": f"Protected {sum(red.summary.values())} pieces of personal information"}

class FileIdBody(BaseModel):
    file_id: str

@app.post("/extract-metadata")
def extract_metadata(body: FileIdBody):
    text = state.redacted_text.get(body.file_id)
    if text is None:
        raise HTTPException(404, "Unknown file_id")
    md = state.llm.extract_metadata(text)
    state.metadata_store[body.file_id] = md
    state.registry.update(body.file_id, status="metadata_extracted", message="Metadata extracted")
    return {"file_id": body.file_id, "status": "metadata_extracted", "metadata": md.model_dump()}

def _run_analysis(file_id: str):
    result = analyze_document(file_id, state.pdf_path(file_id),
                              state.redacted_text.get(file_id, ""),
                              state.llm, state.vector_store, state.registry)
    md = state.metadata_store.get(file_id)
    if md is not None:
        result.documentMetadata = md
    state.results[file_id] = result

@app.post("/analyze")
def analyze(body: FileIdBody, background: BackgroundTasks):
    if body.file_id not in state.redacted_text:
        raise HTTPException(404, "Unknown file_id")
    state.registry.update(body.file_id, status="processing", progress=10, message="Starting analysis...")
    background.add_task(_run_analysis, body.file_id)
    return {"file_id": body.file_id, "status": "processing"}

@app.get("/status/{file_id}")
def status(file_id: str):
    job = state.registry.get(file_id)
    if job is None:
        raise HTTPException(404, "Unknown file_id")
    return job.model_dump()

@app.get("/document/{file_id}")
def document(file_id: str):
    result = state.results.get(file_id)
    if result is None:
        raise HTTPException(404, "Analysis not ready")
    return result.model_dump()

@app.get("/pdf/{file_id}")
def pdf(file_id: str):
    path = state.pdf_path(file_id)
    if not os.path.exists(path):
        raise HTTPException(404, "PDF not found")
    return FileResponse(path, media_type="application/pdf")

class DemandLetterBody(BaseModel):
    file_id: str
    sender: dict = {}
    recipient: dict = {}

@app.post("/demand-letter")
def demand_letter(body: DemandLetterBody):
    result = state.results.get(body.file_id)
    if result is None:
        raise HTTPException(404, "Analysis not ready")
    from app.llm_service import FindingDraft
    drafts = [FindingDraft(quoted_text=h.quoted_text, page=h.page, category=h.category,
                           severity=h.severity.value, statute_citation=h.statute_citation,
                           explanation=h.explanation, damages_estimate=h.damages_estimate)
              for h in result.highlights]
    md = state.metadata_store.get(body.file_id) or result.documentMetadata
    body_html = state.llm.draft_demand_letter(drafts, md, body.sender, body.recipient)
    pdf_bytes = render_letter_pdf(body_html, title="Demand Letter")
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=demand-letter.pdf"})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`
Expected: PASS (2 passed). Note: the `/analyze` BackgroundTask runs after the response in TestClient; `test_full_flow` calls `/document` which may need the task to have run — TestClient executes background tasks synchronously on context exit, so fetch `/document` inside the same `with TestClient(app) as client:` block if flaky. If so, wrap the client in a `with` block.

- [ ] **Step 6: Adjust test if needed and re-run**

If `/document` returns 404, change the test to use `with TestClient(app) as client:` so background tasks flush. Re-run until green.

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py backend/app/state.py backend/tests/test_api.py
git commit -m "feat: fastapi endpoints for full analysis flow"
```

---

### Task 12: MA statute corpus + seed script

**Files:**
- Create: `backend/app/data/ma_statutes.json`
- Create: `backend/app/seed_statutes.py`
- Test: `backend/tests/test_seed.py`

- [ ] **Step 1: Write the corpus** (`backend/app/data/ma_statutes.json`)

Start with a curated set (expand later). Each item: `{id, chapter, section, title, text}`.

```json
[
  {"id": "186-15B", "chapter": "186", "section": "15B", "title": "Security deposits",
   "text": "A landlord may not require a security deposit greater than one month's rent, must hold it in a separate interest-bearing account, provide a receipt and a statement of condition, and return it with interest within 30 days after tenancy ends. Failure can entitle the tenant to treble damages."},
  {"id": "186-15", "chapter": "186", "section": "15", "title": "Waiver of rights void",
   "text": "Any provision in a lease whereby a tenant waives statutory rights, such as habitability or the right to a jury trial, is against public policy and void."},
  {"id": "186-14", "chapter": "186", "section": "14", "title": "Quiet enjoyment; utilities",
   "text": "A landlord who directly or indirectly interferes with a tenant's quiet enjoyment, or shuts off utilities, is liable for actual and consequential damages or three months' rent, plus costs and attorney fees."},
  {"id": "239-8A", "chapter": "239", "section": "8A", "title": "Repairs; rent withholding",
   "text": "A tenant may withhold rent or raise defenses for a landlord's breach of the warranty of habitability or failure to maintain the premises in compliance with the sanitary code."},
  {"id": "186-18", "chapter": "186", "section": "18", "title": "Reprisal for reporting",
   "text": "Retaliation against a tenant for reporting code violations or exercising legal rights within six months is presumed unlawful and creates liability for damages of one to three months' rent."},
  {"id": "111-127L", "chapter": "111", "section": "127L", "title": "Right to repair and deduct",
   "text": "Where a landlord fails to remedy a serious sanitary code violation after notice, the tenant may repair and deduct up to four months' rent."},
  {"id": "186-11", "chapter": "186", "section": "11", "title": "Notice to quit for nonpayment",
   "text": "A tenancy at will may only be terminated for nonpayment after proper 14-day written notice to quit; self-help eviction and lockouts are prohibited."},
  {"id": "186-12", "chapter": "186", "section": "12", "title": "Notice to terminate tenancy at will",
   "text": "Termination of a tenancy at will requires written notice equal to the interval between rent days or 30 days, whichever is longer."}
]
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_seed.py
import json
from pathlib import Path
from app.seed_statutes import load_corpus, build_statutes

class FakeLLM:
    def embed(self, text): return [float(len(text) % 7), 1.0, 2.0]

def test_load_corpus_reads_all_items():
    items = load_corpus()
    assert len(items) >= 8
    assert all({"id", "chapter", "section", "title", "text"} <= set(i) for i in items)

def test_build_statutes_attaches_embeddings():
    statutes = build_statutes(load_corpus(), FakeLLM())
    assert statutes[0].embedding is not None and len(statutes[0].embedding) == 3
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_seed.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 4: Write `seed_statutes.py`**

```python
# backend/app/seed_statutes.py
import json, os
from pathlib import Path
from app.vector_store import Statute, get_vector_store

_DATA = Path(__file__).parent / "data" / "ma_statutes.json"

def load_corpus() -> list[dict]:
    return json.loads(_DATA.read_text())

def build_statutes(items: list[dict], llm) -> list[Statute]:
    out = []
    for it in items:
        emb = llm.embed(f"{it['title']}. {it['text']}")
        out.append(Statute(id=it["id"], chapter=it["chapter"], section=it["section"],
                           title=it["title"], text=it["text"], embedding=emb))
    return out

def main() -> None:
    from app.llm_service import LLMService
    from app.gemini_client import GeminiClient
    llm = LLMService(GeminiClient.from_env())
    statutes = build_statutes(load_corpus(), llm)
    store = get_vector_store()
    store.seed(statutes)
    print(f"Seeded {len(statutes)} statutes into {os.environ.get('VECTOR_BACKEND','local')} store.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_seed.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Full backend suite green**

Run: `pytest -q`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/data/ma_statutes.json backend/app/seed_statutes.py backend/tests/test_seed.py
git commit -m "feat: MA statute corpus and seed script"
```

---

### Task 13: Local-store bootstrap at startup

**Files:**
- Modify: `backend/app/main.py` (startup hook)
- Test: `backend/tests/test_bootstrap.py`

For the `local` backend, seed the in-memory store on startup so `/analyze` has statutes without a separate seed run.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_bootstrap.py
import os
import app.state as state
from app.bootstrap import seed_local_if_needed
from app.vector_store import LocalVectorStore

class FakeLLM:
    def embed(self, text): return [1.0, 2.0, 3.0]

def test_seed_local_populates_store(monkeypatch):
    monkeypatch.setenv("VECTOR_BACKEND", "local")
    store = LocalVectorStore()
    seed_local_if_needed(store, FakeLLM())
    results = store.search([1.0, 2.0, 3.0], k=3)
    assert len(results) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bootstrap.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Write `bootstrap.py`**

```python
# backend/app/bootstrap.py
import os
from app.seed_statutes import load_corpus, build_statutes
from app.vector_store import LocalVectorStore

def seed_local_if_needed(store, llm) -> None:
    if os.environ.get("VECTOR_BACKEND", "local").lower() == "local" and isinstance(store, LocalVectorStore):
        store.seed(build_statutes(load_corpus(), llm))
```

- [ ] **Step 4: Wire into `main.py` startup**

Add to the `_init_llm` startup function, after `state.llm` is set:

```python
    from app.bootstrap import seed_local_if_needed
    seed_local_if_needed(state.vector_store, state.llm)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_bootstrap.py -v && pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/bootstrap.py backend/app/main.py backend/tests/test_bootstrap.py
git commit -m "feat: seed local vector store on startup"
```

---

## Phase 5 — Frontend

> Frontend tasks favor concrete component code + a manual browser check over unit tests (UI/visual). Use the `frontend-design` skill to drive visual quality; the palette and inspiration are in the spec §3. Run the backend locally (`cd backend && source .venv/bin/activate && VECTOR_BACKEND=local GEMINI_API_KEY=... uvicorn app.main:app --reload`) while building.

### Task 14: Design tokens + animated backdrop

**Files:**
- Modify: `frontend/src/app/globals.css`
- Create: `frontend/src/app/theme.ts`
- Create: `frontend/src/components/Backdrop.tsx`

- [ ] **Step 1: Add palette CSS variables to `globals.css`** (append)

```css
:root {
  --canvas: #FAF9F5;
  --surface: #F0EEE6;
  --accent: #D97757;
  --accent-deep: #CC785C;
  --ink: #141413;
  --ink-muted: #3D3D3A;
  --ink-subtle: #6B6B63;
  --sev-illegal: #E5484D;
  --sev-high: #E8833A;
  --sev-medium: #E4B62C;
  --sev-favorable: #3FA372;
}
body { background: var(--canvas); color: var(--ink); }
```

- [ ] **Step 2: Write `theme.ts`** (severity → color map for JS use)

```ts
export const SEVERITY_COLORS: Record<string, string> = {
  illegal: "var(--sev-illegal)",
  high: "var(--sev-high)",
  medium: "var(--sev-medium)",
  favorable: "var(--sev-favorable)",
};
export const HIGHLIGHT_HEX: Record<string, string> = {
  red: "#E5484D", orange: "#E8833A", yellow: "#E4B62C", green: "#3FA372",
};
```

- [ ] **Step 3: Write `Backdrop.tsx`** (soft gooey gradient blobs)

```tsx
export function Backdrop() {
  return (
    <div aria-hidden className="fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-32 -left-24 h-96 w-96 rounded-full blur-3xl opacity-40"
           style={{ background: "radial-gradient(circle at 30% 30%, #D97757, transparent 70%)" }} />
      <div className="absolute top-1/3 -right-24 h-[28rem] w-[28rem] rounded-full blur-3xl opacity-30"
           style={{ background: "radial-gradient(circle at 70% 30%, #E8833A, transparent 70%)" }} />
      <div className="absolute inset-0" style={{ backdropFilter: "blur(0px)" }} />
    </div>
  );
}
```

- [ ] **Step 4: Render `Backdrop` in the root layout**

Add `<Backdrop />` at the top of the `<body>` in `frontend/src/app/layout.tsx` and import it.

- [ ] **Step 5: Manual check**

Run `npm run dev`, open `http://localhost:3000` — warm canvas with soft coral blobs, no console errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/globals.css frontend/src/app/theme.ts frontend/src/components/Backdrop.tsx frontend/src/app/layout.tsx
git commit -m "feat(ui): warm palette tokens and gooey backdrop"
```

---

### Task 15: Typed API client

**Files:**
- Create: `frontend/src/lib/api.ts`

Mirror the backend Pydantic field names exactly (see Task 1). This is the parity contract.

- [ ] **Step 1: Write `api.ts`**

```ts
export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UploadResponse {
  file_id: string; filename: string; size: number;
  pii_redacted: Record<string, number>; message: string;
}
export interface StatusResponse {
  file_id: string; status: string; progress: number; message: string; filename?: string;
}
export interface BoundingRect {
  x1: number; y1: number; x2: number; y2: number; width: number; height: number; pageNumber: number;
}
export interface HighlightPosition {
  boundingRect: BoundingRect; rects: BoundingRect[]; pageWidth: number; pageHeight: number;
}
export interface Finding {
  id: string; page: number; quoted_text: string; category: string;
  severity: string; color: string; statute_citation: string | null;
  explanation: string; damages_estimate: number | null; position: HighlightPosition | null;
}
export interface AnalysisResult {
  documentId: string;
  documentMetadata: { parties: { landlord: string; tenant: string; property: string };
    monthlyRent: string; leaseTerm: string; securityDeposit: string };
  deidentificationSummary: { redactedEntities: Record<string, number>; encryptionStatus: string };
  analysisSummary: { overallRisk: string; issuesFound: number; estimatedRecovery: string;
    topIssues: { title: string; severity: string; amount?: string }[] };
  highlights: Finding[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`);
  return res.json();
}

export const api = {
  upload: (file: File) => {
    const fd = new FormData(); fd.append("file", file);
    return req<UploadResponse>("/upload", { method: "POST", body: fd });
  },
  analyze: (file_id: string) =>
    req<{ status: string }>("/analyze", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ file_id }) }),
  status: (file_id: string) => req<StatusResponse>(`/status/${file_id}`),
  document: (file_id: string) => req<AnalysisResult>(`/document/${file_id}`),
  pdfUrl: (file_id: string) => `${BASE_URL}/pdf/${file_id}`,
  warmup: () => fetch(`${BASE_URL}/health`).catch(() => {}),
  demandLetter: (file_id: string, sender: object, recipient: object) =>
    fetch(`${BASE_URL}/demand-letter`, { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_id, sender, recipient }) }),
};
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/api.ts && git commit -m "feat(ui): typed api client mirroring backend models"
```

---

### Task 16: Upload screen

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/UploadCard.tsx`

- [ ] **Step 1: Write `UploadCard.tsx`**

```tsx
"use client";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function UploadCard() {
  const router = useRouter();
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.warmup(); }, []);

  const handle = useCallback(async (file: File) => {
    setError(null);
    if (file.type !== "application/pdf") { setError("Please upload a PDF."); return; }
    if (file.size > 10 * 1024 * 1024) { setError("Max 10MB."); return; }
    setBusy(true);
    try {
      const res = await api.upload(file);
      sessionStorage.setItem("pii", JSON.stringify(res.pii_redacted));
      await api.analyze(res.file_id);
      router.push(`/processing?file_id=${res.file_id}`);
    } catch (e) { setError((e as Error).message); setBusy(false); }
  }, [router]);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false);
        if (e.dataTransfer.files[0]) handle(e.dataTransfer.files[0]); }}
      className={`rounded-3xl border-2 border-dashed p-16 text-center transition
        ${dragging ? "border-[var(--accent)] bg-[var(--surface)]" : "border-[var(--ink-subtle)]/30"}`}
    >
      <p className="text-xl font-medium">{busy ? "Uploading…" : "Drop a lease PDF here"}</p>
      <p className="mt-2 text-[var(--ink-subtle)]">or</p>
      <label className="mt-4 inline-block cursor-pointer rounded-full bg-[var(--accent)] px-6 py-3 text-white">
        Choose file
        <input type="file" accept="application/pdf" hidden
          onChange={(e) => e.target.files?.[0] && handle(e.target.files[0])} />
      </label>
      {error && <p className="mt-4 text-[var(--sev-illegal)]">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Write `page.tsx`**

```tsx
import { UploadCard } from "@/components/UploadCard";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-6">
      <h1 className="mb-2 text-5xl font-semibold tracking-tight">Clause</h1>
      <p className="mb-10 text-lg text-[var(--ink-muted)]">
        Spot illegal and risky clauses in your rental agreement.
      </p>
      <div className="w-full">
        <UploadCard />
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Manual check**

With backend running, drop `old_reference/Clause_frontend-main/public/sample-lease.pdf` → should navigate to `/processing?file_id=...`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/components/UploadCard.tsx
git commit -m "feat(ui): upload screen with drag-drop and warmup"
```

---

### Task 17: Processing screen (polling)

**Files:**
- Create: `frontend/src/app/processing/page.tsx`

- [ ] **Step 1: Write `processing/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

export default function Processing() {
  const params = useSearchParams();
  const router = useRouter();
  const fileId = params.get("file_id")!;
  const [progress, setProgress] = useState(10);
  const [message, setMessage] = useState("Starting analysis…");

  useEffect(() => {
    let active = true;
    const tick = async () => {
      try {
        const s = await api.status(fileId);
        if (!active) return;
        setProgress(s.progress); setMessage(s.message);
        if (s.status === "completed") { router.push(`/results/${fileId}`); return; }
        if (s.status === "failed") { setMessage("Analysis failed."); return; }
      } catch { /* tolerate cold-start blips */ }
      if (active) setTimeout(tick, 1000);
    };
    tick();
    return () => { active = false; };
  }, [fileId, router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center px-6">
      <div className="w-full rounded-3xl bg-[var(--surface)]/70 p-10 backdrop-blur">
        <p className="mb-4 text-center text-lg">{message}</p>
        <div className="h-3 w-full overflow-hidden rounded-full bg-white/60">
          <div className="h-full rounded-full bg-[var(--accent)] transition-all"
               style={{ width: `${progress}%` }} />
        </div>
        <p className="mt-3 text-center text-sm text-[var(--ink-subtle)]">{progress}%</p>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Manual check**

Progress bar animates 10→100 and redirects to `/results/{id}`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/processing/page.tsx
git commit -m "feat(ui): processing screen with status polling"
```

---

### Task 18: Results split view + highlights

**Files:**
- Create: `frontend/src/app/results/[id]/page.tsx`
- Create: `frontend/src/components/ClauseCard.tsx`
- Create: `frontend/src/components/PdfHighlights.tsx`

- [ ] **Step 1: Write `ClauseCard.tsx`**

```tsx
import { Finding } from "@/lib/api";
import { SEVERITY_COLORS } from "@/app/theme";

export function ClauseCard({ f, onClick }: { f: Finding; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="w-full rounded-2xl bg-white/70 p-5 text-left shadow-sm transition hover:shadow-md">
      <div className="flex items-center gap-2">
        <span className="h-3 w-3 rounded-full" style={{ background: SEVERITY_COLORS[f.severity] }} />
        <span className="font-medium">{f.category}</span>
        <span className="ml-auto text-sm capitalize text-[var(--ink-subtle)]">{f.severity}</span>
      </div>
      <p className="mt-2 line-clamp-2 text-sm text-[var(--ink-muted)]">{f.explanation}</p>
      {f.statute_citation && (
        <p className="mt-2 text-xs text-[var(--accent-deep)]">{f.statute_citation}</p>
      )}
    </button>
  );
}
```

- [ ] **Step 2: Write `PdfHighlights.tsx`** (react-pdf-highlighter wrapper)

```tsx
"use client";
import { useMemo } from "react";
import { PdfLoader, PdfHighlighter, Highlight } from "react-pdf-highlighter";
import { Finding } from "@/lib/api";
import { HIGHLIGHT_HEX } from "@/app/theme";

export function PdfHighlights({ url, findings, scrollToId }:
  { url: string; findings: Finding[]; scrollToId: string | null }) {
  const highlights = useMemo(() => findings.filter(f => f.position).map(f => ({
    id: f.id,
    position: {
      boundingRect: f.position!.boundingRect,
      rects: f.position!.rects,
      pageNumber: f.position!.boundingRect.pageNumber,
    },
    content: { text: f.quoted_text },
    comment: { text: f.category, emoji: "" },
    color: f.color,
  })), [findings]);

  return (
    <div className="relative h-[80vh] overflow-auto rounded-2xl bg-white">
      <PdfLoader url={url} beforeLoad={<p className="p-6">Loading PDF…</p>}>
        {(pdfDocument) => (
          <PdfHighlighter
            pdfDocument={pdfDocument}
            enableAreaSelection={() => false}
            scrollRef={() => {}}
            onScrollChange={() => {}}
            highlightTransform={(h) => (
              <div key={h.id}>
                <Highlight position={h.position}
                  comment={h.comment}
                  // @ts-expect-error color passthrough for tinting
                  style={{ background: HIGHLIGHT_HEX[(h as any).color] || "#E4B62C", opacity: 0.4 }} />
              </div>
            )}
            highlights={highlights as any}
          />
        )}
      </PdfLoader>
    </div>
  );
}
```

Note: `react-pdf-highlighter` requires the pdf.js worker. If the PDF fails to load, set the worker in a client-only module: `import { pdfjs } from "react-pdf-highlighter";` is not exported — instead import `pdfjs-dist` worker via `GlobalWorkerOptions` in a `useEffect`. Verify against the library version installed and adjust in this step.

- [ ] **Step 3: Write `results/[id]/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, AnalysisResult } from "@/lib/api";
import { ClauseCard } from "@/components/ClauseCard";
import { PdfHighlights } from "@/components/PdfHighlights";
import { DemandLetterModal } from "@/components/DemandLetterModal";

export default function Results() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [scrollToId, setScrollToId] = useState<string | null>(null);
  const [letterOpen, setLetterOpen] = useState(false);

  useEffect(() => { api.document(id).then(setData).catch(console.error); }, [id]);
  if (!data) return <main className="p-10">Loading results…</main>;

  const s = data.analysisSummary;
  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-6 flex flex-wrap items-center gap-6 rounded-3xl bg-[var(--surface)]/70 p-6 backdrop-blur">
        <Stat label="Overall risk" value={s.overallRisk} />
        <Stat label="Issues found" value={String(s.issuesFound)} />
        <Stat label="Est. recovery" value={s.estimatedRecovery} />
        <button onClick={() => setLetterOpen(true)}
          className="ml-auto rounded-full bg-[var(--accent)] px-6 py-3 text-white">
          Generate demand letter
        </button>
      </header>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
        <PdfHighlights url={api.pdfUrl(id)} findings={data.highlights} scrollToId={scrollToId} />
        <div className="flex flex-col gap-3">
          {data.highlights.map((f) => (
            <ClauseCard key={f.id} f={f} onClick={() => setScrollToId(f.id)} />
          ))}
        </div>
      </div>
      {letterOpen && <DemandLetterModal fileId={id} onClose={() => setLetterOpen(false)} />}
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-[var(--ink-subtle)]">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  );
}
```

- [ ] **Step 4: Manual check**

Results page shows summary header, PDF with colored highlights, and clause cards. (Demand-letter modal comes in Task 19.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/results frontend/src/components/ClauseCard.tsx frontend/src/components/PdfHighlights.tsx
git commit -m "feat(ui): results split view with pdf highlights and clause cards"
```

---

### Task 19: Demand-letter modal

**Files:**
- Create: `frontend/src/components/DemandLetterModal.tsx`

- [ ] **Step 1: Write `DemandLetterModal.tsx`**

```tsx
"use client";
import { useState } from "react";
import { api } from "@/lib/api";

export function DemandLetterModal({ fileId, onClose }: { fileId: string; onClose: () => void }) {
  const [sender, setSender] = useState({ name: "", address: "" });
  const [recipient, setRecipient] = useState({ name: "", address: "" });
  const [busy, setBusy] = useState(false);

  const generate = async () => {
    setBusy(true);
    try {
      const res = await api.demandLetter(fileId, sender, recipient);
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "demand-letter.pdf";
      link.click();
      URL.revokeObjectURL(link.href);
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-md rounded-3xl bg-[var(--canvas)] p-8 shadow-xl">
        <h2 className="mb-4 text-xl font-semibold">Generate demand letter</h2>
        {[["Your name", sender.name, (v: string) => setSender({ ...sender, name: v })],
          ["Your address", sender.address, (v: string) => setSender({ ...sender, address: v })],
          ["Landlord name", recipient.name, (v: string) => setRecipient({ ...recipient, name: v })],
          ["Landlord address", recipient.address, (v: string) => setRecipient({ ...recipient, address: v })],
        ].map(([label, value, set]: any) => (
          <input key={label} placeholder={label} value={value}
            onChange={(e) => set(e.target.value)}
            className="mb-3 w-full rounded-xl border border-[var(--ink-subtle)]/30 bg-white px-4 py-2" />
        ))}
        <div className="mt-4 flex gap-3">
          <button onClick={onClose} className="flex-1 rounded-full border px-4 py-2">Cancel</button>
          <button onClick={generate} disabled={busy}
            className="flex-1 rounded-full bg-[var(--accent)] px-4 py-2 text-white">
            {busy ? "Generating…" : "Download PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Manual check**

Click "Generate demand letter" → fill fields → downloads a PDF built from the analysis.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/DemandLetterModal.tsx
git commit -m "feat(ui): demand-letter modal with pdf download"
```

---

## Phase 6 — Deploy

### Task 20: Backend Dockerfile + Render config

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/render.yaml`

- [ ] **Step 1: Write `Dockerfile`** (WeasyPrint + PyMuPDF system deps)

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev libcairo2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV VECTOR_BACKEND=local
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write `render.yaml`**

```yaml
services:
  - type: web
    name: clause-backend
    runtime: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    plan: free
    healthCheckPath: /health
    envVars:
      - key: GEMINI_API_KEY
        sync: false
      - key: VECTOR_BACKEND
        value: local
      - key: ALLOWED_ORIGINS
        sync: false
```

- [ ] **Step 3: Build image locally to verify**

Run: `cd backend && docker build -t clause-backend .`
Expected: image builds; `docker run -e GEMINI_API_KEY=x -p 8000:8000 clause-backend` serves `/health`.

- [ ] **Step 4: Commit**

```bash
git add backend/Dockerfile backend/render.yaml
git commit -m "chore: backend dockerfile and render config"
```

---

### Task 21: Frontend Vercel config + deploy wiring

**Files:**
- Create: `frontend/vercel.json`
- Modify: `frontend/next.config.ts` (allow pdf worker)

- [ ] **Step 1: Write `vercel.json`**

```json
{ "framework": "nextjs" }
```

- [ ] **Step 2: Ensure pdf.js worker resolves**

In a client component (e.g. top of `PdfHighlights.tsx`), set the worker in `useEffect`:

```tsx
import { GlobalWorkerOptions, version } from "pdfjs-dist";
// inside useEffect:
GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${version}/build/pdf.worker.min.mjs`;
```

Adjust to the installed `pdfjs-dist` version. Verify the PDF renders in production build (`npm run build && npm start`).

- [ ] **Step 3: Deploy backend to Render**

Push repo to GitHub; create a Render Web Service from `render.yaml`; set `GEMINI_API_KEY` and `ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app`. Note the Render URL.

- [ ] **Step 4: Deploy frontend to Vercel**

Import `frontend/` in Vercel; set `NEXT_PUBLIC_API_URL=https://<render-url>`. Deploy.

- [ ] **Step 5: End-to-end smoke test**

Upload `sample-lease.pdf` on the live site → progress → results with highlights → download demand letter. Confirm no CORS errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/vercel.json frontend/next.config.ts
git commit -m "chore: vercel config and pdf worker wiring"
```

---

### Task 22: Switch to Snowflake (optional, when credits available)

**Files:**
- Create: `backend/snowflake_setup.sql`

- [ ] **Step 1: Write `snowflake_setup.sql`**

```sql
CREATE WAREHOUSE IF NOT EXISTS CLAUSE_WH WAREHOUSE_SIZE = XSMALL AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
CREATE DATABASE IF NOT EXISTS CLAUSE_DB;
CREATE SCHEMA IF NOT EXISTS CLAUSE_DB.PUBLIC;
CREATE TABLE IF NOT EXISTS CLAUSE_DB.PUBLIC.STATUTES (
  id STRING, chapter STRING, section STRING, title STRING, text STRING,
  embedding VECTOR(FLOAT, 768)
);
```

- [ ] **Step 2: Seed Snowflake**

Run locally with Snowflake env vars set:
```bash
cd backend && source .venv/bin/activate && VECTOR_BACKEND=snowflake python -m app.seed_statutes
```
Expected: "Seeded N statutes into snowflake store."

- [ ] **Step 3: Flip Render env**

Set `VECTOR_BACKEND=snowflake` + `SNOWFLAKE_*` env vars on Render; redeploy. Re-run the smoke test.

- [ ] **Step 4: Commit**

```bash
git add backend/snowflake_setup.sql
git commit -m "chore: snowflake schema and seed path"
```

---

## Self-review notes (coverage vs spec)

- Hero flow (upload→highlight→list→letter): Tasks 11, 16–19. ✅
- Snowflake vectors + swappable local fallback: Tasks 4, 5, 13, 22. ✅
- Gemini Flash + embeddings: Tasks 6, 10. ✅
- Ephemeral/no-auth: in-memory `state.py`, `/tmp` PDFs (Task 11). ✅
- PII redaction kept: Task 3, wired in `/upload`. ✅
- Exact-overlay highlighting via `search_for` + graceful degradation: Tasks 2, 7, 18. ✅
- HTML→PDF demand letter (WeasyPrint): Tasks 9, 11, 19. ✅
- Fresh minimal Next.js on Vercel: Tasks 0.2, 14–21. ✅
- Warm palette, no assistant name/logo, gooey/beautifului inspiration: Task 14 + `frontend-design` skill. ✅
- MA-only corpus: Task 12. ✅
- Render free + cold-start handling (warmup, resilient polling): Tasks 16, 17, 20. ✅

**Deferred / tune during build:** exact statute list expansion (Task 12 starter set), chunking size (Task 8, `_chunk` default 3000), metadata-confirm step is currently auto-run inside upload flow rather than a separate screen — add a `/review` screen later if desired (spec §12 marks it skippable; the demo path skips straight to analysis).
