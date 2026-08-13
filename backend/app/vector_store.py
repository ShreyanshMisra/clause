from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional, Protocol

@dataclass
class Statute:
    id: str
    chapter: str
    section: str
    title: str
    text: str
    embedding: Optional[list[float]] = None

class VectorStore(Protocol):
    def seed(self, statutes: list[Statute]) -> None: ...
    def search(self, embedding: list[float], k: int) -> list[Statute]: ...

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

class LocalVectorStore:
    def __init__(self) -> None:
        self._items: list[Statute] = []

    def seed(self, statutes: list[Statute]) -> None:
        self._items = list(statutes)

    def search(self, embedding: list[float], k: int) -> list[Statute]:
        scored = sorted(self._items,
                        key=lambda s: _cosine(embedding, s.embedding or []),
                        reverse=True)
        return scored[:k]


import os
from typing import Callable


class SnowflakeVectorStore:
    def __init__(self, conn_factory: Callable[[], object], dim: int = 768,
                 table: str = "STATUTES") -> None:
        self._conn_factory = conn_factory
        self._dim = dim
        self._table = table

    def seed(self, statutes: list[Statute]) -> None:
        conn = self._conn_factory()
        cur = conn.cursor()
        try:
            for s in statutes:
                vec = "[" + ",".join(str(x) for x in (s.embedding or [])) + "]"
                cur.execute(
                    f"INSERT INTO {self._table} (id, chapter, section, title, text, embedding) "
                    f"SELECT %s, %s, %s, %s, %s, {vec}::VECTOR(FLOAT, {self._dim})",
                    (s.id, s.chapter, s.section, s.title, s.text),
                )
        finally:
            cur.close()

    def search(self, embedding: list[float], k: int) -> list[Statute]:
        vec = "[" + ",".join(str(x) for x in embedding) + "]"
        sql = (
            f"SELECT id, chapter, section, title, text FROM {self._table} "
            f"ORDER BY VECTOR_COSINE_SIMILARITY(embedding, {vec}::VECTOR(FLOAT, {self._dim})) "
            f"DESC LIMIT %s"
        )
        conn = self._conn_factory()
        cur = conn.cursor()
        try:
            cur.execute(sql, (k,))
            rows = cur.fetchall()
            return [Statute(id=r[0], chapter=r[1], section=r[2], title=r[3], text=r[4]) for r in rows]
        finally:
            cur.close()


def _load_private_key(path: str):
    from cryptography.hazmat.primitives import serialization
    with open(path, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _default_snowflake_conn():
    import snowflake.connector
    kwargs = dict(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=os.environ.get("SNOWFLAKE_DATABASE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA"),
    )
    # Prefer key-pair auth (works with MFA-enforced accounts); fall back to password.
    key_path = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH")
    if key_path:
        kwargs["private_key"] = _load_private_key(key_path)
    else:
        kwargs["password"] = os.environ["SNOWFLAKE_PASSWORD"]
    return snowflake.connector.connect(**kwargs)


def get_vector_store() -> VectorStore:
    backend = os.environ.get("VECTOR_BACKEND", "local").lower()
    if backend == "snowflake":
        return SnowflakeVectorStore(conn_factory=_default_snowflake_conn)
    return LocalVectorStore()


class CortexEmbedder:
    """Computes embeddings via Snowflake Cortex EMBED_TEXT_768 (in-database).

    Exposes the same `.embed(text) -> list[float]` interface as GeminiClient, so it
    can drive retrieval without an external embedding API. One connection is cached
    and reused across calls (a document produces one embed per page)."""

    def __init__(self, conn_factory: Callable[[], object], model: Optional[str] = None) -> None:
        self._conn_factory = conn_factory
        self._model = model or os.environ.get("CORTEX_EMBED_MODEL", "snowflake-arctic-embed-m-v1.5")
        self._conn = None

    def _cursor(self):
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn.cursor()

    def embed(self, text: str) -> list[float]:
        cur = self._cursor()
        try:
            cur.execute("SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768(%s, %s)", (self._model, text))
            return list(cur.fetchone()[0])
        finally:
            cur.close()


def get_embedder():
    """Return the retrieval embedder for the active backend.

    - snowflake: Cortex EMBED_TEXT_768 (in-DB, no external embedding key).
    - local: Gemini embeddings (google-generativeai)."""
    backend = os.environ.get("VECTOR_BACKEND", "local").lower()
    if backend == "snowflake":
        return CortexEmbedder(conn_factory=_default_snowflake_conn)
    from app.gemini_client import GeminiClient
    return GeminiClient.from_env()
