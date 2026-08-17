"""Analysis eval scaffolding: measures how well an analysis function flags the
expected clauses and cites the right statutes.

`score(analyze_fn)` takes a callable `lease_text -> list[finding dict]` where each
finding has at least `statute_citation` (and optionally `category`). Phase 2 wires
the real pipeline in; for now this defines the shape + metrics with no pass/fail
gate.
"""
import json
import re
from pathlib import Path
from typing import Callable

_DATA = Path(__file__).parent / "analysis_dataset.jsonl"

Finding = dict
AnalyzeFn = Callable[[str], list[Finding]]


def load(path: Path = _DATA) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _norm_citation(cite: str | None) -> str:
    """Collapse a citation to comparable tokens: chapter + section digits/letters."""
    return re.sub(r"[^a-z0-9]", "", (cite or "").lower())


def score(analyze_fn: AnalyzeFn) -> dict:
    """Compute precision/recall over expected findings (matched by statute citation)
    and citation accuracy among matches."""
    expected_total = 0
    produced_total = 0
    matched = 0
    for row in load():
        produced = analyze_fn(row["lease_text"])
        produced_total += len(produced)
        produced_cites = {_norm_citation(f.get("statute_citation")) for f in produced}
        for exp in row["expected"]:
            expected_total += 1
            if _norm_citation(exp["statute"]) in produced_cites:
                matched += 1
    return {
        "expected": expected_total,
        "produced": produced_total,
        "matched": matched,
        "recall": matched / expected_total if expected_total else 1.0,
        "precision": matched / produced_total if produced_total else 0.0,
    }


if __name__ == "__main__":  # pragma: no cover
    # Demo with a perfect oracle so the scaffolding is runnable standalone.
    rows = load()
    oracle = {r["lease_text"]: [{"statute_citation": e["statute"]} for e in r["expected"]]
              for r in rows}
    result = score(lambda text: oracle.get(text, []))
    print(result)
