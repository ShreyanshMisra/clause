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


def test_statutory_damages_override_model_estimate():
    from app.llm_service import LLMService
    from app.models import Metadata

    class DepositClient:
        def embed(self, text): return [1.0, 0.0, 0.0]
        def generate_json(self, prompt, schema=None):
            from app.pdf_service import extract_pages
            word = extract_pages(FIX)[0].text.split()[0]
            return {"findings": [{"quoted_text": word, "page": 1, "category": "Deposit",
                                  "severity": "illegal", "statute_id": "186-15B",
                                  "explanation": "forfeiture clause", "damages_estimate": 99}]}

    registry = JobRegistry()
    registry.create("fid-dmg", filename="s.pdf")
    store = LocalVectorStore()
    store.seed([Statute(id="186-15B", chapter="186", section="15B", title="Deposits",
                        text="return within 30 days", embedding=[1.0, 0.0, 0.0])])
    md = Metadata(monthlyRent="$2,000", securityDeposit="$1,500")
    result = analyze_document("fid-dmg", FIX, redacted_pages=["chunk"],
                              llm=LLMService(DepositClient()), embedder=DepositClient(),
                              store=store, registry=registry, metadata=md)
    # Model said 99; code recomputes treble the $1,500 deposit = 4500.
    assert result.highlights[0].damages_estimate == 4500.0
    assert "treble" in result.highlights[0].damages_basis.lower()


def test_parallel_chunks_return_in_document_order():
    import re
    from app.llm_service import LLMService

    class PageClient:
        """Returns a finding whose category is the chunk's first page number, so we
        can assert results reassemble in document order despite concurrency."""
        def embed(self, text): return [1.0, 0.0, 0.0]
        def generate_json(self, prompt, schema=None):
            m = re.search(r"=== PAGE (\d+) ===", prompt)
            page = m.group(1) if m else "0"
            return {"findings": [{"quoted_text": "x", "page": int(page), "category": page,
                                  "severity": "high", "statute_id": "a", "explanation": "e"}]}

    registry = JobRegistry()
    registry.create("fid-order")
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="D", text="d",
                        embedding=[1.0, 0.0, 0.0])])
    pages = [f"page {i} content" for i in range(1, 7)]  # 6 pages -> 3 groups
    result = analyze_document("fid-order", FIX, redacted_pages=pages,
                              llm=LLMService(PageClient()), embedder=PageClient(),
                              store=store, registry=registry)
    # One finding per group, categories = first page of each group, ascending.
    cats = [int(h.category) for h in result.highlights]
    assert cats == sorted(cats) and cats == [1, 3, 5]


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
