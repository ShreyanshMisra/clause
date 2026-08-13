from app.letter_service import render_letter_pdf

def test_render_letter_returns_pdf_bytes():
    pdf = render_letter_pdf("<p>Dear Landlord, please return my deposit.</p>",
                            title="Demand Letter")
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500
