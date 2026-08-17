import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.pii_llm import llm_pii_spans
from app.redaction_map import RedactionSpan

# Optional fast-model client for the LLM PII assist layer, injected at startup
# (see main._init_services). None keeps redaction pure/regex+NER-only for tests.
_pii_client: Any = None


def set_pii_client(client: Any) -> None:
    global _pii_client
    _pii_client = client


def _llm_assist_enabled() -> bool:
    return (_pii_client is not None
            and os.environ.get("PII_LLM_ASSIST", "").lower() in ("1", "true", "yes", "on"))


@dataclass
class RedactionResult:
    redacted_text: str
    summary: dict = field(default_factory=dict)
    spans: list[RedactionSpan] = field(default_factory=list)


# Regex layer: catches structured PII (and street addresses, which Presidio's default
# recognizers miss). Multi-field patterns (CREDIT_CARD, ADDRESS) are listed before the
# narrower number patterns so overlap-resolution keeps the wider, more specific span.
_REGEX = {
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "PHONE": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ADDRESS": re.compile(
        r"\b\d{1,6}\s+(?:[A-Za-z0-9.'-]+\s+){0,4}"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|"
        r"Way|Place|Pl|Terrace|Ter|Circle|Cir|Highway|Hwy)\b\.?"
        # Optional unit and city/state/ZIP tail so a full mailing address is one span.
        r"(?:\s*,?\s*(?:Apt|Apartment|Unit|Suite|Ste|Rm|Room|#)\s*\.?\s*[A-Za-z0-9-]+)?"
        r"(?:\s*,\s*[A-Za-z .'-]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)?",
        re.IGNORECASE,
    ),
    "PO_BOX": re.compile(r"\bP\.?\s*O\.?\s*Box\s+\d+\b", re.IGNORECASE),
}

# Presidio NER entity -> placeholder label shown to the user.
_ENTITY_PLACEHOLDER = {
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "US_SSN": "SSN",
}
_NER_ENTITIES = list(_ENTITY_PLACEHOLDER.keys())

# NER confidence floor. For a privacy tool recall matters more than precision
# (over-redaction is safe, a leak is not), so the default leans permissive and the
# allowlist below rescues common lease-term false positives. Tunable via env.
_NER_SCORE_THRESHOLD = float(os.environ.get("PII_NER_SCORE_THRESHOLD", 0.35))

# spaCy mislabels lease defined-terms and the jurisdiction as PERSON/LOCATION. Keeping these
# preserves the meaning the LLM needs (and they aren't personal identifiers).
_ALLOWLIST = {
    "tenant", "tenants", "landlord", "landlords", "lessor", "lessee", "owner", "owners",
    "agent", "manager", "management", "occupant", "occupants", "resident", "residents",
    "premises", "property", "unit", "apartment", "building", "lease", "agreement",
    "guarantor", "subtenant", "sublessee", "co-tenant", "cotenant", "company", "landlord's",
    "tenant's", "lessor's", "lessee's", "owner's", "security", "deposit", "rent",
    "massachusetts", "commonwealth", "the commonwealth", "united states", "u.s.", "america",
}


def _allowed(span: str) -> bool:
    return span.strip().strip(".,'’").rstrip("s").lower() in _ALLOWLIST or span.strip().lower() in _ALLOWLIST


_analyzer: Any = None
_ner_unavailable = False


def _get_ner():
    """Lazily build the Presidio analyzer (spaCy en_core_web_sm).

    Cached across calls. If Presidio or the model isn't installed, returns None and the
    caller falls back to regex-only redaction."""
    global _analyzer, _ner_unavailable
    if _ner_unavailable:
        return None
    if _analyzer is not None:
        return _analyzer
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        })
        _analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
        return _analyzer
    except Exception:
        _ner_unavailable = True
        return None


def _collect_spans(text: str) -> list[tuple[int, int, str]]:
    """Gather candidate (start, end, entity_type) matches on the ORIGINAL text from
    both the regex layer and Presidio NER, before overlap-resolution."""
    raw: list[tuple[int, int, str]] = []
    for kind, pattern in _REGEX.items():
        for m in pattern.finditer(text):
            raw.append((m.start(), m.end(), kind))
    analyzer = _get_ner()
    if analyzer is not None:
        for r in analyzer.analyze(text=text, entities=_NER_ENTITIES, language="en"):
            if r.score >= _NER_SCORE_THRESHOLD and not _allowed(text[r.start:r.end]):
                raw.append((r.start, r.end, _ENTITY_PLACEHOLDER.get(r.entity_type, r.entity_type)))
    if _llm_assist_enabled():
        for s in llm_pii_spans(text, _pii_client):
            if not _allowed(text[s.start:s.end]):
                raw.append((s.start, s.end, s.entity_type))
    return raw


def _resolve_overlaps(raw: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Greedily keep non-overlapping spans, preferring earlier start then longer span."""
    raw.sort(key=lambda t: (t[0], -(t[1] - t[0])))
    kept: list[tuple[int, int, str]] = []
    last_end = -1
    for start, end, et in raw:
        if start >= last_end:
            kept.append((start, end, et))
            last_end = end
    return kept


def redact(text: str) -> RedactionResult:
    """Redact PII before the text reaches the LLM / Cortex.

    Offset-based: PII is detected on the ORIGINAL text (regex + Presidio/spaCy NER),
    overlaps are resolved, and each removed span gets a *consistent* placeholder
    (same value -> same `[TYPE_n]`). Returns the redacted text, a per-type count
    summary, and the list of `RedactionSpan`s (original offsets) so callers can map
    an LLM's redacted quote back to the source text for PDF highlighting."""
    kept = _resolve_overlaps(_collect_spans(text))

    placeholders: dict[tuple[str, str], int] = {}
    spans: list[RedactionSpan] = []
    summary: dict[str, int] = {}
    for start, end, et in kept:
        original = text[start:end]
        key = (et, original.strip().lower())
        if key not in placeholders:
            placeholders[key] = sum(1 for k in placeholders if k[0] == et) + 1
        placeholder = f"[{et}_{placeholders[key]}]"
        spans.append(RedactionSpan(start=start, end=end, placeholder=placeholder,
                                   entity_type=et, original=original))
        summary[et] = summary.get(et, 0) + 1

    out = text
    for s in sorted(spans, key=lambda s: s.start, reverse=True):
        out = out[:s.start] + s.placeholder + out[s.end:]
    return RedactionResult(redacted_text=out, summary=summary, spans=spans)
