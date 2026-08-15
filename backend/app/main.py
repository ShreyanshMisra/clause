import os, uuid
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env before any module reads env (VECTOR_BACKEND, GEMINI_API_KEY, etc.).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional
import re
import app.state as state
import app.db as db
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

def _build_services():
    """Build the generation LLM (Gemini) and the retrieval embedder
    (Cortex in snowflake mode, Gemini in local mode)."""
    from app.gemini_client import GeminiClient
    from app.llm_service import LLMService
    from app.vector_store import get_embedder
    llm = LLMService(GeminiClient.from_env())
    embedder = get_embedder()
    return llm, embedder

@app.on_event("startup")
def _init_db():
    db.init()

@app.on_event("startup")
def _init_llm():
    if state.llm is None:
        try:
            state.llm, state.embedder = _build_services()
        except Exception as exc:
            import logging
            logging.warning("Service init failed at startup: %s — will retry on first request", exc)
            return
    try:
        from app.bootstrap import seed_local_if_needed
        seed_local_if_needed(state.vector_store, state.embedder)
        state.seeded = True
    except Exception as exc:
        import logging
        logging.warning("Statute seeding failed at startup: %s — will retry on first analysis", exc)

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Accounts ───────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _norm_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    email = email.strip().lower()
    return email if _EMAIL_RE.match(email) else None

class LoginBody(BaseModel):
    email: str

@app.post("/login")
def login(body: LoginBody):
    """Password-less accounts: the email is the username. Upsert and return it."""
    email = _norm_email(body.email)
    if email is None:
        raise HTTPException(400, "Enter a valid email address")
    db.upsert_user(email)
    return {"email": email}

@app.get("/cases")
def cases(x_user_email: Optional[str] = Header(default=None)):
    email = _norm_email(x_user_email)
    if email is None:
        raise HTTPException(401, "Sign in to view your cases")
    return {"cases": db.list_cases(email)}

def _authorize_case(file_id: str, x_user_email: Optional[str]) -> None:
    """Guard case-scoped endpoints against IDOR. A case that has an owner may
    only be accessed with the matching X-User-Email; ownerless (guest/demo)
    cases are public. We 404 on mismatch so we never confirm that another
    user's file_id exists. (The email header is spoofable by design in this
    password-less model — this is defence-in-depth plus enumeration
    protection, layered on top of the unguessable uuid4 file_id.)"""
    case = db.get_case(file_id)
    if case is None:
        return  # unknown to the DB; the endpoint's own 404 handling applies
    owner = case.get("user_email")
    if owner is not None and _norm_email(x_user_email) != owner:
        raise HTTPException(404, "Unknown file_id")

@app.post("/upload")
async def upload(file: UploadFile = File(...),
                 x_user_email: Optional[str] = Header(default=None)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(400, "File exceeds 10MB")
    file_id = uuid.uuid4().hex
    path = state.pdf_path(file_id)
    with open(path, "wb") as f:
        f.write(data)
    pages = extract_pages(path)
    if len(pages) > 20:
        os.unlink(path)
        raise HTTPException(400, "Document exceeds 20 pages for this demo")
    page_redactions = [redact(p.text) for p in pages]
    state.redacted_pages[file_id] = [r.redacted_text for r in page_redactions]
    state.redacted_text[file_id] = "\n".join(r.redacted_text for r in page_redactions)
    summary: dict[str, int] = {}
    for r in page_redactions:
        for k, v in r.summary.items():
            summary[k] = summary.get(k, 0) + v
    state.registry.create(file_id, filename=file.filename)
    email = _norm_email(x_user_email)
    if email is not None:
        db.upsert_user(email)
    db.create_case(file_id, email, file.filename or "lease.pdf", path)
    return {"file_id": file_id, "filename": file.filename, "size": len(data),
            "pii_redacted": summary,
            "message": f"Protected {sum(summary.values())} pieces of personal information"}

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
    if state.llm is None:
        state.llm, state.embedder = _build_services()
    if not state.seeded:
        from app.bootstrap import seed_local_if_needed
        seed_local_if_needed(state.vector_store, state.embedder)
        state.seeded = True
    try:
        result = analyze_document(file_id, state.pdf_path(file_id),
                                  state.redacted_pages.get(file_id, []),
                                  state.llm, state.embedder, state.vector_store, state.registry)
    except Exception:
        # Registry already marked failed; persist it so the dashboard card
        # doesn't show a perpetual "Analysing…" for this case.
        db.set_status(file_id, "failed")
        raise
    md = state.metadata_store.get(file_id)
    if md is not None:
        result.documentMetadata = md
    state.results[file_id] = result
    db.save_result(file_id, result.model_dump())

@app.post("/analyze")
def analyze(body: FileIdBody, background: BackgroundTasks):
    if body.file_id not in state.redacted_text:
        raise HTTPException(404, "Unknown file_id")
    state.registry.update(body.file_id, status="processing", progress=10, message="Starting analysis...")
    background.add_task(_run_analysis, body.file_id)
    return {"file_id": body.file_id, "status": "processing"}

@app.get("/status/{file_id}")
def status(file_id: str, x_user_email: Optional[str] = Header(default=None)):
    _authorize_case(file_id, x_user_email)
    job = state.registry.get(file_id)
    if job is not None:
        return job.model_dump()
    # Re-opened case after a restart: derive status from the persisted row.
    case = db.get_case(file_id)
    if case is None:
        raise HTTPException(404, "Unknown file_id")
    completed = case["status"] == "completed"
    return {"file_id": file_id, "status": case["status"],
            "progress": 100 if completed else 0,
            "message": "Completed" if completed else case["status"],
            "filename": case["filename"]}

@app.get("/document/{file_id}")
def document(file_id: str, x_user_email: Optional[str] = Header(default=None)):
    _authorize_case(file_id, x_user_email)
    result = state.results.get(file_id)
    if result is not None:
        return result.model_dump()
    stored = db.get_result(file_id)  # persisted case
    if stored is not None:
        return stored
    raise HTTPException(404, "Analysis not ready")

@app.get("/pdf/{file_id}")
def pdf(file_id: str, x_user_email: Optional[str] = Header(default=None)):
    _authorize_case(file_id, x_user_email)
    path = state.pdf_path(file_id)
    if not os.path.exists(path):
        raise HTTPException(404, "PDF not found")
    return FileResponse(path, media_type="application/pdf")

class DemandLetterBody(BaseModel):
    file_id: str
    sender: dict = {}
    recipient: dict = {}

@app.post("/demand-letter")
def demand_letter(body: DemandLetterBody, x_user_email: Optional[str] = Header(default=None)):
    _authorize_case(body.file_id, x_user_email)
    result = state.results.get(body.file_id)
    if result is None:
        stored = db.get_result(body.file_id)  # persisted case
        if stored is None:
            raise HTTPException(404, "Analysis not ready")
        from app.models import AnalysisResult
        result = AnalysisResult(**stored)
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
