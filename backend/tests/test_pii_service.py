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


def test_redact_email_span_roundtrips():
    text = "Reach me at a@b.com please."
    result = redact(text)
    email_spans = [s for s in result.spans if s.entity_type == "EMAIL"]
    assert email_spans and text[email_spans[0].start:email_spans[0].end] == "a@b.com"


def test_repeated_value_gets_one_consistent_placeholder():
    # Regex entities have stable boundaries (unlike NER), so this deterministically
    # exercises the consistent-placeholder path: same value twice -> same token.
    text = "Email a@b.com or a@b.com; second contact c@d.com."
    result = redact(text)
    assert result.redacted_text.count("[EMAIL_1]") == 2  # a@b.com deduped
    assert "[EMAIL_2]" in result.redacted_text            # c@d.com distinct
    assert "a@b.com" not in result.redacted_text and "c@d.com" not in result.redacted_text


def test_spans_contract_same_value_same_placeholder():
    text = "Email a@b.com or a@b.com; second contact c@d.com."
    spans = redact(text).spans
    by_value: dict[str, set[str]] = {}
    for s in spans:
        by_value.setdefault(s.original.strip().lower(), set()).add(s.placeholder)
        assert text[s.start:s.end] == s.original          # offsets roundtrip
    # Each distinct value maps to exactly one placeholder...
    assert all(len(phs) == 1 for phs in by_value.values())
    # ...and distinct values map to distinct placeholders.
    picked = [next(iter(phs)) for phs in by_value.values()]
    assert len(set(picked)) == len(picked)


def test_redaction_recall_on_mixed_structured_pii():
    """Recall eval: every structured PII item in a realistic sentence must be
    stripped (regex layer only, so this runs even without the NER engine)."""
    text = (
        "Payment by card 4111 1111 1111 1111 or SSN 123-45-6789; reach "
        "jane.doe@example.com or (415) 555-0100; mail to 16 New Ocean Street, "
        "Boston, MA 02139 or P.O. Box 4512."
    )
    result = redact(text)
    for leaked in ("4111 1111 1111 1111", "123-45-6789", "jane.doe@example.com",
                   "555-0100", "New Ocean Street", "02139", "P.O. Box 4512"):
        assert leaked not in result.redacted_text, f"{leaked!r} leaked through redaction"
    for kind in ("CREDIT_CARD", "SSN", "EMAIL", "PHONE", "ADDRESS", "PO_BOX"):
        assert result.summary.get(kind, 0) >= 1, f"expected a {kind} redaction"
