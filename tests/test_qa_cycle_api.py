"""Tests for the QA Testing Cycle API router."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.routers.qa_cycle as qa_module


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(qa_module.router)
    return TestClient(app)


class TestQaCycleApi:
    def setup_method(self) -> None:
        fake = MagicMock()
        fake.start_cycle.return_value = MagicMock(id=1, name="QA Testing", status="running")
        fake.get_cycle_status.return_value = {
            "cycle": {"id": 1, "name": "QA Testing", "status": "running"},
            "stages": ["test_plan", "test_execution", "evidence", "report", "follow_up"],
            "metrics": {},
        }
        fake.ensure_cycle.return_value = MagicMock(id=1)
        fake.advance_stage.return_value = MagicMock()
        fake.advance_stage.return_value.name = "Test Execution"
        fake.generate_test_cases.return_value.to_dict.return_value = {
            "name": "QA Auto-Suite",
            "test_cases": [{"title": "Target reachability"}],
        }
        fake.run_full_qa_cycle.return_value = {
            "cycle_id": 1,
            "report": {"pass_rate": 0.9, "total_tests": 10},
        }
        qa_module.qa_cycle = fake
        self.fake = fake

    def test_start(self) -> None:
        response = _client().post("/api/cycles/qa/start")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_status(self) -> None:
        response = _client().get("/api/cycles/qa/status")
        assert response.status_code == 200
        assert response.json()["cycle"]["id"] == 1
        assert len(response.json()["stages"]) == 5

    def test_advance_stage(self) -> None:
        response = _client().put("/api/cycles/qa/stage/test_plan")
        assert response.status_code == 200
        assert response.json()["next"] == "Test Execution"

    def test_advance_stage_not_found(self) -> None:
        self.fake.advance_stage.return_value = None
        response = _client().put("/api/cycles/qa/stage/missing")
        assert response.status_code == 404

    def test_generate_cases(self) -> None:
        response = _client().post("/api/cycles/qa/cases", json={"target_ids": [1]})
        assert response.status_code == 200
        assert response.json()["name"] == "QA Auto-Suite"
        self.fake.generate_test_cases.assert_called_once_with(
            target_ids=[1], endpoint_ids=None, finding_ids=None, include_regression=True
        )

    def test_run_full_cycle(self) -> None:
        response = _client().post("/api/cycles/qa/run")
        assert response.status_code == 200
        assert response.json()["report"]["pass_rate"] == 0.9

    def test_run_full_cycle_failure_is_500(self) -> None:
        self.fake.run_full_qa_cycle.side_effect = RuntimeError("boom")
        response = _client().post("/api/cycles/qa/run")
        assert response.status_code == 500
        assert "boom" in response.json()["detail"]
