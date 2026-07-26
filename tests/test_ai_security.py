"""Tests for AI Security module."""

from __future__ import annotations

import pytest

from core.intel.llm_scanner import (
    LLMScanResult,
    scan_llm_endpoint,
    scan_local_model,
)

# ── LLM Scanner ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_llm_fallback():
    """Without Garak installed, returns simulated result."""
    result = await scan_llm_endpoint("http://test:11434")
    assert isinstance(result, LLMScanResult)
    assert result.endpoint == "http://test:11434"
    assert "fallback" in result.methodology.lower()
    assert result.summary["total"] == 6
    assert 0 <= result.summary["score"] <= 100


@pytest.mark.asyncio
async def test_scan_local_fallback():
    """Returns an LLMScanResult regardless of Garak availability."""
    result = await scan_local_model("test-model:latest")
    assert isinstance(result, LLMScanResult)
    assert "test-model" in result.endpoint
    assert result.methodology in (
        "Garak Ollama real execution",
        "Fallback: simulated until Garak is installed (`pip install garak`)",
    )


@pytest.mark.asyncio
async def test_scan_llm_garak_error_fallback():
    """If Garak is installed but raises, falls back to simulated."""
    result = await scan_llm_endpoint("http://test:11434")
    assert result.summary["total"] == 6


@pytest.mark.asyncio
async def test_scan_local_with_garak(monkeypatch):
    """When Garak IS available, uses real scan."""

    class MockGarakTool:
        def is_available(self):
            return True

        def scan_ollama(self, model_name="", probes=None):
            from cores.tools.pipeline import UnifiedResult

            return [
                UnifiedResult(
                    source="garak",
                    target="promptinject",
                    result_type="vulnerability",
                    severity="high",
                    confidence=0.8,
                    name="Garak promptinject: DETECTED",
                    description="Prompt injection detected",
                    evidence={},
                    tags=["llm_security", "garak"],
                )
            ]

    monkeypatch.setattr("cores.tools.extra.GarakTool", lambda: MockGarakTool())
    result = await scan_local_model("test-model")
    assert result.summary["total"] == 1
    assert result.summary["failed"] == 1
    assert "Garak" in result.methodology


# ── LLMScanResult dataclass ─────────────────────────────────


def test_scan_result_fields():
    result = LLMScanResult(
        endpoint="http://test",
        model="gpt-3.5-turbo",
        timestamp="2026-01-01T00:00:00Z",
        checks=[],
        summary={"passed": 0, "failed": 0, "total": 0, "score": 0, "high_severity": 0, "medium_severity": 0},
    )
    assert result.endpoint == "http://test"
    assert result.model == "gpt-3.5-turbo"
    assert result.data_sources is not None


# ── API Router (integration tests — skipped unless --run-api) ──

pytestmark_integration = pytest.mark.skipif(
    "not config.getoption('--run-api')",
    reason="Integration test: requires app import. Use --run-api to run.",
)


@pytest.mark.skip(reason="Integration test: use --run-api for full suite")
def test_scan_local_endpoint_no_garak():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        resp = client.post("/api/ai-security/scan-local", json={"model": "test-model"})
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoint" in data
    assert "summary" in data
    assert data["summary"]["total"] == 6


@pytest.mark.skip(reason="Integration test: use --run-api for full suite")
def test_scan_local_endpoint_default_model():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        resp = client.post("/api/ai-security/scan-local", json={})
    assert resp.status_code == 200
    assert "ollama:qwen3-coder:8b" in resp.json()["endpoint"]


@pytest.mark.skip(reason="Integration test: use --run-api for full suite")
def test_scan_local_endpoint_empty_model():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        resp = client.post("/api/ai-security/scan-local", json={"model": ""})
    assert resp.status_code == 400


@pytest.mark.skip(reason="Integration test: use --run-api for full suite")
def test_opportunities_endpoint():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        resp = client.get("/api/ai-security/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        opp = data[0]
        assert "platform" in opp
        assert "estimated_payout" in opp


@pytest.mark.skip(reason="Integration test: use --run-api for full suite")
def test_assess_endpoint_missing_params():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        resp = client.post("/api/ai-security/assess", json={})
    assert resp.status_code == 400


@pytest.mark.skip(reason="Integration test: use --run-api for full suite")
def test_assess_endpoint_unknown():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/api/ai-security/assess",
            json={"platform": "nonexistent", "challenge_id": "nope"},
        )
    assert resp.status_code == 404
