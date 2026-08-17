from eval.analysis_runner import load, score


def test_perfect_oracle_scores_full_recall():
    """Guards the scaffolding (not the model): an oracle returning the expected
    citations must score recall/precision 1.0."""
    rows = load()
    oracle = {r["lease_text"]: [{"statute_citation": e["statute"]} for e in r["expected"]]
              for r in rows}
    result = score(lambda text: oracle.get(text, []))
    assert result["recall"] == 1.0
    assert result["precision"] == 1.0
    assert result["matched"] == result["expected"] >= 3


def test_empty_analysis_scores_zero_recall():
    result = score(lambda _text: [])
    assert result["recall"] == 0.0
    assert result["matched"] == 0
