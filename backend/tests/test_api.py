from pathlib import Path
from fastapi.testclient import TestClient
import app.state as state
from app.main import app
from app.vector_store import LocalVectorStore, Statute
from app.llm_service import LLMService

FIX = Path(__file__).parent / "fixtures" / "sample-lease.pdf"

class FakeClient:
    def embed(self, text): return [1.0, 0.0, 0.0]
    def generate_json(self, prompt):
        if "metadata" in prompt.lower():
            return {"parties": {"landlord": "L", "tenant": "T", "property": "P"},
                    "monthlyRent": "$1000", "leaseTerm": "12mo", "securityDeposit": "$1500"}
        from app.pdf_service import extract_pages
        word = extract_pages(str(FIX))[0].text.split()[0]
        return {"findings": [{"quoted_text": word, "page": 1, "category": "Deposit",
                              "severity": "illegal", "statute_citation": "c.186",
                              "explanation": "e", "damages_estimate": 1500}]}
    def generate_text(self, prompt): return "<p>Dear Landlord</p>"

def setup_module(module):
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="Deposits",
                        text="deposit", embedding=[1.0, 0.0, 0.0])])
    state.vector_store = store
    state.llm = LLMService(FakeClient())
    state.embedder = FakeClient()
    state.seeded = True

def test_full_flow_upload_analyze_results():
    with TestClient(app) as client:
        with open(FIX, "rb") as f:
            up = client.post("/upload", files={"file": ("sample-lease.pdf", f, "application/pdf")})
        assert up.status_code == 200
        fid = up.json()["file_id"]
        assert "pii_redacted" in up.json()

        an = client.post("/analyze", json={"file_id": fid})
        assert an.status_code == 200

        st = client.get(f"/status/{fid}")
        assert st.status_code == 200 and st.json()["status"] in ("processing", "completed")

        doc = client.get(f"/document/{fid}")
        assert doc.status_code == 200
        assert doc.json()["analysisSummary"]["issuesFound"] >= 1

def test_pdf_endpoint_serves_bytes():
    with TestClient(app) as client:
        with open(FIX, "rb") as f:
            fid = client.post("/upload", files={"file": ("s.pdf", f, "application/pdf")}).json()["file_id"]
        r = client.get(f"/pdf/{fid}")
        assert r.status_code == 200 and r.content[:4] == b"%PDF"

def test_upload_rejects_non_pdf():
    with TestClient(app) as client:
        r = client.post("/upload", files={"file": ("doc.txt", b"hello", "text/plain")})
        assert r.status_code == 400

def test_status_unknown_id_returns_404():
    with TestClient(app) as client:
        r = client.get("/status/doesnotexist")
        assert r.status_code == 404

def test_demand_letter_returns_pdf():
    with TestClient(app) as client:
        with open(FIX, "rb") as f:
            fid = client.post("/upload", files={"file": ("s.pdf", f, "application/pdf")}).json()["file_id"]
        client.post("/analyze", json={"file_id": fid})
        client.get(f"/status/{fid}")  # flush
        r = client.post("/demand-letter", json={"file_id": fid, "sender": {"name": "T"}, "recipient": {"name": "L"}})
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
