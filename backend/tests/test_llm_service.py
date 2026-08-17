from app.llm_service import LLMService

class FakeClient:
    def __init__(self, payload): self.payload = payload; self.calls = []
    def generate_json(self, prompt, schema=None):
        self.calls.append(prompt); return self.payload
    def generate_text(self, prompt): return "<p>letter body</p>"
    def embed(self, text): return [0.1, 0.2, 0.3]

def test_extract_metadata_maps_fields():
    client = FakeClient({"parties": {"landlord": "L", "tenant": "T", "property": "P"},
                         "monthlyRent": "$1000", "leaseTerm": "12mo", "securityDeposit": "$1500"})
    svc = LLMService(client)
    md = svc.extract_metadata("some redacted text")
    assert md.parties.landlord == "L" and md.monthlyRent == "$1000"

def test_analyze_chunk_grounds_and_canonicalizes_citation():
    from app.vector_store import Statute
    statutes = [Statute(id="186-15B", chapter="186", section="15B", title="Deposits",
                        text="A lessor shall return the deposit within 30 days.")]
    client = FakeClient({"findings": [
        {"quoted_text": "no return of deposit", "page": 2, "category": "Deposit",
         "severity": "illegal", "statute_id": "186-15B",
         "legal_reasoning": "clause forfeits deposit, violating 15B",
         "severity_rationale": "explicit forfeiture is illegal",
         "recommended_action": "demand return of the deposit",
         "confidence": 0.9,
         "explanation": "deposits must be returned", "damages_estimate": 1500}
    ]})
    svc = LLMService(client)
    drafts = svc.analyze_chunk("chunk", statutes, page_hint=2)
    assert drafts[0].severity == "illegal" and drafts[0].damages_estimate == 1500
    # citation comes from our corpus, canonicalized — never the raw model output
    assert drafts[0].statute_citation == "M.G.L. c.186 § 15B"
    # reasoning fields propagate; statute_quote is sourced from OUR corpus text
    assert drafts[0].legal_reasoning == "clause forfeits deposit, violating 15B"
    assert drafts[0].recommended_action == "demand return of the deposit"
    assert drafts[0].confidence == 0.9
    assert drafts[0].statute_quote == "A lessor shall return the deposit within 30 days."

def test_analyze_chunk_drops_ungrounded_findings():
    from app.vector_store import Statute
    statutes = [Statute(id="186-15B", chapter="186", section="15B", title="Deposits", text="...")]
    client = FakeClient({"findings": [
        {"quoted_text": "x", "page": 1, "category": "Made up", "severity": "illegal",
         "statute_id": "999-999", "explanation": "hallucinated", "damages_estimate": 1},
        {"quoted_text": "y", "page": 1, "category": "Deposit", "severity": "high",
         "statute_id": "186-15B", "explanation": "real", "damages_estimate": 2},
    ]})
    svc = LLMService(client)
    drafts = svc.analyze_chunk("chunk", statutes, page_hint=1)
    assert len(drafts) == 1 and drafts[0].category == "Deposit"  # ungrounded one dropped

def test_embed_delegates_to_client():
    svc = LLMService(FakeClient({}))
    assert svc.embed("hi") == [0.1, 0.2, 0.3]

def test_draft_demand_letter_returns_text():
    from app.llm_service import FindingDraft
    from app.models import Metadata
    svc = LLMService(FakeClient({}))
    draft = FindingDraft(quoted_text="q", page=1, category="Deposit", severity="illegal",
                         statute_citation="c.186", explanation="e", damages_estimate=100)
    html = svc.draft_demand_letter([draft], Metadata(), {"name": "T"}, {"name": "L"})
    assert html == "<p>letter body</p>"
