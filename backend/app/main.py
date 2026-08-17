import os, uuid
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env before any module reads env (VECTOR_BACKEND, GEMINI_API_KEY, etc.).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional
import re
import app.state as state
import app.db as db
from app import security
from app.pdf_service import extract_pages
from app.pii_service import redact
from app.analysis import analyze_document
from app.letter_service import render_letter_pdf
from app.ratelimit import SlidingWindowLimiter


def _build_services():
    """Build the generation LLM (Gemini) and the retrieval embedder
    (Cortex in snowflake mode, Gemini in local mode)."""
    from app.gemini_client import GeminiClient
    from app.llm_service import LLMService
    from app.vector_store import get_embedder
    llm = LLMService(GeminiClient.from_env())
    embedder = get_embedder()
    return llm, embedder


def _llm():
    """Return the generation LLM, building it lazily if startup init was skipped
    (e.g. the model/key wasn't ready at boot). Guarantees a non-None service."""
    if state.llm is None:
        state.llm, state.embedder = _build_services()
    return state.llm


def _init_services() -> None:
    """Build the LLM/embedder and seed statutes; tolerate failures so the app
    still boots and retries lazily on the first request."""
    import logging
    if state.llm is None:
        try:
            state.llm, state.embedder = _build_services()
        except Exception as exc:
            logging.warning("Service init failed at startup: %s — will retry on first request", exc)
            return
    try:
        from app.bootstrap import seed_local_if_needed
        seed_local_if_needed(state.vector_store, state.embedder)
        state.seeded = True
    except Exception as exc:
        logging.warning("Statute seeding failed at startup: %s — will retry on first analysis", exc)
    # Warm the spaCy/Presidio NER model now so the first upload doesn't eat the
    # multi-second model load. Best-effort: redaction falls back to regex if absent.
    try:
        from app.pii_service import _get_ner
        _get_ner()
    except Exception as exc:
        logging.warning("NER warmup skipped: %s", exc)
    # Optional second PII layer on the fast model (see app.pii_llm). Off unless
    # PII_LLM_ASSIST is set; tolerate a missing key so the app still boots.
    if os.environ.get("PII_LLM_ASSIST", "").lower() in ("1", "true", "yes", "on"):
        try:
            from app.gemini_client import GeminiClient
            from app.pii_service import set_pii_client
            set_pii_client(GeminiClient.fast_from_env())
        except Exception as exc:
            logging.warning("PII LLM assist unavailable: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    _init_services()
    yield


app = FastAPI(title="Clause Lite", lifespan=lifespan)
# Auth is a Bearer token (not a cookie), so credentials aren't needed; keeping
# them off lets us pin an explicit origin list and a minimal method/header set.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in
                   os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
                   if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Accounts ───────────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Brute-force guards: lock a targeted account after a few bad passwords, and cap
# failures from a single IP to blunt credential spraying. Both count *failures*
# only (a successful login clears them), so ordinary use never trips them.
_LOGIN_WINDOW = float(os.environ.get("LOGIN_LOCKOUT_WINDOW", 15 * 60))
_email_throttle = SlidingWindowLimiter(
    max_events=int(os.environ.get("LOGIN_MAX_FAILS_PER_EMAIL", 5)), window_seconds=_LOGIN_WINDOW)
_ip_throttle = SlidingWindowLimiter(
    max_events=int(os.environ.get("LOGIN_MAX_FAILS_PER_IP", 20)), window_seconds=_LOGIN_WINDOW)

def _norm_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    email = email.strip().lower()
    return email if _EMAIL_RE.match(email) else None

class LoginBody(BaseModel):
    email: str
    password: str

def _throttle_guard(email: str, ip: str) -> None:
    """Reject the request early if this account or IP is currently locked out."""
    for key, limiter in ((email, _email_throttle), (ip, _ip_throttle)):
        wait = limiter.retry_after(key)
        if wait > 0:
            raise HTTPException(429, "Too many failed attempts. Try again later.",
                                headers={"Retry-After": str(int(wait) + 1)})


# Abuse/cost guard for the expensive routes. Unlike login (which counts only
# failures), these count *every* call per client IP, because each upload burns
# disk and each analyze/metadata/letter call spends real LLM budget — so an
# anonymous loop could otherwise drain the quota. Limits are generous enough for
# ordinary interactive use and configurable via env for tuning per deploy.
_COST_WINDOW = float(os.environ.get("COST_RATE_WINDOW", 60 * 60))
_upload_throttle = SlidingWindowLimiter(
    max_events=int(os.environ.get("UPLOAD_MAX_PER_WINDOW", 50)), window_seconds=_COST_WINDOW)
_analyze_throttle = SlidingWindowLimiter(
    max_events=int(os.environ.get("ANALYZE_MAX_PER_WINDOW", 50)), window_seconds=_COST_WINDOW)
_letter_throttle = SlidingWindowLimiter(
    max_events=int(os.environ.get("LETTER_MAX_PER_WINDOW", 30)), window_seconds=_COST_WINDOW)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _cost_guard(limiter: SlidingWindowLimiter, ip: str, what: str) -> None:
    """Reject and record one call against a per-IP budget for an expensive route."""
    wait = limiter.retry_after(ip)
    if wait > 0:
        raise HTTPException(429, f"Too many {what}. Try again later.",
                            headers={"Retry-After": str(int(wait) + 1)})
    limiter.record(ip)


@app.post("/login")
def login(body: LoginBody, request: Request):
    """Email + password accounts. The first login for an email registers it;
    subsequent logins verify the password. Returns a signed session token that
    later requests present as `Authorization: Bearer <token>`."""
    email = _norm_email(body.email)
    if email is None:
        raise HTTPException(400, "Enter a valid email address")
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    ip = request.client.host if request.client else "unknown"
    _throttle_guard(email, ip)
    user = db.get_user(email)
    if user is None:
        db.create_user(email, security.hash_password(body.password))  # register
    elif not user.get("password_hash") or not security.verify_password(
        body.password, user["password_hash"]
    ):
        _email_throttle.record(email)
        _ip_throttle.record(ip)
        raise HTTPException(401, "Incorrect password")
    # Clean login: forgive earlier stray failures for this account/IP.
    _email_throttle.reset(email)
    _ip_throttle.reset(ip)
    return {"email": email, "token": security.sign_token(email)}

@app.get("/cases")
def cases(authorization: Optional[str] = Header(default=None)):
    email = security.email_from_token(authorization)
    if email is None:
        raise HTTPException(401, "Sign in to view your cases")
    return {"cases": db.list_cases(email)}

def _authorize_case(file_id: str, authorization: Optional[str]) -> None:
    """Guard case-scoped endpoints against IDOR. A case that has an owner may
    only be accessed by that owner (proven by a valid Bearer token); ownerless
    (guest/demo) cases are public. We 404 on mismatch so we never confirm that
    another user's file_id exists."""
    case = db.get_case(file_id)
    if case is None:
        return  # unknown to the DB; the endpoint's own 404 handling applies
    owner = case.get("user_email")
    if owner is not None and security.email_from_token(authorization) != owner:
        raise HTTPException(404, "Unknown file_id")

@app.post("/upload")
async def upload(request: Request, file: UploadFile = File(...),
                 authorization: Optional[str] = Header(default=None)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")
    _cost_guard(_upload_throttle, _client_ip(request), "uploads")
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
    state.redaction_spans[file_id] = [r.spans for r in page_redactions]
    state.redacted_text[file_id] = "\n".join(r.redacted_text for r in page_redactions)
    summary: dict[str, int] = {}
    for r in page_redactions:
        for k, v in r.summary.items():
            summary[k] = summary.get(k, 0) + v
    filename = file.filename or "lease.pdf"
    state.registry.create(file_id, filename=filename)
    email = security.email_from_token(authorization)  # None for guest uploads
    db.create_case(file_id, email, filename, path)
    return {"file_id": file_id, "filename": file.filename, "size": len(data),
            "pii_redacted": summary,
            "message": f"Protected {sum(summary.values())} pieces of personal information"}

class FileIdBody(BaseModel):
    file_id: str

@app.post("/extract-metadata")
def extract_metadata(body: FileIdBody, request: Request,
                     authorization: Optional[str] = Header(default=None)):
    _authorize_case(body.file_id, authorization)
    _cost_guard(_analyze_throttle, _client_ip(request), "requests")
    text = state.redacted_text.get(body.file_id)
    if text is None:
        raise HTTPException(404, "Unknown file_id")
    md = _llm().extract_metadata(text)
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
    # Ensure metadata exists — it feeds the statutory damages calculator and the
    # demand letter. If the UI didn't call /extract-metadata, derive it inline.
    md = state.metadata_store.get(file_id)
    if md is None:
        text = state.redacted_text.get(file_id)
        if text:
            try:
                md = state.llm.extract_metadata(text)
                state.metadata_store[file_id] = md
            except Exception:
                md = None
    try:
        result = analyze_document(file_id, state.pdf_path(file_id),
                                  state.redacted_pages.get(file_id, []),
                                  state.llm, state.embedder, state.vector_store, state.registry,
                                  metadata=md,
                                  redaction_spans=state.redaction_spans.get(file_id))
    except Exception:
        # Registry already marked failed; persist it so the dashboard card
        # doesn't show a perpetual "Analysing…" for this case.
        db.set_status(file_id, "failed")
        raise
    if md is not None:
        result.documentMetadata = md
    state.results[file_id] = result
    db.save_result(file_id, result.model_dump())

@app.post("/analyze")
def analyze(body: FileIdBody, background: BackgroundTasks, request: Request,
            authorization: Optional[str] = Header(default=None)):
    _authorize_case(body.file_id, authorization)
    _cost_guard(_analyze_throttle, _client_ip(request), "analysis requests")
    if body.file_id not in state.redacted_text:
        raise HTTPException(404, "Unknown file_id")
    state.registry.update(body.file_id, status="processing", progress=10, message="Starting analysis...")
    background.add_task(_run_analysis, body.file_id)
    return {"file_id": body.file_id, "status": "processing"}

@app.get("/status/{file_id}")
def status(file_id: str, authorization: Optional[str] = Header(default=None)):
    _authorize_case(file_id, authorization)
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
def document(file_id: str, authorization: Optional[str] = Header(default=None)):
    _authorize_case(file_id, authorization)
    result = state.results.get(file_id)
    if result is not None:
        return result.model_dump()
    stored = db.get_result(file_id)  # persisted case
    if stored is not None:
        return stored
    raise HTTPException(404, "Analysis not ready")

@app.get("/pdf/{file_id}")
def pdf(file_id: str, authorization: Optional[str] = Header(default=None)):
    _authorize_case(file_id, authorization)
    path = state.pdf_path(file_id)
    if not os.path.exists(path):
        raise HTTPException(404, "PDF not found")
    return FileResponse(path, media_type="application/pdf")

class DemandLetterBody(BaseModel):
    file_id: str
    sender: dict = {}
    recipient: dict = {}

@app.post("/demand-letter")
def demand_letter(body: DemandLetterBody, request: Request,
                  authorization: Optional[str] = Header(default=None)):
    _authorize_case(body.file_id, authorization)
    _cost_guard(_letter_throttle, _client_ip(request), "letter requests")
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
                           explanation=h.explanation, damages_estimate=h.damages_estimate,
                           legal_reasoning=h.legal_reasoning, damages_basis=h.damages_basis)
              for h in result.highlights]
    md = state.metadata_store.get(body.file_id) or result.documentMetadata
    body_html = _llm().draft_demand_letter(drafts, md, body.sender, body.recipient)
    # Render the damages table deterministically (not by the LLM), one row per
    # finding with a monetary remedy, plus a total.
    damages_rows = [(h.category, h.statute_citation or "", h.damages_estimate)
                    for h in result.highlights
                    if h.damages_estimate and h.damages_estimate > 0]
    pdf_bytes = render_letter_pdf(body_html, title="Demand Letter", damages_rows=damages_rows)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=demand-letter.pdf"})

@app.get("/report/{file_id}")
def report(file_id: str, authorization: Optional[str] = Header(default=None)):
    """Export the analysis itself as a PDF report (no LLM call — rendered from the
    stored findings)."""
    _authorize_case(file_id, authorization)
    result = state.results.get(file_id)
    stored = result.model_dump() if result is not None else db.get_result(file_id)
    if stored is None:
        raise HTTPException(404, "Analysis not ready")
    from app.letter_service import render_report_pdf
    highlights = stored.get("highlights", [])
    damages_rows = [(h.get("category", ""), h.get("statute_citation") or "", h["damages_estimate"])
                    for h in highlights
                    if h.get("damages_estimate") and h["damages_estimate"] > 0]
    pdf_bytes = render_report_pdf(highlights, damages_rows=damages_rows)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=clause-report.pdf"})
