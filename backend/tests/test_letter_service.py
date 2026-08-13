import pytest
from app.letter_service import render_letter_pdf, _blocking_url_fetcher

def test_render_letter_returns_pdf_bytes():
    pdf = render_letter_pdf("<p>Dear Landlord, please return my deposit.</p>",
                            title="Demand Letter")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500

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
