"""Tests for the hunt router — live-scheduler kickoff semantics.

Regression guard: POST /api/hunt/start must kick a pipeline cycle on the
running ScanScheduler instance (api.scheduler.scheduler_instance), never
create a second scheduler with empty cooldown/last_run state.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.hunt import router as hunt_router

app = FastAPI()
app.include_router(hunt_router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_hunt_state() -> None:
    from api.routers import hunt

    hunt._hunt_state["status"] = "idle"
    hunt._hunt_state["started_at"] = None
    yield


class _FakeScheduler:
    def __init__(self) -> None:
        self.cycles = 0

    async def run_cycle(self) -> None:
        self.cycles += 1


def test_start_reuses_live_scheduler_instance(monkeypatch) -> None:
    from api import scheduler as sched_mod

    fake = _FakeScheduler()
    monkeypatch.setattr(sched_mod, "scheduler_instance", fake)

    resp = client.post("/api/hunt/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    # The live instance ran exactly one cycle; no new ScanScheduler was created.
    assert fake.cycles == 1
    assert sched_mod.scheduler_instance is fake


def test_start_falls_back_when_no_live_instance(monkeypatch) -> None:
    from api import scheduler as sched_mod
    from api.scheduler import ScanScheduler

    monkeypatch.setattr(sched_mod, "scheduler_instance", None)

    async def _noop_run_cycle(self) -> None:  # noqa: ANN001
        pass

    monkeypatch.setattr(ScanScheduler, "run_cycle", _noop_run_cycle)

    resp = client.post("/api/hunt/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    # Fallback registered the ad-hoc instance so subsequent triggers reuse it.
    assert sched_mod.scheduler_instance is not None


def test_start_already_running() -> None:
    from api.routers import hunt

    hunt._hunt_state["status"] = "running"
    resp = client.post("/api/hunt/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_running"
