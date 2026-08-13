import re
from dataclasses import dataclass, field

@dataclass
class RedactionResult:
    redacted_text: str
    summary: dict = field(default_factory=dict)

_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}
_PLACEHOLDER = {"email": "[EMAIL]", "phone": "[PHONE]", "ssn": "[SSN]"}

def redact(text: str) -> RedactionResult:
    summary: dict[str, int] = {}
    out = text
    for kind, pattern in _PATTERNS.items():
        matches = pattern.findall(out)
        if matches:
            summary[kind] = len(matches)
            out = pattern.sub(_PLACEHOLDER[kind], out)
    return RedactionResult(redacted_text=out, summary=summary)
