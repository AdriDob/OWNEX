"""Tests for the Internal Dev Agent (repo's own queue).

Propose is read-only; build needs a real single-use approval token.
Bridge is faked (no opencode binary needed); approval tokens are real.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.internal_dev import router
from cores.autonomy.internal_dev import (
    DevQueue,
    approve_and_build,
    run_internal_dev_propose,
)

app = FastAPI()
app.include_router(router)


class FakeBridge:
    def __init__(self, files_changed: list[str] | None = None, success: bool = True) -> None:
        self.files_changed = files_changed or []
        self.success = success
        self.calls: list[str] = []

    async def propose(self, description: str) -> dict:
        self.calls.append("propose")
        return {"run_id": "run_p1", "output": f"PLAN: {description[:60]}", "success": True}

    async def implement(self, description: str) -> dict:
        self.calls.append("implement")
        return {"run_id": "run_b1", "success": self.success, "files_changed": self.files_changed}

    async def fix(self, description: str) -> dict:
        self.calls.append("fix")
        return await self.implement(description)

    async def refactor(self, description: str) -> dict:
        self.calls.append("refactor")
        return await self.implement(description)


@pytest.fixture()
def queue(tmp_path, monkeypatch):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    return DevQueue()


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    return TestClient(app)


def _token() -> str:
    from cores.automation.safety import issue_approval

    return issue_approval("opencode:execute", "repo")


class TestDevQueue:
    def test_add_get_list_roundtrip(self, queue: DevQueue) -> None:
        task = queue.add("fix", "Arreglar X", ["cores/a.py"], "true")
        assert task.status == "queued"
        fetched = queue.get(task.id)
        assert fetched is not None and fetched.description == "Arreglar X"
        assert len(queue.list()) == 1
        assert len(queue.list(status="queued")) == 1

    def test_add_rejects_bad_kind_and_empty(self, queue: DevQueue) -> None:
        with pytest.raises(ValueError):
            queue.add("deploy", "X")
        with pytest.raises(ValueError):
            queue.add("fix", "   ")

    def test_reload_survives(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        first = DevQueue()
        task = first.add("implement", "Y")
        assert DevQueue().get(task.id) is not None


class TestProposeCycle:
    async def _run(self, queue, bridge):
        import asyncio

        return asyncio.new_event_loop().run_until_complete(run_internal_dev_propose(queue, bridge))

    def test_empty_queue(self, queue: DevQueue) -> None:
        import asyncio

        out = asyncio.new_event_loop().run_until_complete(run_internal_dev_propose(queue, FakeBridge()))
        assert out == {"proposed": 0, "reason": "cola vacía"}

    def test_propose_parks_oldest(self, queue: DevQueue) -> None:
        import asyncio

        queue.add("implement", "Primera")
        queue.add("fix", "Segunda")
        out = asyncio.new_event_loop().run_until_complete(run_internal_dev_propose(queue, FakeBridge()))
        assert out["proposed"] == 1
        tasks = queue.list()
        assert tasks[0].status == "proposed" and tasks[0].proposal.startswith("PLAN:")
        assert tasks[1].status == "queued"


class TestApproveBuild:
    def test_bad_token_rejected(self, queue: DevQueue) -> None:
        import asyncio

        task = queue.add("fix", "X", [], "true")
        out = asyncio.new_event_loop().run_until_complete(approve_and_build(task.id, "nope", queue, FakeBridge()))
        assert out["ok"] is False and "approval_token" in out["error"]
        fetched = queue.get(task.id)
        assert fetched is not None and fetched.status == "queued"  # intacto

    def test_unknown_task(self, queue: DevQueue) -> None:
        import asyncio

        out = asyncio.new_event_loop().run_until_complete(approve_and_build("nope", _token(), queue, FakeBridge()))
        assert out["ok"] is False

    def test_happy_path_done(self, queue: DevQueue) -> None:
        import asyncio

        task = queue.add("fix", "X", ["cores/a.py"], "true")
        bridge = FakeBridge(files_changed=["cores/a.py"])
        out = asyncio.new_event_loop().run_until_complete(approve_and_build(task.id, _token(), queue, bridge))
        assert out["ok"] is True
        fetched = queue.get(task.id)
        assert fetched is not None and fetched.status == "done"

    def test_out_of_scope_failed(self, queue: DevQueue) -> None:
        import asyncio

        task = queue.add("fix", "X", ["cores/a.py"], "true")
        bridge = FakeBridge(files_changed=["api/routers/other.py"])
        out = asyncio.new_event_loop().run_until_complete(approve_and_build(task.id, _token(), queue, bridge))
        assert out["ok"] is False and "fuera de scope" in out["error"]
        fetched = queue.get(task.id)
        assert fetched is not None and fetched.status == "failed"

    def test_token_single_use(self, queue: DevQueue) -> None:
        import asyncio

        task = queue.add("fix", "X", [], "true")
        tok = _token()
        first = asyncio.new_event_loop().run_until_complete(approve_and_build(task.id, tok, queue, FakeBridge()))
        assert first["ok"] is True
        task2 = queue.add("fix", "Y", [], "true")
        second = asyncio.new_event_loop().run_until_complete(approve_and_build(task2.id, tok, queue, FakeBridge()))
        assert second["ok"] is False


class TestInternalDevApi:
    def test_add_list_propose_approve_flow(self, api_client: TestClient, monkeypatch) -> None:
        import cores.autonomy.internal_dev as dev_mod

        class QB:
            async def propose(self, description: str) -> dict:
                return {"run_id": "r", "output": "PLAN mock", "success": True}

        async def _fake_propose(queue=None, bridge=None):  # type: ignore[no-untyped-def]
            return await run_internal_dev_propose(queue, QB())

        monkeypatch.setattr(dev_mod, "run_internal_dev_propose", _fake_propose)
        created = api_client.post("/api/internal-dev/dev-queue", json={"kind": "fix", "description": "X"})
        assert created.status_code == 201
        assert api_client.get("/api/internal-dev/dev-queue").json()["total"] == 1
        prop = api_client.post("/api/internal-dev/dev-queue/propose").json()
        assert prop["proposed"] == 1
        bad = api_client.post("/api/internal-dev/dev-queue", json={"kind": "deploy", "description": "X"})
        assert bad.status_code == 422
        # approve sin token válido → 422, tarea intacta
        tid = created.json()["id"]
        denied = api_client.post(f"/api/internal-dev/dev-queue/{tid}/approve", json={"approval_token": "nope"})
        assert denied.status_code == 422


class TestInternalDevJob:
    def test_job_registered_and_resolves(self) -> None:
        import importlib

        from cores.scheduler.jobs import get_forge_jobs

        ids = [j.job_id for j in get_forge_jobs()]
        assert "forge_internal_dev_propose" in ids
        job = next(j for j in get_forge_jobs() if j.job_id == "forge_internal_dev_propose")
        handler_path: str = job.handler  # type: ignore[assignment]
        mod_name, attr = handler_path.rsplit(":", 1)
        assert callable(getattr(importlib.import_module(mod_name), attr))
