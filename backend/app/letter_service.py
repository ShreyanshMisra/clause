import re
from typing import Optional
from weasyprint import HTML, default_url_fetcher

_STYLE = (
    "body { font-family: Georgia, serif; color: #141413; margin: 1in; line-height: 1.5; }"
    " h1 { color: #CC785C; font-size: 20px; }"
    " h2 { color: #CC785C; font-size: 14px; margin-top: 24px; }"
    " table.damages { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }"
    " table.damages th, table.damages td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }"
    " table.damages td.amt { text-align: right; white-space: nowrap; }"
    " table.damages tr.total td { font-weight: bold; border-top: 2px solid #999; }"
)


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _damages_table(rows: list[tuple[str, str, float]]) -> str:
    """Render the damages table deterministically from our own data (not the LLM),
    so the figures in the letter always match the analysis."""
    if not rows:
        return ""
    body = ""
    total = 0.0
    for category, citation, amount in rows:
        total += amount or 0
        body += (f"<tr><td>{_esc(category)}</td><td>{_esc(citation)}</td>"
                 f"<td class='amt'>${amount:,.0f}</td></tr>")
    body += (f"<tr class='total'><td colspan='2'>Total demanded</td>"
             f"<td class='amt'>${total:,.0f}</td></tr>")
    return ("<h2>Statutory damages</h2><table class='damages'>"
            "<thead><tr><th>Issue</th><th>Statute</th><th>Amount</th></tr></thead>"
            f"<tbody>{body}</tbody></table>")

# Strip tags that can execute or pull in external/local resources. Defense in depth on
# top of the url_fetcher below, since the letter body is LLM-generated (untrusted).
_DANGEROUS_TAGS = re.compile(
    r"<\s*/?\s*(script|iframe|object|embed|link|meta|base|style)\b[^>]*>", re.IGNORECASE
)


def _blocking_url_fetcher(url: str):
    """Block SSRF/LFI: refuse to fetch any external or file:// resource.

    A demand letter needs no remote assets, so only inline data: URIs are allowed.
    This stops crafted HTML (e.g. <img src="file:///etc/passwd"> or an internal URL)
    from causing WeasyPrint to read local files or reach internal services.
    """
    if url.startswith("data:"):
        return default_url_fetcher(url)
    raise ValueError("External resource fetching is disabled")


def build_letter_html(body_html: str, title: str = "Demand Letter",
                      damages_rows: Optional[list[tuple[str, str, float]]] = None) -> str:
    """Assemble the full letter HTML: sanitized LLM prose plus a deterministic
    damages table. Exposed separately so it can be unit-tested without WeasyPrint."""
    safe_body = _DANGEROUS_TAGS.sub("", body_html or "")
    safe_title = (title or "").replace("<", "&lt;").replace(">", "&gt;")
    damages_html = _damages_table(damages_rows or [])
    # Build without str.format so literal braces in the LLM output can't break rendering.
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        + _STYLE
        + "</style></head><body><h1>"
        + safe_title
        + "</h1>"
        + safe_body
        + damages_html
        + "</body></html>"
    )


def render_letter_pdf(body_html: str, title: str = "Demand Letter",
                      damages_rows: Optional[list[tuple[str, str, float]]] = None) -> bytes:
    html = build_letter_html(body_html, title, damages_rows)
    return HTML(string=html, url_fetcher=_blocking_url_fetcher, base_url=None).write_pdf()
