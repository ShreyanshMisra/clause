import os
from app.seed_statutes import load_corpus, build_statutes
from app.vector_store import LocalVectorStore

def seed_local_if_needed(store, llm) -> None:
    if os.environ.get("VECTOR_BACKEND", "local").lower() == "local" and isinstance(store, LocalVectorStore):
        store.seed(build_statutes(load_corpus(), llm))
