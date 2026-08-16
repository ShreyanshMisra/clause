import os
import re
from dataclasses import dataclass, field
from typing import Any

@dataclass
class RedactionResult:
    redacted_text: str
    summary: dict = field(default_factory=dict)


# Regex layer: catches structured PII (and street addresses, which Presidio's default
# recognizers miss). Runs before NER so full addresses/cards get a precise label first.
# Order matters: multi-field patterns (CREDIT_CARD, ADDRESS) run before the narrower
# PHONE/number patterns so they aren't chopped into partial matches.
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

# NER confidence floor. For a privacy tool, recall matters more than precision
# (over-redaction is safe; a leak is not), so the default leans permissive and the
# lease-term allowlist below rescues the common false positives. Tune via env.
_NER_SCORE_THRESHOLD = float(os.environ.get("PII_NER_SCORE_THRESHOLD", 0.35))

# Presidio NER entity -> placeholder label shown to the user.
_ENTITY_PLACEHOLDER = {
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "US_SSN": "SSN",
}
_NER_ENTITIES = list(_ENTITY_PLACEHOLDER.keys())

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
_anonymizer: Any = None
_operators: Any = None
_ner_unavailable = False


def _get_ner():
    """Lazily build the Presidio analyzer/anonymizer (spaCy en_core_web_sm).

    Cached across calls. If Presidio or the model isn't installed, returns None and the
    caller falls back to regex-only redaction."""
    global _analyzer, _anonymizer, _operators, _ner_unavailable
    if _ner_unavailable:
        return None
    if _analyzer is not None:
        return _analyzer
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        })
        _analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
        _anonymizer = AnonymizerEngine()
        _operators = {
            et: OperatorConfig("replace", {"new_value": f"[{ph}]"})
            for et, ph in _ENTITY_PLACEHOLDER.items()
        }
        return _analyzer
    except Exception:
        _ner_unavailable = True
        return None


def _redact_regex(text: str) -> tuple[str, dict]:
    summary: dict[str, int] = {}
    out = text
    for kind, pattern in _REGEX.items():
        matches = pattern.findall(out)
        if matches:
            summary[kind] = summary.get(kind, 0) + len(matches)
            out = pattern.sub(f"[{kind}]", out)
    return out, summary


def redact(text: str) -> RedactionResult:
    """Redact PII before the text reaches the LLM / Cortex.

    NER (Presidio + spaCy) removes names, locations, emails, phones, and SSNs; a regex
    pass then sweeps street addresses and any structured PII NER missed. The ORIGINAL
    text is never mutated by the caller — it's kept locally for PDF coordinate mapping."""
    # Structured PII first (emails, phones, SSNs, street addresses) so full addresses get
    # the ADDRESS label before NER would otherwise catch the street name as a LOCATION.
    out, summary = _redact_regex(text)

    analyzer = _get_ner()
    if analyzer is not None:
        results = analyzer.analyze(text=out, entities=_NER_ENTITIES, language="en")
        results = [r for r in results
                   if r.score >= _NER_SCORE_THRESHOLD and not _allowed(out[r.start:r.end])]
        if results:
            anon = _anonymizer.anonymize(text=out, analyzer_results=results, operators=_operators)
            out = anon.text
            for item in anon.items:
                ph = _ENTITY_PLACEHOLDER.get(item.entity_type, item.entity_type)
                summary[ph] = summary.get(ph, 0) + 1
    return RedactionResult(redacted_text=out, summary=summary)
