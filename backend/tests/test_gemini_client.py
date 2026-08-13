from app.gemini_client import GeminiClient

class FakeResp:
    def __init__(self, text): self.text = text

class FakeModel:
    def __init__(self, text): self._text = text
    def generate_content(self, prompt): return FakeResp(self._text)

def test_generate_json_parses_fenced_block():
    client = GeminiClient(model=FakeModel('```json\n{"a": 1}\n```'), embed_fn=lambda t: [0.0])
    assert client.generate_json("p") == {"a": 1}

def test_generate_json_returns_empty_on_garbage():
    client = GeminiClient(model=FakeModel("not json at all"), embed_fn=lambda t: [0.0])
    assert client.generate_json("p") == {}
