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
