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
