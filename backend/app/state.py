import os, tempfile
from app.jobs import JobRegistry
from app.vector_store import get_vector_store
from app.llm_service import LLMService

TMP_DIR = os.path.join(tempfile.gettempdir(), "clause")
os.makedirs(TMP_DIR, exist_ok=True)

registry = JobRegistry()
vector_store = get_vector_store()
llm: LLMService | None = None  # set on startup or by tests

results: dict[str, object] = {}          # file_id -> AnalysisResult
redacted_text: dict[str, str] = {}        # file_id -> redacted text
metadata_store: dict[str, object] = {}    # file_id -> Metadata

def pdf_path(file_id: str) -> str:
    return os.path.join(TMP_DIR, f"{file_id}.pdf")
