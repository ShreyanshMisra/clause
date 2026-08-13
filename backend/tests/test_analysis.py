from pathlib import Path
from app.jobs import JobRegistry
from app.analysis import analyze_document
from app.vector_store import LocalVectorStore, Statute

FIX = str(Path(__file__).parent / "fixtures" / "sample-lease.pdf")

class FakeClient:
    def embed(self, text): return [1.0, 0.0, 0.0]
    def generate_json(self, prompt):
        from app.pdf_service import extract_pages
        word = extract_pages(FIX)[0].text.split()[0]
        return {"findings": [{"quoted_text": word, "page": 1, "category": "Deposit",
                              "severity": "illegal", "statute_citation": "c.186 s.15B",
                              "explanation": "deposit issue", "damages_estimate": 1500}]}

def test_analyze_document_produces_result_and_progress():
    from app.llm_service import LLMService
    registry = JobRegistry()
    registry.create("fid", filename="sample-lease.pdf")
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="Deposits",
                        text="deposit", embedding=[1.0, 0.0, 0.0])])
    result = analyze_document("fid", FIX, redacted_text="chunk text",
                              llm=LLMService(FakeClient()), store=store, registry=registry)
    assert result.analysisSummary.issuesFound >= 1
    assert registry.get("fid").status == "completed"
    assert registry.get("fid").progress == 100
    assert result.highlights[0].color == "red"
