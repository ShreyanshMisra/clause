import json, os
from pathlib import Path
from app.vector_store import Statute, get_vector_store, get_embedder

_DATA = Path(__file__).parent / "data" / "ma_statutes.json"

def load_corpus() -> list[dict]:
    return json.loads(_DATA.read_text())

def build_statutes(items: list[dict], embedder) -> list[Statute]:
    out = []
    for it in items:
        tags = it.get("topic_tags", [])
        # Fold title + topic tags into the embedded text so lexical topic cues
        # (e.g. "deposit", "retaliation") strengthen retrieval.
        emb = embedder.embed(f"{it['title']}. {' '.join(tags)}. {it['text']}")
        out.append(Statute(id=it["id"], chapter=it["chapter"], section=it["section"],
                           title=it["title"], text=it["text"], embedding=emb,
                           topic_tags=tags, source_url=it.get("source_url", ""),
                           citation=it.get("citation", "")))
    return out

def main() -> None:
    # Uses Cortex embeddings when VECTOR_BACKEND=snowflake, Gemini embeddings when local.
    embedder = get_embedder()
    statutes = build_statutes(load_corpus(), embedder)
    store = get_vector_store()
    store.seed(statutes)
    print(f"Seeded {len(statutes)} statutes into {os.environ.get('VECTOR_BACKEND','local')} store.")

if __name__ == "__main__":
    main()
