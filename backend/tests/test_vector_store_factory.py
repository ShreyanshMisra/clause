from app.vector_store import get_vector_store, LocalVectorStore, SnowflakeVectorStore

def test_factory_returns_local_by_default(monkeypatch):
    monkeypatch.setenv("VECTOR_BACKEND", "local")
    assert isinstance(get_vector_store(), LocalVectorStore)

def test_snowflake_search_builds_cosine_query():
    captured = {}
    class FakeCursor:
        def execute(self, sql, params=None):
            captured["sql"] = sql; captured["params"] = params
        def fetchall(self):
            return [("a", "186", "15B", "Deposits", "security deposit text")]
        def close(self): pass
    class FakeConn:
        def cursor(self): return FakeCursor()
    store = SnowflakeVectorStore(conn_factory=lambda: FakeConn())
    results = store.search([0.1, 0.2, 0.3], k=3)
    assert "VECTOR_COSINE_SIMILARITY" in captured["sql"]
    assert results[0].id == "a" and results[0].title == "Deposits"
