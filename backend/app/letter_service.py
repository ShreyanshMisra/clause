from weasyprint import HTML

_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; color: #141413; margin: 1in; line-height: 1.5; }}
  h1 {{ color: #CC785C; font-size: 20px; }}
</style></head>
<body><h1>{title}</h1>{body}</body></html>"""

def render_letter_pdf(body_html: str, title: str = "Demand Letter") -> bytes:
    html = _TEMPLATE.format(title=title, body=body_html)
    return HTML(string=html).write_pdf()
