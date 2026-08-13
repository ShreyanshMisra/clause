import re
from weasyprint import HTML, default_url_fetcher

_STYLE = (
    "body { font-family: Georgia, serif; color: #141413; margin: 1in; line-height: 1.5; }"
    " h1 { color: #CC785C; font-size: 20px; }"
)

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


def render_letter_pdf(body_html: str, title: str = "Demand Letter") -> bytes:
    safe_body = _DANGEROUS_TAGS.sub("", body_html or "")
    safe_title = (title or "").replace("<", "&lt;").replace(">", "&gt;")
    # Build without str.format so literal braces in the LLM output can't break rendering.
    html = (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        + _STYLE
        + "</style></head><body><h1>"
        + safe_title
        + "</h1>"
        + safe_body
        + "</body></html>"
    )
    return HTML(string=html, url_fetcher=_blocking_url_fetcher, base_url=None).write_pdf()
