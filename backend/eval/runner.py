"""PII redaction eval: measures recall (fraction of labeled PII removed) against a
labeled dataset and reports the concrete leaks. Run as `python -m eval.runner` for
a human-readable report, or via the pytest gate in tests/test_eval_pii.py."""
import json
from pathlib import Path

from app.pii_service import redact

_DATA = Path(__file__).parent / "pii_dataset.jsonl"


def load(path: Path = _DATA) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def score() -> dict:
    """Recall = fraction of labeled PII strings removed. `leaks` lists the misses."""
    total, removed, leaks = 0, 0, []
    for row in load():
        red = redact(row["text"]).redacted_text
        for pii in row["pii"]:
            total += 1
            if pii not in red:
                removed += 1
            else:
                leaks.append({"text": row["text"], "leaked": pii})
    return {"total": total, "removed": removed,
            "recall": removed / total if total else 1.0, "leaks": leaks}


if __name__ == "__main__":
    result = score()
    print(f"PII recall: {result['recall']:.1%} ({result['removed']}/{result['total']})")
    for leak in result["leaks"]:
        print(f"  LEAK: {leak['leaked']!r} in {leak['text']!r}")
