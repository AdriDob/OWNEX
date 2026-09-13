"""OpenCode bridge two-phase flow — subprocess mocked, no real runs."""

from __future__ import annotations

import pathlib
import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.copilot import router
from cores.copilot import opencode_bridge as ob

app = FastAPI()
app.include_router(router)
client = TestClient(app)


class FakeCompleted:
    def __init__(self, stdout="done", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


@pytest.fixture()
def fake_run(monkeypatch, tmp_path):
    """Capture opencode CLI invocations; fake success; isolate runs dir."""
    calls: dict = {}
    monkeypatch.setattr(ob, "_runs_dir", lambda: tmp_path)
    monkeypatch.setattr(ob, "PROJECT_DIR", tmp_path)

    def _fake(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["cwd"] = kwargs.get("cwd")
        return FakeCompleted(stdout="x" * 5000)

    monkeypatch.setattr(subprocess, "run", _fake)
    return calls


@pytest.fixture()
def bridge():
    return ob.OpenCodeBridge()


class TestBridgeContract:
    async def test_execute_prepends_agent_loop(self, bridge, fake_run):
        res = await bridge.run("Do the thing")
        assert res["success"] is True
        prompts = list(pathlib.Path(res["output_file"]).parent.glob("prompt.txt"))
        assert prompts
        text = prompts[0].read_text(encoding="utf-8")
        assert "AGENT_CHARTER" in text
        assert res["output_truncated"] is True  # 5000 > 3000 tail
        assert len(res["output"]) == 3000

    async def test_propose_is_readonly_prompt(self, bridge, fake_run):
        res = await bridge.propose("Add a widget")
        assert res["mode"] == "propose"
        prompt = next(pathlib.Path(res["output_file"]).parent.glob("prompt.txt"))
        assert "READ-ONLY" in prompt.read_text(encoding="utf-8")

    async def test_run_records_files_changed(self, bridge, fake_run, monkeypatch):
        monkeypatch.setattr(ob, "_git", lambda args, cwd: " M foo.py\n?? bar.py\n")
        res = await bridge.run("x")
        assert res["files_changed"] == ["bar.py", "foo.py"]
        assert "diff_stat" in res and "diff_file" in res

    async def test_timeout_shape(self, bridge, monkeypatch, tmp_path):
        monkeypatch.setattr(ob, "_runs_dir", lambda: tmp_path)
        monkeypatch.setattr(ob, "PROJECT_DIR", tmp_path)

        def _boom(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 1)

        monkeypatch.setattr(subprocess, "run", _boom)
        res = await bridge.run("x", timeout_s=1)
        assert res["success"] is False and "timeout" in res["error"]

    async def test_missing_binary_shape(self, bridge, monkeypatch, tmp_path):
        monkeypatch.setattr(ob, "_runs_dir", lambda: tmp_path)
        monkeypatch.setattr(ob, "PROJECT_DIR", tmp_path)

        def _boom(cmd, **kwargs):
            raise FileNotFoundError("nope")

        monkeypatch.setattr(subprocess, "run", _boom)
        res = await bridge.run("x")
        assert res["success"] is False and "not found" in res["error"]


class TestApprovalGate:
    def test_ask_is_free(self, fake_run):
        import asyncio

        res = asyncio.run(ob.get_opencode_bridge().ask("what is X?"))
        assert res["mode"] == "propose"

    def test_implement_without_token_denied(self):
        r = client.post("/api/copilot/execute", json={"action": "opencode:implement", "params": {"description": "x"}})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "denied"
        assert "approval_token" in body["detail"]

    def test_implement_with_token_runs(self, fake_run):
        tok = client.post("/api/copilot/approve", json={"target": "repo"}).json()["approval_token"]
        r = client.post(
            "/api/copilot/execute",
            json={"action": "opencode:implement", "params": {"description": "x", "approval_token": tok}},
        )
        assert r.json()["status"] == "ok"

    def test_token_single_use(self, fake_run):
        tok = client.post("/api/copilot/approve", json={"target": "repo"}).json()["approval_token"]
        payload = {"action": "opencode:fix", "params": {"bug": "x", "approval_token": tok}}
        assert client.post("/api/copilot/execute", json=payload).json()["status"] == "ok"
        assert client.post("/api/copilot/execute", json=payload).json()["status"] == "denied"

    def test_unknown_subtask(self):
        r = client.post("/api/copilot/execute", json={"action": "opencode:frobnicate", "params": {}})
        assert "Unknown opencode subtask" in r.json()["detail"]

    def test_approve_rejects_other_targets(self):
        assert client.post("/api/copilot/approve", json={"target": "prod"}).status_code == 400

    def test_runs_endpoint(self):
        assert client.get("/api/copilot/runs").json()["status"] == "ok"
