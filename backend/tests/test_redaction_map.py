from app.redaction_map import RedactionSpan, restore


def test_restore_maps_placeholders_back_to_original():
    spans = [
        RedactionSpan(start=4, end=14, placeholder="[PERSON_1]",
                      entity_type="PERSON", original="John Smith"),
    ]
    # The LLM quotes the redacted form; restore rebuilds the original wording.
    assert restore("The [PERSON_1] shall pay rent.", spans) == "The John Smith shall pay rent."


def test_restore_is_noop_without_placeholders():
    assert restore("The tenant shall pay rent.", []) == "The tenant shall pay rent."


def test_restore_handles_repeated_placeholder():
    spans = [RedactionSpan(start=0, end=3, placeholder="[PERSON_1]",
                           entity_type="PERSON", original="Ann")]
    assert restore("[PERSON_1] and [PERSON_1]", spans) == "Ann and Ann"
