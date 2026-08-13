from dataclasses import dataclass
from typing import Optional
from app.models import Metadata, Parties
from app.vector_store import Statute

@dataclass
class FindingDraft:
    quoted_text: str
    page: int
    category: str
    severity: str
    statute_citation: Optional[str]
    explanation: str
    damages_estimate: Optional[float]

_META_PROMPT = (
    "Extract lease metadata as JSON with keys parties{{landlord,tenant,property}}, "
    "monthlyRent, leaseTerm, securityDeposit. Use empty strings if unknown.\n\nDOCUMENT:\n{text}"
)

_ANALYZE_PROMPT = (
    "You are a Massachusetts tenant-rights attorney. Given a lease CHUNK and relevant STATUTES, "
    "return JSON {{\"findings\": [ ... ]}} where each finding has quoted_text (verbatim from the "
    "chunk), page (integer — the CHUNK may span multiple pages delimited by lines like "
    "'=== PAGE N ==='; set page to the PAGE number where this finding's quoted_text appears), "
    "category, severity (one of illegal|high|medium|favorable), "
    "statute_citation, explanation, and damages_estimate: your best estimate of the tenant's "
    "potential dollar recovery for this violation under Massachusetts law (e.g. treble the "
    "security deposit under c.186 s.15B, up to three months' rent for quiet-enjoyment or "
    "retaliation violations), as a plain number with no symbols or commas. Only use null when a "
    "violation genuinely has no monetary remedy. Only flag real issues. "
    "Default page to {page_hint}.\n\nSTATUTES:\n{statutes}\n\nCHUNK:\n{chunk}"
)

class LLMService:
    def __init__(self, client) -> None:
        self._client = client

    def embed(self, text: str) -> list[float]:
        return self._client.embed(text)

    def extract_metadata(self, text: str) -> Metadata:
        data = self._client.generate_json(_META_PROMPT.format(text=text[:8000]))
        p = data.get("parties", {}) or {}
        return Metadata(
            parties=Parties(landlord=p.get("landlord", ""), tenant=p.get("tenant", ""),
                            property=p.get("property", "")),
            monthlyRent=data.get("monthlyRent", ""),
            leaseTerm=data.get("leaseTerm", ""),
            securityDeposit=data.get("securityDeposit", ""),
        )

    def analyze_chunk(self, chunk: str, statutes: list[Statute], page_hint: int = 1) -> list[FindingDraft]:
        statute_text = "\n".join(f"- {s.chapter} s.{s.section} {s.title}: {s.text}" for s in statutes)
        data = self._client.generate_json(
            _ANALYZE_PROMPT.format(statutes=statute_text, chunk=chunk, page_hint=page_hint))
        out = []
        for f in data.get("findings", []):
            out.append(FindingDraft(
                quoted_text=f.get("quoted_text", ""),
                page=int(f.get("page", page_hint) or page_hint),
                category=f.get("category", "General"),
                severity=f.get("severity", "medium"),
                statute_citation=f.get("statute_citation"),
                explanation=f.get("explanation", ""),
                damages_estimate=f.get("damages_estimate"),
            ))
        return out

    def draft_demand_letter(self, findings: list[FindingDraft], metadata: Metadata,
                            sender: dict, recipient: dict) -> str:
        issues = "\n".join(f"- {f.category} ({f.severity}): {f.explanation} "
                           f"[{f.statute_citation}]" for f in findings)
        prompt = (
            "Draft the BODY (HTML paragraphs only, no <html>/<head>) of a firm but professional "
            "demand letter from a Massachusetts tenant to a landlord citing these issues and "
            "requesting remedy within 30 days.\n\n"
            f"SENDER: {sender}\nRECIPIENT: {recipient}\nISSUES:\n{issues}"
        )
        return self._client.generate_text(prompt)
