import json
from pathlib import Path

from scripts.build_corpus import validate

_DATA = Path(__file__).resolve().parent.parent / "app" / "data" / "ma_statutes.json"


def _load() -> list[dict]:
    return json.loads(_DATA.read_text())


def test_corpus_records_are_well_formed():
    records = _load()
    # Verified core; grows as coverage expands toward comprehensive.
    assert len(records) >= 8
    assert validate(records) == []


def test_corpus_ids_are_unique():
    ids = [r["id"] for r in _load()]
    assert len(ids) == len(set(ids))


def test_corpus_covers_core_chapters():
    chapters = {r["chapter"] for r in _load()}
    # The remedies most demand letters rely on: deposits/quiet enjoyment (186),
    # eviction defense (239), and consumer protection / treble damages (93A).
    assert {"186", "239", "93A"} <= chapters
