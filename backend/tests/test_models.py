from app.models import Finding, HighlightPosition, BoundingRect, Severity, COLOR_BY_SEVERITY

def test_color_by_severity_maps_all():
    assert COLOR_BY_SEVERITY[Severity.illegal] == "red"
    assert COLOR_BY_SEVERITY[Severity.high] == "orange"
    assert COLOR_BY_SEVERITY[Severity.medium] == "yellow"
    assert COLOR_BY_SEVERITY[Severity.favorable] == "green"

def test_finding_serializes_camel_fields():
    pos = HighlightPosition(
        boundingRect=BoundingRect(x1=1, y1=2, x2=3, y2=4, width=612, height=792, pageNumber=1),
        rects=[BoundingRect(x1=1, y1=2, x2=3, y2=4, width=612, height=792, pageNumber=1)],
        pageWidth=612, pageHeight=792,
    )
    f = Finding(id="f1", page=1, quoted_text="x", category="Deposit",
                severity=Severity.illegal, color="red", statute_citation="M.G.L. c.186",
                explanation="why", damages_estimate=100.0, position=pos)
    assert f.model_dump()["position"]["boundingRect"]["pageNumber"] == 1
