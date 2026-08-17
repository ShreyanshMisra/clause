import pytest
from app.letter_service import build_letter_html, render_letter_pdf, _blocking_url_fetcher

def test_render_letter_returns_pdf_bytes():
    pdf = render_letter_pdf("<p>Dear Landlord, please return my deposit.</p>",
                            title="Demand Letter")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500

def test_damages_table_renders_rows_and_total():
    html = build_letter_html(
        "<p>body</p>", title="Demand Letter",
        damages_rows=[("Security deposit", "M.G.L. c.186 § 15B", 4500.0),
                      ("Quiet enjoyment", "M.G.L. c.186 § 14", 6000.0)])
    assert "Statutory damages" in html
    assert "$4,500" in html and "$6,000" in html
    assert "Total demanded" in html and "$10,500" in html

def test_no_damages_table_when_no_rows():
    html = build_letter_html("<p>body</p>", damages_rows=[])
    assert "Statutory damages" not in html

def test_damages_table_escapes_cell_values():
    html = build_letter_html("<p>b</p>", damages_rows=[("<script>", "cite", 100.0)])
    assert "<script>" not in html and "&lt;script&gt;" in html

def test_url_fetcher_blocks_file_and_http():
    with pytest.raises(ValueError):
        _blocking_url_fetcher("file:///etc/passwd")
    with pytest.raises(ValueError):
        _blocking_url_fetcher("http://169.254.169.254/latest/meta-data/")

def test_render_letter_strips_dangerous_tags_and_survives_braces():
    # Untrusted body with a script tag, a local-file image, and literal braces.
    body = '<p>hi {not_a_placeholder}</p><script>alert(1)</script>' \
           '<img src="file:///etc/passwd">'
    pdf = render_letter_pdf(body, title="<b>x</b>")
    assert pdf[:4] == b"%PDF"
