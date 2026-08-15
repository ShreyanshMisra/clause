from pathlib import Path
from fastapi.testclient import TestClient
import app.state as state
from app.main import app
from app.vector_store import LocalVectorStore, Statute
from app.llm_service import LLMService
from tests.test_api import FakeClient

FIX = Path(__file__).parent / "fixtures" / "sample-lease.pdf"


def setup_module(module):
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="Deposits",
                        text="deposit", embedding=[1.0, 0.0, 0.0])])
    state.vector_store = store
    state.llm = LLMService(FakeClient())
    state.embedder = FakeClient()
    state.seeded = True


def test_login_rejects_bad_email():
    with TestClient(app) as client:
        assert client.post("/login", json={"email": "nope"}).status_code == 400


def test_login_normalizes_and_returns_email():
    with TestClient(app) as client:
        r = client.post("/login", json={"email": "  User@Example.COM "})
        assert r.status_code == 200 and r.json()["email"] == "user@example.com"


def test_cases_requires_auth_header():
    with TestClient(app) as client:
        assert client.get("/cases").status_code == 401


def test_uploaded_case_appears_in_user_dashboard():
    email = "tenant@example.com"
    with TestClient(app) as client:
        with open(FIX, "rb") as f:
            up = client.post("/upload", headers={"X-User-Email": email},
                             files={"file": ("lease.pdf", f, "application/pdf")})
        fid = up.json()["file_id"]
        client.post("/analyze", json={"file_id": fid})
        client.get(f"/status/{fid}")  # flush background task

        cases = client.get("/cases", headers={"X-User-Email": email}).json()["cases"]
        ids = [c["id"] for c in cases]
        assert fid in ids
        case = next(c for c in cases if c["id"] == fid)
        assert case["status"] == "completed"
        assert case["issues_found"] >= 1


def test_case_isolated_between_users():
    with TestClient(app) as client:
        with open(FIX, "rb") as f:
            fid = client.post("/upload", headers={"X-User-Email": "a@example.com"},
                              files={"file": ("l.pdf", f, "application/pdf")}).json()["file_id"]
        other = client.get("/cases", headers={"X-User-Email": "b@example.com"}).json()["cases"]
        assert fid not in [c["id"] for c in other]
