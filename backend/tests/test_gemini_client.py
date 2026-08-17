from app.gemini_client import GeminiClient

class FakeResp:
    def __init__(self, text): self.text = text

class FakeModel:
    def __init__(self, text): self._text = text; self.last_kwargs = None
    def generate_content(self, prompt, **kwargs): self.last_kwargs = kwargs; return FakeResp(self._text)

def test_generate_json_parses_fenced_block():
    client = GeminiClient(model=FakeModel('```json\n{"a": 1}\n```'), embed_fn=lambda t: [0.0])
    assert client.generate_json("p") == {"a": 1}

def test_generate_json_returns_empty_on_garbage():
    client = GeminiClient(model=FakeModel("not json at all"), embed_fn=lambda t: [0.0])
    assert client.generate_json("p") == {}

def test_generate_json_passes_schema_to_model():
    model = FakeModel('{"ok": true}')
    client = GeminiClient(model=model, embed_fn=lambda t: [0.0])
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    assert client.generate_json("p", schema=schema) == {"ok": True}
    cfg = model.last_kwargs["generation_config"]
    assert cfg["response_schema"] == schema
    assert cfg["response_mime_type"] == "application/json"

def test_generate_json_without_schema_omits_schema_config():
    model = FakeModel('{"ok": true}')
    client = GeminiClient(model=model, embed_fn=lambda t: [0.0])
    client.generate_json("p")
    assert "response_schema" not in model.last_kwargs["generation_config"]
