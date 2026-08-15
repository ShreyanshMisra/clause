import json, os, re
from typing import Callable, Optional

_FENCE = re.compile(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", re.DOTALL)

# Hard per-request timeout so a slow/hanging model can never stall analysis
# (some model aliases hang indefinitely on the generateContent path).
_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "60"))

class GeminiClient:
    def __init__(self, model=None, embed_fn: Optional[Callable[[str], list]] = None) -> None:
        self._model = model
        self._embed_fn = embed_fn

    @classmethod
    def from_env(cls) -> "GeminiClient":
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"))
        embed_model = os.environ.get("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")
        def embed_fn(text: str) -> list:
            r = genai.embed_content(model=embed_model, content=text,
                                    output_dimensionality=768,
                                    request_options={"timeout": _TIMEOUT})
            return r["embedding"]
        return cls(model=model, embed_fn=embed_fn)

    def embed(self, text: str) -> list:
        return self._embed_fn(text)

    def _generate(self, prompt: str) -> str:
        resp = self._model.generate_content(prompt, request_options={"timeout": _TIMEOUT})
        return resp.text or ""

    def generate_json(self, prompt: str) -> dict:
        raw = self._generate(prompt)
        m = _FENCE.search(raw)
        candidate = m.group(1) if m else raw.strip()
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {"findings": parsed}
        except json.JSONDecodeError:
            return {}

    def generate_text(self, prompt: str) -> str:
        return self._generate(prompt)
