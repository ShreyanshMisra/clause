import json, os, re
from typing import Callable, Optional

_FENCE = re.compile(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", re.DOTALL)

# Hard per-request timeout so a slow/hanging model can never stall analysis
# (some model aliases hang indefinitely on the generateContent path).
_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "60"))
# Deterministic sampling by default — consistency matters more than variety for
# legal analysis, so we pin temperature to 0 unless explicitly overridden.
_TEMPERATURE = float(os.environ.get("GEMINI_TEMPERATURE", "0"))

class GeminiClient:
    def __init__(self, model=None, embed_fn: Optional[Callable[[str], list]] = None) -> None:
        self._model = model
        self._embed_fn = embed_fn

    @classmethod
    def from_env(cls) -> "GeminiClient":
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-3-pro"))
        embed_model = os.environ.get("GEMINI_EMBED_MODEL", "models/gemini-embedding-001")
        def embed_fn(text: str) -> list:
            r = genai.embed_content(model=embed_model, content=text,
                                    output_dimensionality=768,
                                    request_options={"timeout": _TIMEOUT})
            return r["embedding"]
        return cls(model=model, embed_fn=embed_fn)

    @classmethod
    def fast_from_env(cls) -> "GeminiClient":
        """Build a client on the cheap/fast model (GEMINI_FAST_MODEL) for extraction
        steps like the PII assist pass. No embedder — generation only."""
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(os.environ.get("GEMINI_FAST_MODEL", "gemini-3.5-flash"))
        return cls(model=model)

    def embed(self, text: str) -> list:
        if self._embed_fn is None:
            raise RuntimeError("GeminiClient has no embedder; build it via from_env()")
        return self._embed_fn(text)

    def _generate(self, prompt: str, generation_config: Optional[dict] = None) -> str:
        config = {"temperature": _TEMPERATURE}
        if generation_config:
            config.update(generation_config)
        resp = self._model.generate_content(
            prompt,
            generation_config=config,
            request_options={"timeout": _TIMEOUT},
        )
        return resp.text or ""

    def generate_json(self, prompt: str, schema: Optional[dict] = None) -> dict:
        """Generate JSON. When `schema` is given, ask the model for schema-constrained
        JSON output; always fall back to parsing a fenced/raw JSON block so models or
        paths that ignore the schema still work."""
        config: Optional[dict] = None
        if schema is not None:
            config = {"response_mime_type": "application/json", "response_schema": schema}
        try:
            raw = self._generate(prompt, config)
        except Exception:
            # A model/SDK that rejects the schema config shouldn't break analysis —
            # retry prompt-only and lean on the fenced-JSON parser below.
            if config is None:
                raise
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
