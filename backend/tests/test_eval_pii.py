import pytest

from app.pii_service import _get_ner
from eval.runner import score


def test_pii_recall_meets_threshold():
    if _get_ner() is None:
        pytest.skip("NER engine not available; structured-only recall is lower")
    result = score()
    assert result["recall"] >= 0.90, f"PII leaks: {result['leaks']}"
