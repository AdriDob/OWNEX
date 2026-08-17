"""Tests for Mobile COPILOT endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_mobile_copilot_chat(client):
    """Test mobile COPILOT chat endpoint."""
    response = client.post(
        "/mobile/copilot/chat",
        json={"messages": [{"role": "user", "content": "hola"}]},
    )
    # Should return 200 even if providers fail (fallback to rule-based)
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "provider" in data
    assert "duration_ms" in data


def test_mobile_copilot_decision(client):
    """Test mobile COPILOT decision endpoint."""
    response = client.post(
        "/mobile/copilot/decision",
        json={"messages": [{"role": "user", "content": "qué hacer ahora?"}]},
    )
    # Should return 200 even if providers fail (fallback to rule-based)
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "provider" in data


def test_mobile_copilot_approve(client):
    """Test mobile COPILOT approve endpoint."""
    response = client.post(
        "/mobile/copilot/approve",
        json={"decision_id": "test-123", "approved": True, "reason": "looks good"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision_id"] == "test-123"
    assert data["approved"] is True
    assert data["status"] == "approved"


def test_mobile_providers_status(client):
    """Test mobile providers health check endpoint."""
    response = client.get("/mobile/providers/status")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "total" in data
    assert "available" in data
    # Should have at least the COPILOT providers
    assert len(data["providers"]) >= 6  # devin, freebuff, opencode, fcc, nvidia, ollama
