import os, tempfile
from app.jobs import JobRegistry
from app.vector_store import get_vector_store
from app.llm_service import LLMService

TMP_DIR = os.path.join(tempfile.gettempdir(), "clause")
os.makedirs(TMP_DIR, exist_ok=True)

registry = JobRegistry()
vector_store = get_vector_store()
llm: LLMService | None = None  # generation LLM (Gemini); set on startup or by tests
embedder = None                 # retrieval embedder (Cortex in snowflake mode, Gemini in local)
seeded: bool = False

results: dict[str, object] = {}          # file_id -> AnalysisResult
redacted_text: dict[str, str] = {}        # file_id -> redacted text
redacted_pages: dict[str, list[str]] = {}  # file_id -> per-page redacted text
metadata_store: dict[str, object] = {}    # file_id -> Metadata

def pdf_path(file_id: str) -> str:
    return os.path.join(TMP_DIR, f"{file_id}.pdf")
