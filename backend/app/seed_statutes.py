import json, os
from pathlib import Path
from app.vector_store import Statute, get_vector_store

_DATA = Path(__file__).parent / "data" / "ma_statutes.json"

def load_corpus() -> list[dict]:
    return json.loads(_DATA.read_text())

def build_statutes(items: list[dict], llm) -> list[Statute]:
    out = []
    for it in items:
        emb = llm.embed(f"{it['title']}. {it['text']}")
        out.append(Statute(id=it["id"], chapter=it["chapter"], section=it["section"],
                           title=it["title"], text=it["text"], embedding=emb))
    return out

def main() -> None:
    from app.llm_service import LLMService
    from app.gemini_client import GeminiClient
    llm = LLMService(GeminiClient.from_env())
    statutes = build_statutes(load_corpus(), llm)
    store = get_vector_store()
    store.seed(statutes)
    print(f"Seeded {len(statutes)} statutes into {os.environ.get('VECTOR_BACKEND','local')} store.")

if __name__ == "__main__":
    main()
