"""Tests for GitHubCommenter — bounty claim via slash-commands."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from core.autonomy.github_commenter import CommentResult, GitHubCommenter


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class TestClaimCommands:
    def test_no_token_fails_gracefully(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        commenter = GitHubCommenter()
        result = _run(commenter.post_issue_comment("o", "r", 1, "/try"))
        assert not result.success
        assert "GITHUB_TOKEN" in (result.error or "")

    def test_unknown_platform_claim(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        result = _run(GitHubCommenter().claim_bounty("issuehunt", "o", "r", 1))
        assert not result.success
        assert "algora" in (result.error or "") and "opire" in (result.error or "")

    def test_empty_body_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        result = _run(GitHubCommenter().post_issue_comment("o", "r", 1, "   "))
        assert not result.success

    def test_algora_command_is_attempt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        captured: dict[str, Any] = {}

        class FakeResp:
            status_code = 201
            text = ""
            html_url = "http://x"

            def json(self) -> dict:
                return {"html_url": "http://c/1"}

        class FakeAsyncClient:
            def __init__(self, *a: Any, **kw: Any) -> None:
                pass

            async def __aenter__(self) -> FakeAsyncClient:
                return self

            async def __aexit__(self, *a: Any) -> None:
                pass

            async def post(self, url: str, json: dict | None = None, headers: dict | None = None) -> FakeResp:
                captured["url"] = url
                captured["body"] = json.get("body")
                return FakeResp()

        import core.autonomy.github_commenter as mod

        original = mod.httpx.AsyncClient
        mod.httpx.AsyncClient = FakeAsyncClient  # type: ignore[misc]
        try:
            result = _run(GitHubCommenter().claim_bounty("Algora", "owner", "repo", 7))
        finally:
            mod.httpx.AsyncClient = original

        assert result.success
        assert captured["body"] == "/attempt"
        assert captured["url"].endswith("/repos/owner/repo/issues/7/comments")

    def test_opire_command_is_try(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "t")
        sent: list[str] = []

        class FakeResp:
            status_code = 201
            text = ""

            def json(self) -> dict:
                return {"html_url": "http://c"}

        class FakeAsyncClient:
            def __init__(self, *a: Any, **kw: Any) -> None:
                pass

            async def __aenter__(self) -> FakeAsyncClient:
                return self

            async def __aexit__(self, *a: Any) -> None:
                pass

            async def post(self, url: str, json: dict | None = None, headers: dict | None = None) -> FakeResp:
                sent.append(json.get("body"))
                return FakeResp()

        import core.autonomy.github_commenter as mod

        original = mod.httpx.AsyncClient
        mod.httpx.AsyncClient = FakeAsyncClient  # type: ignore[misc]
        try:
            result = _run(GitHubCommenter().claim_bounty("opire", "o", "r", 3))
        finally:
            mod.httpx.AsyncClient = original

        assert result.success
        assert sent == ["/try"]

    def test_api_error_returns_failed_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "t")

        class FakeResp:
            status_code = 404
            text = "Not Found"

            def json(self) -> dict:
                return {}

        class FakeAsyncClient:
            def __init__(self, *a: Any, **kw: Any) -> None:
                pass

            async def __aenter__(self) -> FakeAsyncClient:
                return self

            async def __aexit__(self, *a: Any) -> None:
                pass

            async def post(self, url: str, json: dict | None = None, headers: dict | None = None) -> FakeResp:
                return FakeResp()

        import core.autonomy.github_commenter as mod

        original = mod.httpx.AsyncClient
        mod.httpx.AsyncClient = FakeAsyncClient  # type: ignore[misc]
        try:
            result = _run(GitHubCommenter().post_issue_comment("o", "r", 99, "/try"))
        finally:
            mod.httpx.AsyncClient = original

        assert isinstance(result, CommentResult)
        assert not result.success
        assert "404" in (result.error or "")


class TestPrBodyClaim:
    def test_appends_claim_reference(self) -> None:
        body = GitHubCommenter.pr_body_with_claim("Fixes crash on divide.", 42)
        assert body.endswith("/claim #42")

    def test_idempotent(self) -> None:
        once = GitHubCommenter.pr_body_with_claim("Body", 5)
        twice = GitHubCommenter.pr_body_with_claim(once, 5)
        assert once == twice
