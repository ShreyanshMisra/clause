from app.pii_llm import llm_pii_spans


class FakeFast:
    def __init__(self, payload):
        self.payload = payload
        self.prompts = []

    def generate_json(self, prompt):
        self.prompts.append(prompt)
        return self.payload


def test_llm_pii_spans_locates_offsets_and_type():
    text = "The landlord Jonathan Whitmore may enter."
    client = FakeFast({"pii": [{"text": "Jonathan Whitmore", "type": "PERSON"}]})
    spans = llm_pii_spans(text, client)
    assert spans and text[spans[0].start:spans[0].end] == "Jonathan Whitmore"
    assert spans[0].entity_type == "PERSON"


def test_llm_pii_spans_finds_all_occurrences():
    text = "Ann signed. Ann paid."
    spans = llm_pii_spans(text, FakeFast({"pii": [{"text": "Ann", "type": "PERSON"}]}))
    assert len(spans) == 2
    assert all(text[s.start:s.end] == "Ann" for s in spans)


def test_llm_pii_spans_ignores_missing_or_unfound_text():
    text = "No personal data here."
    spans = llm_pii_spans(text, FakeFast({"pii": [{"text": "Nonexistent", "type": "PERSON"}]}))
    assert spans == []


def test_llm_pii_spans_tolerates_bad_payload():
    text = "Something."
    assert llm_pii_spans(text, FakeFast({})) == []
    assert llm_pii_spans(text, FakeFast({"pii": "oops"})) == []


def test_redact_unions_llm_assist_when_enabled(monkeypatch):
    from app import pii_service
    # "Zeta Holdings" is an org name NER/regex won't catch; the LLM layer adds it.
    client = FakeFast({"pii": [{"text": "Zeta Holdings", "type": "ACCOUNT"}]})
    monkeypatch.setenv("PII_LLM_ASSIST", "1")
    pii_service.set_pii_client(client)
    try:
        result = pii_service.redact("Rent is paid to Zeta Holdings each month.")
        assert "Zeta Holdings" not in result.redacted_text
        assert result.summary.get("ACCOUNT", 0) >= 1
    finally:
        pii_service.set_pii_client(None)


def test_redact_ignores_llm_when_disabled(monkeypatch):
    from app import pii_service
    client = FakeFast({"pii": [{"text": "Zeta Holdings", "type": "ACCOUNT"}]})
    monkeypatch.delenv("PII_LLM_ASSIST", raising=False)
    pii_service.set_pii_client(client)
    try:
        result = pii_service.redact("Rent is paid to Zeta Holdings each month.")
        # Layer is injected but the flag is off, so the org name is left alone.
        assert "Zeta Holdings" in result.redacted_text
    finally:
        pii_service.set_pii_client(None)
