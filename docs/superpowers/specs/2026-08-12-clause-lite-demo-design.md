# Clause Lite — Design Spec

**Date:** 2026-08-12
**Status:** Approved design → ready for implementation planning
**Working directory:** `/Users/shreyansh/Desktop/clause` (build here; `old_reference/` is read-only reference, deleted at the very end)

---

## 1. Purpose

Clause Lite is a cheap-to-host demo of an AI contract-analysis tool for **residential rental agreements**. A user uploads a lease PDF; the app detects illegal / risky clauses by semantically searching them against Massachusetts landlord-tenant statutes (RAG), returns severity-scored findings with citations and an exact-overlay highlighted PDF, and can generate a downloadable demand letter.

It is a rebuild of an older, heavier version (see `old_reference/`) — trimmed to the impressive core and re-architected for near-zero hosting cost.

### Non-goals (explicitly cut from the old version)
- No auth / user accounts / per-user history.
- No chat interface.
- No cases list, notifications, dashboard analytics, calendar, or admin template.
- No persistence of user documents (ephemeral only). The **only** persisted data is the statute corpus.
- No LaTeX toolchain.

---

## 2. Locked decisions

| Area | Decision |
|------|----------|
| Hero flow | Upload PDF → exact-overlay highlighted results + flagged-clause list → HTML→PDF demand letter. No chat. |
| Vector store | Snowflake as a **pure vector store**, behind a swappable interface with a local fallback. Trial credits, XS warehouse, auto-suspend. |
| LLM | **Gemini Flash** for metadata extraction + clause analysis + demand-letter drafting. |
| Embeddings | Gemini embeddings (external), vectors stored in Snowflake `VECTOR` column. |
| Persistence / auth | **Ephemeral, no auth.** |
| PII redaction | **Keep** a simple version (regex + light NER) before the LLM sees the document. |
| PDF highlighting | **Exact overlay** on the original PDF via `react-pdf-highlighter`, coordinates resolved server-side with PyMuPDF `search_for`. |
| Demand letter | LLM fills an HTML template → **WeasyPrint → PDF** download. |
| Frontend | **Fresh minimal Next.js** (App Router), deployed on **Vercel** (Hobby, free). |
| Backend | **FastAPI** on **Render** (free tier), designed around cold starts. |
| Corpus | **Massachusetts landlord-tenant law only.** |

---

## 3. Branding & design direction

Clause is a play on words — a "clause" in a contract, and a nod to the assistant family the name rhymes with. **Never mention that assistant by name and never use its logo.** We only borrow a warm, friendly palette that evokes it.

**Palette (starting point — warm coral + cream + slate):**
- Background / canvas: warm ivory `#FAF9F5`, secondary surface `#F0EEE6`
- Primary accent (coral / terracotta): `#D97757`, deep variant `#CC785C`
- Ink / text: near-black slate `#141413`, muted `#3D3D3A`, subtle `#6B6B63`
- Severity colors (findings): illegal `#E5484D` (red), high `#E8833A` (orange), medium `#E4B62C` (amber), favorable `#3FA372` (green)

**Aesthetic:** phenomenal, modern, tactile. Inspiration: https://gooey.jakubantalik.com/ (soft "gooey"/glassy depth, blurred gradient blobs, rounded geometry, playful but refined motion) and https://www.beautifului.dev/ (crisp, curated component polish).
Concretely: generous whitespace, soft shadows and layered surfaces, rounded corners, a subtle animated warm gradient/blob backdrop, smooth micro-interactions and transitions, tasteful typography. Avoid generic AI-dashboard aesthetics. The `frontend-design` skill should drive the UI build.

---

## 4. Architecture

Two deployables:

```
┌─────────────────────────┐         ┌──────────────────────────────────────┐
│  Next.js (Vercel)        │  HTTPS  │  FastAPI (Render free tier)          │
│  - Upload UI             │◄───────►│  /upload /extract-metadata /analyze  │
│  - Progress (polling)    │  JSON   │  /status /document /pdf /demand-letter│
│  - PDF + highlights      │         │                                      │
│  - Demand-letter modal   │         │  PyMuPDF · Gemini · WeasyPrint · PII  │
└─────────────────────────┘         └──────────────────┬───────────────────┘
                                                        │ embed + vector search
                                               ┌────────▼─────────┐
                                               │  VectorStore iface│
                                               │  Snowflake (VECTOR)│ ← default
                                               │  Local (numpy/sqlite)│ ← fallback
                                               └───────────────────┘
```

- Frontend talks to backend via `NEXT_PUBLIC_API_URL`.
- Backend job state is an **in-memory dict keyed by `file_id`**; uploaded PDFs live in `/tmp/{file_id}.pdf`. Ephemeral by design.
- **Documented limitation:** on Render free, the instance sleeps after ~15 min idle and in-flight jobs are lost. Mitigated because analysis is short (target < 60s for the sample lease) and the client polls continuously, keeping the instance awake during a run. A warm-up ping on the upload screen masks the initial cold start.

---

## 5. Components (each with one clear purpose)

### Backend (`/backend`, Python 3.11, FastAPI)

