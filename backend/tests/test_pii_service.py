from app.pii_service import redact

def test_redacts_email_phone_and_reports_counts():
    text = "Contact john@example.com or 415-555-1234 for questions."
    result = redact(text)
    assert "john@example.com" not in result.redacted_text
    assert "415-555-1234" not in result.redacted_text
    assert result.summary.get("EMAIL") == 1
    assert result.summary.get("PHONE") == 1

def test_redacts_person_name_via_ner():
    # Requires Presidio+spaCy; skip gracefully if the NER engine isn't installed.
    from app.pii_service import _get_ner
    if _get_ner() is None:
        import pytest
        pytest.skip("Presidio/spaCy not available")
    result = redact("The landlord Jonathan Whitmore may enter the unit with notice.")
    assert "Jonathan Whitmore" not in result.redacted_text
    assert result.summary.get("PERSON", 0) >= 1

def test_redacts_street_address():
    result = redact("The premises at 16 New Ocean Street are leased to the tenant.")
    assert "16 New Ocean Street" not in result.redacted_text
    assert result.summary.get("ADDRESS", 0) >= 1

def test_no_structured_pii_keeps_clause_text():
    text = "The tenant shall pay rent on the first day of each month."
    result = redact(text)
    assert result.summary.get("EMAIL") is None
    assert result.summary.get("PHONE") is None
    assert "shall pay rent" in result.redacted_text
