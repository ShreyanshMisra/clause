from pathlib import Path
from fastapi.testclient import TestClient
import app.state as state
from app.main import app
from app.vector_store import LocalVectorStore, Statute
from app.llm_service import LLMService
from tests.test_api import FakeClient

FIX = Path(__file__).parent / "fixtures" / "sample-lease.pdf"
PW = "hunter2pass"


def setup_module(module):
    store = LocalVectorStore()
    store.seed([Statute(id="a", chapter="186", section="15B", title="Deposits",
                        text="deposit", embedding=[1.0, 0.0, 0.0])])
    state.vector_store = store
    state.llm = LLMService(FakeClient())
    state.embedder = FakeClient()
    state.seeded = True


def _auth(client, email, password=PW):
    """Register-or-login and return an Authorization header."""
    token = client.post("/login", json={"email": email, "password": password}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_rejects_bad_email():
    with TestClient(app) as client:
        r = client.post("/login", json={"email": "nope", "password": PW})
        assert r.status_code == 400


def test_login_rejects_short_password():
    with TestClient(app) as client:
        r = client.post("/login", json={"email": "a@example.com", "password": "short"})
        assert r.status_code == 400


def test_login_registers_then_returns_token():
    with TestClient(app) as client:
        r = client.post("/login", json={"email": "  User@Example.COM ", "password": PW})
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "user@example.com" and body["token"]


def test_login_wrong_password_rejected():
    with TestClient(app) as client:
        client.post("/login", json={"email": "pw@example.com", "password": PW})  # register
        r = client.post("/login", json={"email": "pw@example.com", "password": "wrongpass1"})
        assert r.status_code == 401


def test_cases_requires_valid_token():
    with TestClient(app) as client:
        assert client.get("/cases").status_code == 401
        assert client.get("/cases", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_uploaded_case_appears_in_user_dashboard():
    email = "tenant@example.com"
    with TestClient(app) as client:
        hdr = _auth(client, email)
        with open(FIX, "rb") as f:
            up = client.post("/upload", headers=hdr,
                             files={"file": ("lease.pdf", f, "application/pdf")})
        fid = up.json()["file_id"]
        client.post("/analyze", json={"file_id": fid})

        cases = client.get("/cases", headers=hdr).json()["cases"]
        case = next(c for c in cases if c["id"] == fid)
        assert case["status"] == "completed"
        assert case["issues_found"] >= 1


def test_case_isolated_between_users():
    with TestClient(app) as client:
        a, b = _auth(client, "a@example.com"), _auth(client, "b@example.com")
        with open(FIX, "rb") as f:
            fid = client.post("/upload", headers=a,
                              files={"file": ("l.pdf", f, "application/pdf")}).json()["file_id"]
        other = client.get("/cases", headers=b).json()["cases"]
        assert fid not in [c["id"] for c in other]


def test_owned_case_endpoints_reject_other_users():
    with TestClient(app) as client:
        owner = _auth(client, "owner@example.com")
        attacker = _auth(client, "attacker@example.com")
        with open(FIX, "rb") as f:
            fid = client.post("/upload", headers=owner,
                              files={"file": ("l.pdf", f, "application/pdf")}).json()["file_id"]
        client.post("/analyze", json={"file_id": fid})

        # Owner can read their own case + PDF.
        assert client.get(f"/document/{fid}", headers=owner).status_code == 200
        assert client.get(f"/pdf/{fid}", headers=owner).status_code == 200

        # Another user — and an unauthenticated request — get 404 (not 403), so
        # we never confirm the file_id exists.
        for hdr in (attacker, {}):
            assert client.get(f"/document/{fid}", headers=hdr).status_code == 404
            assert client.get(f"/pdf/{fid}", headers=hdr).status_code == 404
            assert client.get(f"/status/{fid}", headers=hdr).status_code == 404
            assert client.post("/demand-letter", headers=hdr,
                               json={"file_id": fid}).status_code == 404


def test_guest_case_remains_public():
    # A case uploaded with no account (owner is NULL) stays accessible — this is
    # the demo/anonymous path the base test suite relies on.
    with TestClient(app) as client:
        with open(FIX, "rb") as f:
            fid = client.post("/upload",
                              files={"file": ("l.pdf", f, "application/pdf")}).json()["file_id"]
        assert client.get(f"/pdf/{fid}").status_code == 200
