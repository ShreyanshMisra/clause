"""Validate the statute corpus and print a coverage summary.

Run: `python -m scripts.build_corpus` (from backend/). Acts as a lint gate — exits
non-zero if any record is malformed or an id is duplicated. It does NOT verify legal
accuracy; statute text must be reviewed by a human familiar with MA landlord-tenant
law before it ships.
"""
import json
import sys
from collections import Counter
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "app" / "data" / "ma_statutes.json"
_REQUIRED = ("id", "chapter", "section", "title", "text", "topic_tags", "source_url")


def validate(records: list[dict]) -> list[str]:
    errors: list[str] = []
    ids = Counter(r.get("id") for r in records)
    for dup, n in ids.items():
        if n > 1:
            errors.append(f"duplicate id: {dup!r} ({n}x)")
    for r in records:
        rid = r.get("id", "<no id>")
        for key in _REQUIRED:
            val = r.get(key)
            if val in (None, "", []):
                errors.append(f"{rid}: missing/empty field {key!r}")
        if not isinstance(r.get("topic_tags"), list):
            errors.append(f"{rid}: topic_tags must be a list")
    return errors


def main() -> int:
    records = json.loads(_DATA.read_text())
    errors = validate(records)
    by_chapter = Counter(r["chapter"] for r in records)
    print(f"Corpus: {len(records)} records across {len(by_chapter)} chapters")
    for chapter, n in sorted(by_chapter.items()):
        print(f"  c.{chapter}: {n}")
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("OK — all records well-formed (content still requires legal review).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
