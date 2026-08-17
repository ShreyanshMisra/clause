import os

import pytest

from eval.analysis_runner import load, score


def test_perfect_oracle_scores_full_recall():
    """Guards the scaffolding (not the model): an oracle returning the expected
    citations must score recall/precision 1.0."""
    rows = load()
    oracle = {r["lease_text"]: [{"statute_citation": e["statute"]} for e in r["expected"]]
              for r in rows}
    result = score(lambda text: oracle.get(text, []))
    assert result["recall"] == 1.0
    assert result["precision"] == 1.0
    assert result["matched"] == result["expected"] >= 8


def test_empty_analysis_scores_zero_recall():
    result = score(lambda _text: [])
    assert result["recall"] == 0.0
    assert result["matched"] == 0


def _corpus_statutes():
    """Real corpus statutes with dummy embeddings, used as the candidate list so the
    grounding + citation-canonicalization pipeline runs end-to-end."""
    from app.seed_statutes import load_corpus
    from app.vector_store import Statute
    return [Statute(id=s["id"], chapter=s["chapter"], section=s["section"],
                    title=s["title"], text=s["text"], embedding=[0.0]) for s in load_corpus()]


class _OracleClient:
    """Fake LLM that, given a chunk, returns the dataset's expected finding for it —
    so the test measures the pipeline (grounding, citation) not the model."""
    def __init__(self, rows):
        self._by_text = {r["lease_text"]: r["expected"] for r in rows}

    def generate_json(self, prompt, schema=None):
        for text, expected in self._by_text.items():
            if text in prompt:
                return {"findings": [
                    {"quoted_text": text[:20], "page": 1, "category": e["category"],
                     "severity": "illegal", "statute_id": e["statute_id"],
                     "explanation": "e", "confidence": 0.9} for e in expected]}
        return {"findings": []}

    def embed(self, text):
        return [0.0]


def test_pipeline_scores_full_recall_with_oracle_llm():
    """End-to-end pipeline check with a deterministic LLM: grounding must map each
    statute_id back to the correct canonical citation, scoring 1.0. No API calls."""
    from app.llm_service import LLMService
    rows = load()
    statutes = _corpus_statutes()
    svc = LLMService(_OracleClient(rows))

    def analyze_fn(lease_text):
        drafts = svc.analyze_chunk(lease_text, statutes)
        return [{"statute_citation": d.statute_citation} for d in drafts]

    result = score(analyze_fn)
    assert result["recall"] == 1.0, result
    assert result["precision"] == 1.0, result


@pytest.mark.skipif(os.environ.get("RUN_LIVE_EVAL") != "1",
                    reason="live eval hits the real Gemini API; set RUN_LIVE_EVAL=1 to run")
def test_pipeline_live_model():  # pragma: no cover - opt-in, needs credentials
    from app.gemini_client import GeminiClient
    from app.llm_service import LLMService
    statutes = _corpus_statutes()
    svc = LLMService(GeminiClient.from_env())

    def analyze_fn(lease_text):
        drafts = svc.analyze_chunk(lease_text, statutes)
        return [{"statute_citation": d.statute_citation} for d in drafts]

    result = score(analyze_fn)
    assert result["recall"] >= 0.6, result
