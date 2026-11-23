"""Tests for the open-source factory repair slice (audit B1–B7).

Covers: legal queue transitions (find_path), autopilot idempotency and
safe blocking, repo-URL resolution, patch path-traversal guard, sandboxed
test execution plumbing, and delivery-package serialization roundtrip.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.autonomy.code_generator import CodeChange, GenerationPlan
from core.autonomy.issue_analyzer import IssueAnalysis
from core.autonomy.repo_analyzer import RepoInfo


def _issue(**kw) -> IssueAnalysis:
    base = dict(
        issue_id="42",
        title="Fix crash",
        body="It crashes",
        url="https://github.com/o/r/issues/42",
        platform="github",
        issue_type="bug",
        severity="high",
        confidence=0.9,
    )
    base.update(kw)
    return IssueAnalysis(**base)


def _repo_info(path: Path) -> RepoInfo:
    return RepoInfo(path=path, language="python", default_branch="main")


def _plan(path: Path, changes: list[CodeChange] | None = None) -> GenerationPlan:
    return GenerationPlan(
        issue_analysis=_issue(),
        repo_info=_repo_info(path),
        changes=changes or [],
        estimated_confidence=0.9,
    )


# ── find_path (B1) ──────────────────────────────────────────────


class TestFindPath:
    def test_discovered_to_executing_walks_legal_chain(self):
        from core.execution_queue.models import ExecState, find_path

        path = find_path(ExecState.DISCOVERED, ExecState.EXECUTING)
        assert path == [
            ExecState.QUALIFIED,
            ExecState.READY,
            ExecState.QUEUED,
            ExecState.EXECUTING,
        ]

    def test_ready_to_executing(self):
        from core.execution_queue.models import ExecState, find_path

        assert find_path(ExecState.READY, ExecState.EXECUTING) == [ExecState.QUEUED, ExecState.EXECUTING]

    def test_same_state_returns_empty(self):
        from core.execution_queue.models import ExecState, find_path

        assert find_path(ExecState.EXECUTING, ExecState.EXECUTING) == []

    def test_terminal_has_no_path(self):
        from core.execution_queue.models import ExecState, find_path

        assert find_path(ExecState.PAID, ExecState.QUEUED) is None
        assert find_path(ExecState.BLOCKED, ExecState.EXECUTING) is None

    def test_executing_to_blocked_via_waiting_human(self):
        from core.execution_queue.models import ExecState, find_path

        assert find_path(ExecState.EXECUTING, ExecState.BLOCKED) == [
            ExecState.WAITING_HUMAN,
            ExecState.BLOCKED,
        ]


# ── CoderAgent patch application guard (B4) ─────────────────────


class TestApplyPlanChanges:
    @pytest.mark.asyncio
    async def test_applies_changes_inside_repo(self, tmp_path: Path):
        from core.autonomy.coder_agent import CoderAgent

        agent = CoderAgent()
        change = CodeChange(
            file_path=Path("src/app.py"),
            original_content="",
            new_content="print('hi')\n",
            change_type="fix",
            description="fix",
        )
        await agent._apply_plan_changes(tmp_path, _plan(tmp_path, [change]))
        assert (tmp_path / "src" / "app.py").read_text() == "print('hi')\n"

    @pytest.mark.asyncio
    async def test_rejects_dotdot_traversal(self, tmp_path: Path):
        from core.autonomy.coder_agent import CoderAgent

        agent = CoderAgent()
        change = CodeChange(
            file_path=Path("../escape.py"),
            original_content="",
            new_content="evil",
            change_type="fix",
            description="evil",
        )
        with pytest.raises(ValueError, match="escapes repository root"):
            await agent._apply_plan_changes(tmp_path, _plan(tmp_path, [change]))
        assert not (tmp_path.parent / "escape.py").exists()

    @pytest.mark.asyncio
    async def test_rejects_absolute_path_outside_repo(self, tmp_path: Path):
        from core.autonomy.coder_agent import CoderAgent

        agent = CoderAgent()
        outside = tmp_path.parent / "outside_secret.txt"
        change = CodeChange(
            file_path=outside,
            original_content="",
            new_content="pwned",
            change_type="fix",
            description="evil",
        )
        with pytest.raises(ValueError, match="escapes repository root"):
            await agent._apply_plan_changes(tmp_path, _plan(tmp_path, [change]))
        assert not outside.exists()


# ── Delivery package serialization roundtrip (B5) ───────────────


class TestDeliverySerialization:
    def test_plan_roundtrip(self, tmp_path: Path):
        from core.autonomy.coder_agent import CoderAgent

        change = CodeChange(
            file_path=Path("a.py"),
            original_content="old",
            new_content="new",
            change_type="fix",
            description="d",
            confidence=0.7,
        )
        plan = _plan(tmp_path, [change])
        data = CoderAgent._serialize_plan(plan)
        # must be JSON-safe
        json.dumps(data)
        restored = CoderAgent._deserialize_plan(data)
        assert restored.changes[0].new_content == "new"
        assert restored.changes[0].file_path == Path("a.py")
        assert restored.issue_analysis.issue_id == "42"
        assert restored.repo_info.path == tmp_path

    def test_repo_info_roundtrip_with_paths(self, tmp_path: Path):
        from core.autonomy.coder_agent import CoderAgent

        info = RepoInfo(
            path=tmp_path,
            language="go",
            test_files=[tmp_path / "x_test.go"],
            config_files={"go.mod": tmp_path / "go.mod"},
        )
        data = CoderAgent._serialize_repo_info(info)
        json.dumps(data)
        restored = CoderAgent._deserialize_repo_info(data)
        assert restored.test_files == [tmp_path / "x_test.go"]
        assert restored.config_files["go.mod"] == tmp_path / "go.mod"


# ── CoderAutopilot queue handling (B1, B2) ──────────────────────


def _work_item(**kw):
    base = dict(
        id="wb-1",
        title="Fix bug in repo",
        platform="algora",
        reward=50.0,
        status="ready_to_deliver",
        access_status="public",
        url="https://github.com/acme/widgets/issues/12",
        description="Steps to reproduce...",
    )
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def queue_env(tmp_path, monkeypatch):
    """Isolate ExecutionQueueStore + delivery dirs per test."""
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    return tmp_path


class _FakeAgent:
    """Stands in for CoderAgent — records the call, returns a canned result."""

    calls: list[dict] = []
    verdict: str = "ready_for_owner_review"

    def __init__(self, *a, **kw):
        pass

    async def solve_issue(self, issue_data, repo_url, platform):
        type(self).calls.append({"issue_data": issue_data, "repo_url": repo_url, "platform": platform})
        return SimpleNamespace(
            success=True,
            verdict=type(self).verdict,
            delivery_package="/tmp/pkg",
            workspace_path="/tmp/ws",
            patch_path="/tmp/patch.diff",
            error=None,
        )


@pytest.fixture
def fake_coder(monkeypatch):
    import core.autonomy.coder_agent as ca

    _FakeAgent.calls = []
    _FakeAgent.verdict = "ready_for_owner_review"
    monkeypatch.setattr(ca, "CoderAgent", _FakeAgent)
    return _FakeAgent


class TestAutopilotSolveOne:
    def test_github_issue_item_reaches_waiting_human(self, queue_env, fake_coder):
        from core.cycles.tasks_coder_autopilot import _solve_one
        from core.execution_queue.models import ExecutionQueueStore

        item = _work_item()
        out = _solve_one(item)
        assert out["success"] is True
        assert fake_coder.calls[0]["repo_url"] == "https://github.com/acme/widgets"
        assert fake_coder.calls[0]["issue_data"]["number"] == 12

        store = ExecutionQueueStore()
        assert store.get(item.id)["state"] == "waiting_human"

    def test_rerun_is_idempotent(self, queue_env, fake_coder):
        from core.cycles.tasks_coder_autopilot import _solve_one
        from core.execution_queue.models import ExecutionQueueStore

        item = _work_item()
        _solve_one(item)
        out = _solve_one(item)  # second run must not reset/re-execute
        assert out["skipped"] is True
        assert len(fake_coder.calls) == 1
        assert ExecutionQueueStore().get(item.id)["state"] == "waiting_human"

    def test_non_github_url_blocks_safely(self, queue_env, fake_coder):
        from core.cycles.tasks_coder_autopilot import _solve_one
        from core.execution_queue.models import ExecutionQueueStore

        item = _work_item(url="https://opire.dev/bounties/abc-123", id="wb-2")
        out = _solve_one(item)
        assert out["blocked"] is True
        assert fake_coder.calls == []
        assert ExecutionQueueStore().get(item.id)["state"] == "blocked"

    def test_blocked_verdict_parks_item(self, queue_env, fake_coder):
        from core.cycles.tasks_coder_autopilot import _solve_one
        from core.execution_queue.models import ExecutionQueueStore

        fake_coder.verdict = "blocked"
        item = _work_item(id="wb-3")
        out = _solve_one(item)
        assert out["blocked"] is True
        assert ExecutionQueueStore().get(item.id)["state"] == "blocked"

    def test_failed_verdict_marks_failed(self, queue_env, fake_coder):
        from core.cycles.tasks_coder_autopilot import _solve_one
        from core.execution_queue.models import ExecutionQueueStore

        fake_coder.verdict = "tests_failed"
        item = _work_item(id="wb-4")
        out = _solve_one(item)
        assert out["success"] is False
        assert ExecutionQueueStore().get(item.id)["state"] == "failed"


# ── GitHub target extraction (B2) ────────────────────────────────


class TestExtractGithubTarget:
    def test_issue_url(self):
        from core.cycles.tasks_coder_autopilot import _extract_github_target

        assert _extract_github_target("https://github.com/acme/widgets/issues/12") == ("acme/widgets", "12")

    def test_pull_url(self):
        from core.cycles.tasks_coder_autopilot import _extract_github_target

        assert _extract_github_target("https://github.com/acme/widgets/pull/7") == ("acme/widgets", "7")

    def test_platform_page_returns_none(self):
        from core.cycles.tasks_coder_autopilot import _extract_github_target

        assert _extract_github_target("https://algora.io/bounties/xyz") is None
        assert _extract_github_target("") is None
        assert _extract_github_target(None) is None
