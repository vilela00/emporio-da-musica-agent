from emporio.quality import findings, report


def test_known_anomalies_are_found(store):
    found = {f.code: " ".join(f.evidence) for f in findings(store)}
    assert "#135" in found["A-01"] and "#142" in found["A-01"]
    assert "#130" in found["A-02"]
    assert "#136" in found["A-03"]
    assert "order #3" in found["A-05"] and "order #20" in found["A-05"]
    assert all(f"order #{n}:" in found["A-06"] for n in (9, 16, 18))
    assert "bruno.martins@jmail.com" in found["A-08"]
    assert "Instrumentos de Sopro (Madeiras)" in found["A-12"]
    assert "order #8" in found["A-16"]


def test_report_renders(store):
    assert report(store).startswith("# Data quality report")
