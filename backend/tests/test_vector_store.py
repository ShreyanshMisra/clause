from app.vector_store import LocalVectorStore, Statute

def test_local_store_seed_and_search_orders_by_similarity():
    store = LocalVectorStore()
    store.seed([
        Statute(id="a", chapter="186", section="15B", title="Deposits", text="security deposit",
                embedding=[1.0, 0.0, 0.0]),
        Statute(id="b", chapter="186", section="14", title="Entry", text="quiet enjoyment",
                embedding=[0.0, 1.0, 0.0]),
    ])
    results = store.search([0.9, 0.1, 0.0], k=2)
    assert results[0].id == "a"
    assert len(results) == 2


def test_search_keyword_boost_breaks_vector_ties():
    store = LocalVectorStore()
    store.seed([
        Statute(id="dep", chapter="186", section="15B", title="Security deposits",
                text="A lessor shall pay interest on a security deposit",
                topic_tags=["deposit"], embedding=[1.0, 0.0]),
        Statute(id="quiet", chapter="186", section="14", title="Quiet enjoyment",
                text="interference with quiet enjoyment", topic_tags=["quiet"],
                embedding=[1.0, 0.0]),  # identical vector -> keyword must decide
    ])
    res = store.search([1.0, 0.0], k=1, query_text="security deposit interest")
    assert res[0].id == "dep"


def test_search_without_query_text_is_pure_vector():
    store = LocalVectorStore()
    store.seed([
        Statute(id="a", chapter="1", section="1", title="A", text="alpha", embedding=[1.0, 0.0]),
        Statute(id="b", chapter="1", section="2", title="B", text="beta", embedding=[0.0, 1.0]),
    ])
    assert store.search([0.2, 1.0], k=1)[0].id == "b"
