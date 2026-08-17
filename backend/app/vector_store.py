from __future__ import annotations
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

@dataclass
class Statute:
    id: str
    chapter: str
    section: str
    title: str
    text: str
    embedding: Optional[list[float]] = None
    topic_tags: list[str] = field(default_factory=list)
    source_url: str = ""
    # Preformatted citation for sources that don't fit the "M.G.L. c.X § Y" mold
    # (regulations like 105 CMR 410.180, case law like 363 Mass. 184). Empty for
    # ordinary statutes, which fall back to the chapter/section citation.
    citation: str = ""

class VectorStore(Protocol):
    def seed(self, statutes: list[Statute]) -> None: ...
    def search(self, embedding: list[float], k: int, query_text: str = "") -> list[Statute]: ...

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0

# Very small stopword set — enough to stop function words from dominating the
# keyword overlap without pulling in an NLP dependency.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "at", "by",
    "with", "shall", "may", "any", "this", "that", "is", "are", "be", "as", "from",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS and len(t) > 2}


def _keyword_overlap(query_text: str, statute: Statute) -> float:
    """Fraction of query tokens that appear in the statute's title/text/tags."""
    q = _tokens(query_text)
    if not q:
        return 0.0
    hay = _tokens(f"{statute.title} {statute.text} {' '.join(statute.topic_tags)}")
    return len(q & hay) / len(q)


# Weight on the keyword signal relative to cosine similarity. Small by default so
# vector similarity leads and keywords break ties / rescue lexical matches.
_KEYWORD_BOOST = 0.15


class LocalVectorStore:
    def __init__(self) -> None:
        self._items: list[Statute] = []

    def __len__(self) -> int:
        return len(self._items)

    def seed(self, statutes: list[Statute]) -> None:
        self._items = list(statutes)

    def search(self, embedding: list[float], k: int, query_text: str = "") -> list[Statute]:
        """Hybrid retrieval: cosine similarity plus a small keyword-overlap boost so
        lexically-obvious matches aren't lost when embeddings are noisy."""
        def hybrid(s: Statute) -> float:
            return _cosine(embedding, s.embedding or []) + _KEYWORD_BOOST * _keyword_overlap(query_text, s)
        return sorted(self._items, key=hybrid, reverse=True)[:k]


import os


class SnowflakeVectorStore:
    def __init__(self, conn_factory: Callable[[], Any], dim: int = 768,
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

    def search(self, embedding: list[float], k: int, query_text: str = "") -> list[Statute]:
        # query_text is accepted for interface parity with LocalVectorStore; the
        # DB path ranks purely by vector similarity for now.
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

    def __init__(self, conn_factory: Callable[[], Any], model: Optional[str] = None) -> None:
        self._conn_factory = conn_factory
        self._model = model or os.environ.get("CORTEX_EMBED_MODEL", "snowflake-arctic-embed-m-v1.5")
        self._conn: Any = None

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
