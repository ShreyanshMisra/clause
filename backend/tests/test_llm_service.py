from app.llm_service import LLMService

class FakeClient:
    def __init__(self, payload): self.payload = payload; self.calls = []
    def generate_json(self, prompt):
        self.calls.append(prompt); return self.payload
    def embed(self, text): return [0.1, 0.2, 0.3]

def test_extract_metadata_maps_fields():
    client = FakeClient({"parties": {"landlord": "L", "tenant": "T", "property": "P"},
                         "monthlyRent": "$1000", "leaseTerm": "12mo", "securityDeposit": "$1500"})
    svc = LLMService(client)
    md = svc.extract_metadata("some redacted text")
    assert md.parties.landlord == "L" and md.monthlyRent == "$1000"

def test_analyze_chunk_returns_finding_drafts():
    client = FakeClient({"findings": [
        {"quoted_text": "no return of deposit", "page": 2, "category": "Deposit",
         "severity": "illegal", "statute_citation": "M.G.L. c.186 s.15B",
         "explanation": "deposits must be returned", "damages_estimate": 1500}
    ]})
    svc = LLMService(client)
    drafts = svc.analyze_chunk("chunk", [], page_hint=2)
    assert drafts[0].severity == "illegal" and drafts[0].damages_estimate == 1500

def test_embed_delegates_to_client():
    svc = LLMService(FakeClient({}))
    assert svc.embed("hi") == [0.1, 0.2, 0.3]
