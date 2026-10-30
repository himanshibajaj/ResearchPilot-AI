
from src.main import verify_citations


def test_all_citations_exist():
    report = "Benefits [S1] and risks [S2]."
    evidence = [
        {"id": "S1"},
        {"id": "S2"},
    ]

    result = verify_citations(report, evidence)

    assert result["status"] == "passed"
    assert result["invalid_citations"] == []


def test_unknown_citation_detected():
    report = "This claim uses [S3]."
    evidence = [
        {"id": "S1"},
        {"id": "S2"},
    ]

    result = verify_citations(report, evidence)

    assert result["status"] == "warning"
    assert result["invalid_citations"] == ["S3"]


def test_uncited_source_reported():
    report = "This claim uses [S1]."
    evidence = [
        {"id": "S1"},
        {"id": "S2"},
    ]

    result = verify_citations(report, evidence)

    assert result["uncited_source_ids"] == ["S2"]
