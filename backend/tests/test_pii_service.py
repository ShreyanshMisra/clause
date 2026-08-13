from app.pii_service import redact

def test_redacts_email_phone_and_reports_counts():
    text = "Contact john@example.com or 415-555-1234 for questions."
    result = redact(text)
    assert "john@example.com" not in result.redacted_text
    assert "415-555-1234" not in result.redacted_text
    assert result.summary.get("email") == 1
    assert result.summary.get("phone") == 1

def test_no_pii_leaves_text_unchanged():
    text = "The tenant shall pay rent monthly."
    result = redact(text)
    assert result.redacted_text == text
    assert sum(result.summary.values()) == 0
