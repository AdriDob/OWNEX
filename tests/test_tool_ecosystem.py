"""Tests for the Tool Ecosystem Management layer (FINALIZATION PROTOCOL)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.stability import router as stability_router
from cores.tools.ecosystem import ToolEcosystem, ToolUsageTracker


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(stability_router)
    return TestClient(app)


class TestToolUsageTracker:
    def test_records_and_persists(self, tmp_path: Path) -> None:
        tracker = ToolUsageTracker(tmp_path / "usage.json")
        tracker.record("nuclei")
        tracker.record("nuclei")
        tracker.record("httpx")

        reloaded = ToolUsageTracker(tmp_path / "usage.json")
        assert reloaded.frequency() == {"nuclei": 2, "httpx": 1}
        assert reloaded.snapshot() == {"nuclei": 2, "httpx": 1}

    def test_missing_file_starts_empty(self, tmp_path: Path) -> None:
        tracker = ToolUsageTracker(tmp_path / "none.json")
        assert tracker.frequency() == {}

    def test_corrupt_state_degrades_to_empty(self, tmp_path: Path) -> None:
        state = tmp_path / "usage.json"
        state.write_text("{not json", encoding="utf-8")
        tracker = ToolUsageTracker(state)
        assert tracker.frequency() == {}


class TestToolEcosystem:
    def test_inventory_covers_registered_tools(self, tmp_path: Path) -> None:
        ecosystem = ToolEcosystem(ToolUsageTracker(tmp_path / "usage.json"))
        rows = ecosystem.inventory()

        assert len(rows) >= 19
        for row in rows:
            assert row["name"]
            assert row["decision"] in {"keep", "remove"}
            assert row["license"]
            assert row["security_status"]
            assert row["usage_frequency"] >= 0

    def test_usage_frequency_reflected_in_inventory(self, tmp_path: Path) -> None:
        tracker = ToolUsageTracker(tmp_path / "usage.json")
        tracker.record("nuclei")
        tracker.record("nuclei")

        rows = ToolEcosystem(tracker).inventory()
        nuclei = next(r for r in rows if r["name"] == "nuclei")
        assert nuclei["usage_frequency"] == 2

    def test_summary_shapes(self, tmp_path: Path) -> None:
        summary = ToolEcosystem(ToolUsageTracker(tmp_path / "usage.json")).summary()
        assert summary["total"] >= 19
        assert "keep" in summary
        assert "remove_candidates" in summary
        assert summary["keep"] + len(summary["remove_candidates"]) == summary["total"]


class TestToolEcosystemApi:
    def test_tools_endpoint_returns_inventory(self) -> None:
        response = _client().get("/api/stability/tools")
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["total"] >= 19
        assert len(payload["tools"]) >= 19
        required = {
            "name",
            "purpose",
            "version",
            "license",
            "security_status",
            "usage_frequency",
            "maintenance_cost",
            "installed",
            "decision",
        }
        assert required.issubset(payload["tools"][0].keys())
        assert "generated_at" in payload
