"""Tests for the LLM-wired CodeGenerator path (Sprint 3: dev bounty execution)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from core.autonomy.code_generator import CodeGenerator, GenerationPlan
from core.autonomy.issue_analyzer import IssueAnalysis
from core.autonomy.repo_analyzer import RepoInfo


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _make_issue(tmp_path: Path) -> IssueAnalysis:
    target = tmp_path / "calc.py"
    target.write_text("def divide(a, b):\n    return a / b\n")
    return IssueAnalysis(
        issue_id="42",
        title="ZeroDivisionError in divide",
        body="Calling divide(1, 0) crashes with ZeroDivisionError.",
        url="https://github.com/fake/repo/issues/42",
        platform="algora",
        issue_type="bug",
        severity="medium",
        confidence=0.8,
        affected_files=["calc.py"],
    )


def _make_repo(tmp_path: Path) -> RepoInfo:
    repo = RepoInfo.__new__(RepoInfo)
    repo.path = tmp_path
    repo.test_files = []
    repo.entry_points = []
    return repo


def _make_plan(issue: IssueAnalysis, repo: RepoInfo) -> GenerationPlan:
    plan = GenerationPlan(issue_analysis=issue, repo_info=repo)
    plan.changes = []
    return plan


class _FakeResponse:
    def __init__(self, content: str, error: str | None = None):
        self.content = content
        self.error = error
        self.provider = "fake"
        self.model = "fake-model"


class TestLLMFixGeneration:
    def test_llm_fix_produces_real_code_change(self, tmp_path: Path) -> None:
        gen = CodeGenerator(config={"use_llm": True})
        issue = _make_issue(tmp_path)
        repo = _make_repo(tmp_path)
        plan = _make_plan(issue, repo)

        fixed = (
            (
                "<<<<<<<FILE_START>>>>>>\n"
                "def divide(a, b):\n"
                '    if b == 0:\n        raise ValueError("cannot divide by zero")\n'
                "    return a / b\n"
                "<<<<<<FILE_END>>>>>>\n"
            )
            .replace("<<<<<<<", "<<<")
            .replace(">>>>>>", ">>>")
        )

        async def fake_complete(system_prompt: str, user_prompt: str) -> str:
            return fixed

        gen._llm_complete = fake_complete  # type: ignore[method-assign]
        changes = _run(gen._generate_changes(plan))
        assert len(changes) == 1
        change = changes[0]
        assert "ValueError" in change.new_content
        assert change.new_content != change.original_content
        assert change.confidence >= 0.7

    def test_llm_unavailable_falls_back_to_heuristics(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        async def dead_route(**kwargs: Any) -> Any:
            raise ConnectionError("no providers")

        import core.copilot.providers.router as router_mod

        monkeypatch.setattr(
            router_mod, "get_provider_router", lambda: type("R", (), {"route": staticmethod(dead_route)})()
        )
        gen = CodeGenerator(config={"use_llm": True})
        result = _run(gen._llm_complete("sys", "user"))
        assert result is None

    def test_malformed_markers_return_no_changes(self, tmp_path: Path) -> None:
        gen = CodeGenerator()
        issue = _make_issue(tmp_path)
        repo = _make_repo(tmp_path)
        plan = _make_plan(issue, repo)

        async def bad_complete(system_prompt: str, user_prompt: str) -> str:
            return "here is the fix, no markers though"

        gen._llm_complete = bad_complete  # type: ignore[method-assign]
        assert _run(gen._generate_llm_fix(plan)) == []

    def test_identical_content_returns_no_changes(self, tmp_path: Path) -> None:
        gen = CodeGenerator()
        issue = _make_issue(tmp_path)
        repo = _make_repo(tmp_path)
        plan = _make_plan(issue, repo)
        original = (tmp_path / "calc.py").read_text()

        async def same_complete(system_prompt: str, user_prompt: str) -> str:
            from core.autonomy.code_generator import CodeGenerator as G

            return f"{G._LLM_FILE_START}\n{original}{G._LLM_FILE_END}"

        gen._llm_complete = same_complete  # type: ignore[method-assign]
        assert _run(gen._generate_llm_fix(plan)) == []

    def test_use_llm_false_skips_llm(self, tmp_path: Path) -> None:
        gen = CodeGenerator(config={"use_llm": False})
        called = False

        async def should_not_call(system_prompt: str, user_prompt: str) -> str:
            nonlocal called
            called = True
            return "x"

        gen._llm_complete = should_not_call  # type: ignore[method-assign]
        issue = _make_issue(tmp_path)
        repo = _make_repo(tmp_path)
        plan = _make_plan(issue, repo)
        _run(gen._generate_changes(plan))
        assert not called


class TestParseLLMFileContent:
    def test_valid_markers(self) -> None:
        gen = CodeGenerator()
        raw = f"intro\n{gen._LLM_FILE_START}\ncode here\n{gen._LLM_FILE_END}\ntrailer"
        assert gen._parse_llm_file_content(raw) == "code here\n"

    def test_missing_end_marker(self) -> None:
        gen = CodeGenerator()
        assert gen._parse_llm_file_content(f"{gen._LLM_FILE_START}\ncode") is None

    def test_empty_body(self) -> None:
        gen = CodeGenerator()
        raw = f"{gen._LLM_FILE_START}\n   \n{gen._LLM_FILE_END}"
        assert gen._parse_llm_file_content(raw) is None


class TestPickPrimaryTarget:
    def test_prefers_mentioned_file(self, tmp_path: Path) -> None:
        gen = CodeGenerator()
        issue = _make_issue(tmp_path)
        repo = _make_repo(tmp_path)
        target = gen._pick_primary_target(issue, repo)
        assert target is not None and target.name == "calc.py"

    def test_none_when_no_targets(self, tmp_path: Path) -> None:
        gen = CodeGenerator()
        issue = IssueAnalysis(
            issue_id="1",
            title="t",
            body="b",
            url="",
            platform="github",
            issue_type="bug",
            severity="low",
            confidence=0.5,
        )
        repo = _make_repo(tmp_path)
        assert gen._pick_primary_target(issue, repo) is None
