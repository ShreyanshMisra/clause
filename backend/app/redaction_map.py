"""Reversible redaction primitives.

`redact()` (in pii_service) produces a list of `RedactionSpan`s recording, for
each removed piece of PII, its offsets in the ORIGINAL text, the placeholder it
was replaced with, and the original value. `restore()` reverses a redacted quote
back to original text so a clause the LLM quoted in redacted form can still be
located in the source PDF for highlighting.

Kept dependency-free (no Presidio import) so highlighting/analysis can use it
without pulling the NER stack.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionSpan:
    start: int          # offset in the ORIGINAL text
    end: int            # exclusive
    placeholder: str    # e.g. "[PERSON_1]"
    entity_type: str    # e.g. "PERSON"
    original: str       # the original substring that was redacted


def restore(redacted_text: str, spans: list[RedactionSpan]) -> str:
    """Replace each placeholder token with its original value.

    Used to turn an LLM's redacted quote back into text that can be located in
    the source PDF. A placeholder is stable per entity, so we de-dup to one
    original per placeholder before substituting."""
    out = redacted_text
    seen: dict[str, str] = {}
    for s in spans:
        seen.setdefault(s.placeholder, s.original)
    for placeholder, original in seen.items():
        out = out.replace(placeholder, original)
    return out
