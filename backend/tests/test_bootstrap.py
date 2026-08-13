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
