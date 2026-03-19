from __future__ import annotations

from fastapi.testclient import TestClient

from sps.api.main import app
import sps.api.main as api_main


def test_readyz_reports_all_healthy(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "_check_postgres_ready", lambda: {"status": "ok"})
    monkeypatch.setattr(api_main, "_check_temporal_ready", lambda: {"status": "ok"})
    monkeypatch.setattr(api_main, "_check_storage_ready", lambda: {"status": "ok"})

    client = TestClient(app)
    response = client.get("/readyz")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"] == {
        "postgres": {"status": "ok"},
        "temporal": {"status": "ok"},
        "storage": {"status": "ok"},
    }


def test_readyz_fails_when_postgres_probe_fails(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "_check_postgres_ready", lambda: {"status": "error", "error": "DBDown"})
    monkeypatch.setattr(api_main, "_check_temporal_ready", lambda: {"status": "ok"})
    monkeypatch.setattr(api_main, "_check_storage_ready", lambda: {"status": "ok"})

    client = TestClient(app)
    response = client.get("/readyz")

    assert response.status_code == 503, response.text
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["checks"]["postgres"] == {"status": "error", "error": "DBDown"}
    assert payload["checks"]["temporal"] == {"status": "ok"}
    assert payload["checks"]["storage"] == {"status": "ok"}


def test_readyz_fails_when_temporal_probe_fails(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "_check_postgres_ready", lambda: {"status": "ok"})
    monkeypatch.setattr(
        api_main,
        "_check_temporal_ready",
        lambda: {"status": "error", "error": "TemporalUnavailable"},
    )
    monkeypatch.setattr(api_main, "_check_storage_ready", lambda: {"status": "ok"})

    client = TestClient(app)
    response = client.get("/readyz")

    assert response.status_code == 503, response.text
    payload = response.json()
    assert payload["checks"]["temporal"] == {
        "status": "error",
        "error": "TemporalUnavailable",
    }


def test_readyz_fails_when_storage_probe_fails(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "_check_postgres_ready", lambda: {"status": "ok"})
    monkeypatch.setattr(api_main, "_check_temporal_ready", lambda: {"status": "ok"})
    monkeypatch.setattr(api_main, "_check_storage_ready", lambda: {"status": "error", "error": "BucketMissing"})

    client = TestClient(app)
    response = client.get("/readyz")

    assert response.status_code == 503, response.text
    payload = response.json()
    assert payload["checks"]["storage"] == {"status": "error", "error": "BucketMissing"}


def test_readyz_reports_mixed_failures(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "_check_postgres_ready", lambda: {"status": "error", "error": "DBDown"})
    monkeypatch.setattr(
        api_main,
        "_check_temporal_ready",
        lambda: {"status": "error", "error": "TemporalUnavailable"},
    )
    monkeypatch.setattr(api_main, "_check_storage_ready", lambda: {"status": "ok"})

    client = TestClient(app)
    response = client.get("/readyz")

    assert response.status_code == 503, response.text
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["checks"]["postgres"]["error"] == "DBDown"
    assert payload["checks"]["temporal"]["error"] == "TemporalUnavailable"
    assert payload["checks"]["storage"] == {"status": "ok"}