| Module | Responsibility |
|--------|----------------|
| `main.py` / `api.py` | FastAPI app, routes, CORS, in-memory job registry. |
| `pdf_service.py` | PyMuPDF: extract per-page text + word bounding boxes; `search_for(text, page)` → rects; serve original PDF. |
| `pii_service.py` | Redact names/addresses/emails/phones (regex + light NER) on a copy of the text; return redaction summary counts. Keeps original text untouched for coordinate mapping. |
| `llm_service.py` | Gemini wrappers: `extract_metadata()`, `analyze_chunk(chunk, statutes)`, `draft_demand_letter(findings, parties)`, `embed(text)`. Structured JSON output + validation. |
| `vector_store.py` | `VectorStore` interface (`seed()`, `search(embedding, k)`); `SnowflakeVectorStore` + `LocalVectorStore`; selected by `VECTOR_BACKEND`. |
| `analysis.py` | Orchestrates the analyze pipeline: chunk → embed → retrieve → analyze → consolidate → map coordinates → aggregate. Emits progress into the job registry. |
| `highlight.py` | Convert PyMuPDF rects → `react-pdf-highlighter` position format; severity → color; graceful degradation when text isn't found. |
| `letter_service.py` | Fill HTML template with letter body + parties → WeasyPrint → PDF bytes. |
| `models.py` | Pydantic schemas mirroring the frontend TS types (subset of old `AnalysisData`). |
| `seed_statutes.py` | One-time script: read curated MA statute corpus → embed → insert into the vector store. |

### Frontend (`/frontend`, Next.js App Router, TS, Tailwind)

| Screen / module | Responsibility |
|-----------------|----------------|
| `/` Upload | Drag/drop PDF, client validation, `POST /upload`, show PII summary, warm-up ping. |
| `/processing` | Progress bar polling `GET /status/{id}`; contextual messages. |
| Metadata confirm (skippable) | Editable form pre-filled from `/extract-metadata`; "Skip & analyze". |
| `/results/{id}` | Split view: `react-pdf-highlighter` (PDF from `/pdf/{id}` + colored highlights) on the left; clause cards on the right; summary header (overall risk, issue count, estimated recovery). |
| Demand-letter modal | Sender/recipient form → `POST /demand-letter` → preview + download PDF. |
| `lib/api.ts` | Typed fetch client (retry/timeout/error class), mirrored from old design. |
| Design system | Palette tokens, gradient-blob backdrop, shared UI primitives. |

---

## 6. Data flow

1. **Upload:** PDF → PyMuPDF extracts text + word boxes → PII redaction produces LLM-safe copy → `file_id` + redaction summary returned.
2. **Metadata (optional):** Gemini reads redacted text → parties/rent/term/deposit → user confirms/edits.
3. **Analyze (background):** chunk redacted text → Gemini embed each chunk → Snowflake top-k statute retrieval → Gemini judges chunk against statutes → findings JSON. For each finding, PyMuPDF `search_for` resolves rects on the cited page → highlight objects. Consolidate/dedupe → aggregates. Progress written to job registry throughout.
4. **Status polling:** `{status, progress, message}` until `completed`.
5. **Results:** `GET /document/{id}` (analysis JSON) + `GET /pdf/{id}` (PDF) → rendered split view.
6. **Demand letter:** findings + parties → Gemini draft → HTML template → WeasyPrint PDF → download.

**Finding shape (per clause):** `{ id, page, quoted_text, category, severity, color, statute_citation, explanation, damages_estimate, position }`.

---

## 7. Snowflake schema

```
STATUTES (
  id STRING,
  chapter STRING,
  section STRING,
  title STRING,
  text STRING,
  embedding VECTOR(FLOAT, 768)   -- dim per Gemini embedding model
)
```
Retrieval: `ORDER BY VECTOR_COSINE_SIMILARITY(embedding, ?) DESC LIMIT k`. Warehouse XS, auto-suspend ~60s. `LocalVectorStore` mirrors the same interface using numpy cosine over a small pickled/sqlite corpus for the free fallback.

---

## 8. Error handling & resilience

- Backend: validate uploads (type, size, page cap); typed error responses; guard every Gemini call (retry + timeout) and fall back to a partial result rather than a hard failure.
- **Coordinate mapping:** if `search_for` returns nothing (LLM paraphrased, or text spans a line break), retry with normalized whitespace / shorter anchor substring; final fallback = page-level highlight + list entry so a finding is never dropped.
- Frontend: retry/timeout in the API client; friendly toasts; resilient polling that survives a cold-start blip.
- Vector store: if Snowflake is unreachable, log and (optionally, via env) fall back to `LocalVectorStore`.

---

## 9. Testing

- Golden test on `old_reference/.../public/sample-lease.pdf`: run the full pipeline, assert findings are produced and each has resolvable coordinates (or a documented degradation).
- Unit tests: PII redaction counts + original text preserved; `highlight.py` rect→position conversion; `VectorStore` interface parity between Snowflake and Local; metadata JSON parsing.
- Manual: full upload→results→letter flow against deployed Vercel + Render.

---

## 10. Cost controls

- Vercel Hobby (free), Render free, Gemini Flash free tier, Snowflake trial credits.
- Page cap (~15) and chunk cap bound LLM/embedding calls per document.
- Snowflake XS + auto-suspend; `VECTOR_BACKEND=local` escape hatch if credits run out.
- Warm-up ping to mask cold starts.

---

## 11. Deployment

- **Frontend → Vercel:** connect repo `frontend/`, set `NEXT_PUBLIC_API_URL` to the Render URL.
- **Backend → Render:** Dockerfile (PyMuPDF + WeasyPrint system deps), env vars: `GEMINI_API_KEY`, `VECTOR_BACKEND`, `SNOWFLAKE_*`, `ALLOWED_ORIGINS`. Health check + warm-up route.
- **Seed step:** run `seed_statutes.py` once against Snowflake before first demo.

---

## 12. Open items to resolve during planning
- Exact MA statute list to seed (source + sectioning granularity).
- Chunking strategy (per-page vs fixed-token) — tune for the sample lease.
- Whether metadata-confirm is on by default or hidden behind a toggle for the demo.
