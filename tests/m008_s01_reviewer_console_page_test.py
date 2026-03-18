from __future__ import annotations

from fastapi.testclient import TestClient

from sps.api.main import app


def test_reviewer_console_page_loads() -> None:
    client = TestClient(app)

    resp = client.get("/reviewer")

    assert resp.status_code == 200
    body = resp.text
    assert "Reviewer Console" in body
    assert "id=\"reviewer-console\"" in body
    assert "id=\"reviewer-api-key\"" in body
    assert "Legacy API Key" in body
    assert "No protected data loads until you provide a legacy/manual reviewer key." in body
    assert "id=\"queue-panel\"" in body
    assert "id=\"evidence-panel\"" in body
    assert "id=\"decision-panel\"" in body
    assert "id=\"decision-submit\"" in body
    assert "id=\"banner-error\"" in body
    assert "id=\"banner-success\"" in body
    assert "all protected reads and writes stay behind API auth" in body
