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

def _build_env_llm():
    from app.gemini_client import GeminiClient
    from app.llm_service import LLMService
    return LLMService(GeminiClient.from_env())

@app.on_event("startup")
def _init_llm():
    if state.llm is None:
        try:
            state.llm = _build_env_llm()
        except Exception as exc:
            import logging
            logging.warning("LLM init failed at startup: %s — will retry on first request", exc)
            return
    try:
        from app.bootstrap import seed_local_if_needed
        seed_local_if_needed(state.vector_store, state.llm)
        state.seeded = True
    except Exception as exc:
        import logging
        logging.warning("Statute seeding failed at startup: %s — will retry on first analysis", exc)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
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
        state.llm = _build_env_llm()
    if not state.seeded:
        from app.bootstrap import seed_local_if_needed
        seed_local_if_needed(state.vector_store, state.llm)
        state.seeded = True
    result = analyze_document(file_id, state.pdf_path(file_id),
                              state.redacted_pages.get(file_id, []),
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
