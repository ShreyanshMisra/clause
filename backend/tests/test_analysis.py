from pathlib import Path
from app.jobs import JobRegistry
from app.analysis import analyze_document
from app.vector_store import LocalVectorStore, Statute

FIX = str(Path(__file__).parent / "fixtures" / "sample-lease.pdf")

class FakeClient:
    def embed(self, text): return [1.0, 0.0, 0.0]
    def generate_json(self, prompt, schema=None):
        from app.pdf_service import extract_pages
        word = extract_pages(FIX)[0].text.split()[0]
        return {"findings": [{"quoted_text": word, "page": 1, "category": "Deposit",
                              "severity": "illegal", "statute_id": "a",
                              "explanation": "deposit issue", "damages_estimate": 1500}]}

def test_analyze_document_produces_result_and_progress():
    from app.llm_service import LLMService
    registry = JobRegistry()
    registry.create("fid", filename="sample-lease.pdf")
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="Deposits",
                        text="deposit", embedding=[1.0, 0.0, 0.0])])
    result = analyze_document("fid", FIX, redacted_pages=["chunk text"],
                              llm=LLMService(FakeClient()), embedder=FakeClient(),
                              store=store, registry=registry)
    assert result.analysisSummary.issuesFound >= 1
    assert registry.get("fid").status == "completed"
    assert registry.get("fid").progress == 100
    assert result.highlights[0].color == "red"


def test_analyze_document_handles_zero_findings():
    from app.llm_service import LLMService
    class EmptyClient:
        def embed(self, text): return [1.0, 0.0, 0.0]
        def generate_json(self, prompt, schema=None): return {"findings": []}
    registry = JobRegistry()
    registry.create("fid2")
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="Deposits",
                        text="deposit", embedding=[1.0, 0.0, 0.0])])
    result = analyze_document("fid2", FIX, redacted_pages=["some text"],
                              llm=LLMService(EmptyClient()), embedder=EmptyClient(),
                              store=store, registry=registry)
    assert result.analysisSummary.issuesFound == 0
    assert result.analysisSummary.overallRisk == "Low"
    assert result.highlights == []
    assert registry.get("fid2").status == "completed"


def test_analyze_document_marks_failed_on_error():
    import pytest
    from app.llm_service import LLMService
    class BoomClient:
        def embed(self, text): raise RuntimeError("boom")
        def generate_json(self, prompt, schema=None): return {"findings": []}
    registry = JobRegistry()
    registry.create("fid3")
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="D", text="d", embedding=[1.0, 0.0, 0.0])])
    with pytest.raises(RuntimeError):
        analyze_document("fid3", FIX, redacted_pages=["text"],
                         llm=LLMService(BoomClient()), embedder=BoomClient(),
                         store=store, registry=registry)
    assert registry.get("fid3").status == "failed"
