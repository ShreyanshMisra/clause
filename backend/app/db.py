"""SQLite persistence for accounts and cases.

Uses the stdlib `sqlite3` — no extra dependency. The demo kept everything in
memory; a working app needs users and their case history to survive restarts,
so completed analyses (result JSON + summary columns) and the uploaded PDF path
are persisted here, keyed by the account email.
"""
import json
import os
import sqlite3
import threading
import time
from typing import Optional

# Persistent data dir (PDFs + sqlite file). Override with DATA_DIR for deploys.
DATA_DIR = os.environ.get(
    "DATA_DIR", os.path.join(os.path.dirname(__file__), "data", "store")
)
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "clause.db")

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None


def _connect() -> sqlite3.Connection:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init(path: Optional[str] = None) -> None:
    """Create tables. Call once at startup (and in tests with a temp path)."""
    global _conn, DATA_DIR, UPLOADS_DIR, DB_PATH
    if path is not None:
        DATA_DIR = path
        UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
        DB_PATH = os.path.join(DATA_DIR, "clause.db")
    with _lock:
        _conn = _connect()
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                email         TEXT PRIMARY KEY,
                created_at    REAL NOT NULL,
                password_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS cases (
                id          TEXT PRIMARY KEY,
                user_email  TEXT,
                filename    TEXT,
                created_at  REAL NOT NULL,
                status      TEXT NOT NULL,
                overall_risk       TEXT,
                issues_found       INTEGER,
                estimated_recovery TEXT,
                pdf_path    TEXT,
                result_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_cases_user ON cases(user_email);
            """
        )
        # Migrate older databases that predate password auth.
        try:
            _conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists
        _conn.commit()


def _db() -> sqlite3.Connection:
    if _conn is None:
        init()
    assert _conn is not None
    return _conn


def upload_path(case_id: str) -> str:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    return os.path.join(UPLOADS_DIR, f"{case_id}.pdf")


# ── Users ────────────────────────────────────────────────────────────────
def upsert_user(email: str) -> None:
    with _lock:
        _db().execute(
            "INSERT INTO users(email, created_at) VALUES(?, ?) "
            "ON CONFLICT(email) DO NOTHING",
            (email, time.time()),
        )
        _db().commit()


def create_user(email: str, password_hash: str) -> None:
    with _lock:
        _db().execute(
            "INSERT INTO users(email, created_at, password_hash) VALUES(?, ?, ?)",
            (email, time.time(), password_hash),
        )
        _db().commit()


def get_user(email: str) -> Optional[dict]:
    row = _db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    return dict(row) if row else None


# ── Cases ────────────────────────────────────────────────────────────────
def create_case(case_id: str, user_email: Optional[str], filename: str,
                pdf_path: str) -> None:
    with _lock:
        _db().execute(
            "INSERT OR REPLACE INTO cases"
            "(id, user_email, filename, created_at, status, pdf_path) "
            "VALUES(?,?,?,?,?,?)",
            (case_id, user_email, filename, time.time(), "uploaded", pdf_path),
        )
        _db().commit()


def save_result(case_id: str, result: dict) -> None:
    """Persist a completed analysis onto its case row."""
    summary = result.get("analysisSummary", {})
    with _lock:
        _db().execute(
            "UPDATE cases SET status=?, overall_risk=?, issues_found=?, "
            "estimated_recovery=?, result_json=? WHERE id=?",
            (
                "completed",
                summary.get("overallRisk"),
                summary.get("issuesFound"),
                summary.get("estimatedRecovery"),
                json.dumps(result),
                case_id,
            ),
        )
        _db().commit()


def set_status(case_id: str, status: str) -> None:
    with _lock:
        _db().execute("UPDATE cases SET status=? WHERE id=?", (status, case_id))
        _db().commit()


def get_case(case_id: str) -> Optional[dict]:
    row = _db().execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    return dict(row) if row else None


def get_result(case_id: str) -> Optional[dict]:
    row = _db().execute(
        "SELECT result_json FROM cases WHERE id=?", (case_id,)
    ).fetchone()
    if row and row["result_json"]:
        return json.loads(row["result_json"])
    return None


def list_cases(user_email: str) -> list[dict]:
    """Case summaries for a user's dashboard, newest first."""
    rows = _db().execute(
        "SELECT id, filename, created_at, status, overall_risk, issues_found, "
        "estimated_recovery FROM cases WHERE user_email=? ORDER BY created_at DESC",
        (user_email,),
    ).fetchall()
    return [dict(r) for r in rows]
