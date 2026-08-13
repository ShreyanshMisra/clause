import json, os, re
from typing import Callable, Optional

_FENCE = re.compile(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", re.DOTALL)

class GeminiClient:
    def __init__(self, model=None, embed_fn: Optional[Callable[[str], list]] = None) -> None:
        self._model = model
        self._embed_fn = embed_fn

    @classmethod
    def from_env(cls) -> "GeminiClient":
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash")
        def embed_fn(text: str) -> list:
            r = genai.embed_content(model="models/text-embedding-004", content=text)
            return r["embedding"]
        return cls(model=model, embed_fn=embed_fn)

    def embed(self, text: str) -> list:
        return self._embed_fn(text)

    def generate_json(self, prompt: str) -> dict:
        raw = self._model.generate_content(prompt).text or ""
        m = _FENCE.search(raw)
        candidate = m.group(1) if m else raw.strip()
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {"findings": parsed}
        except json.JSONDecodeError:
            return {}
