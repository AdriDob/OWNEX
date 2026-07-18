"""Tests for Widget Dashboard system — backend endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api.main import app
    from cores.license.validator import generate_license

    c = TestClient(app, raise_server_exceptions=False)
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    resp = c.post("/api/auth/login", json={"device_id": "pytest-widget"})
    if resp.status_code == 200:
        token = resp.json()["data"]["token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def test_list_widgets_returns_200(client):
    resp = client.get("/api/core/widgets")
    assert resp.status_code == 200


def test_list_widgets_structure(client):
    resp = client.get("/api/core/widgets")
    data = resp.json()
    assert "widgets" in data
    assert "total" in data
    assert isinstance(data["widgets"], list)
    assert data["total"] == len(data["widgets"])


def test_list_widgets_has_expected_types(client):
    resp = client.get("/api/core/widgets")
    data = resp.json()
    ids = {w["id"] for w in data["widgets"]}
    expected = {
        "health-score",
        "active-targets",
        "findings-summary",
        "revenue-overview",
        "scheduler-status",
        "recent-activity",
        "knowledge-graph-mini",
        "top-priorities",
        "bounty-summary",
        "assistant-tip",
    }
    assert expected.issubset(ids)


def test_widget_definition_fields(client):
    resp = client.get("/api/core/widgets")
    data = resp.json()
    for widget in data["widgets"]:
        assert "id" in widget
        assert "name" in widget
        assert "description" in widget
        assert "icon" in widget
        assert "default_cols" in widget
        assert "default_rows" in widget
        assert "refresh_interval" in widget
