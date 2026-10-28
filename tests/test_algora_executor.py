"""Algora real executor — claim → PR → merge (mocked network/git, no side effects)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from cores.opportunity.executors.algora_executor import (
    AlgoraConfig,
    AlgoraDweAdapter,
    AlgoraExecutor,
    build_algora_executor,
)


def _cfg() -> AlgoraConfig:
    return AlgoraConfig(github_token="gh_test", work_dir=Path("/tmp/algora_test"))


class TestClaimIssue:
    async def test_invalid_url_fails_closed(self) -> None:
        ex = AlgoraExecutor(_cfg())
        res = await ex.claim_issue("not-a-url")
        assert res.success is False
        assert "Invalid" in (res.error or "")

    async def test_claim_success(self) -> None:
        ex = AlgoraExecutor(_cfg())
        fake_resp = SimpleNamespace(status_code=200, json=lambda: {"claim_id": "c123"})
        with patch.object(AlgoraExecutor, "client", new_callable=lambda: property(lambda self: _FakeClient(fake_resp))):
            res = await ex.claim_issue("https://algora.io/issues/owner/repo/5")
        assert res.success is True
        assert res.claim_id == "c123"
        assert res.repo_url == "https://github.com/owner/repo"

    async def test_claim_conflict(self) -> None:
        ex = AlgoraExecutor(_cfg())
        fake_resp = SimpleNamespace(status_code=409, text="taken")
        with patch.object(AlgoraExecutor, "client", new_callable=lambda: property(lambda self: _FakeClient(fake_resp))):
            res = await ex.claim_issue("https://algora.io/issues/owner/repo/5")
        assert res.success is False
        assert "claimed" in (res.error or "")


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp
        self.posts = []

    async def post(self, url, **kwargs):
        self.posts.append(url)
        return self._resp

    async def get(self, url, **kwargs):
        return self._resp


class TestCloneAndPR:
    async def test_clone_failure_surfaces(self, tmp_path: Path) -> None:
        cfg = AlgoraConfig(github_token="gh_test", work_dir=tmp_path)
        ex = AlgoraExecutor(cfg)
        with patch("cores.opportunity.executors.algora_executor.subprocess.run") as run:
            run.return_value = SimpleNamespace(returncode=1, stderr="nope", stdout="")
            with pytest.raises(RuntimeError, match="clone"):
                await ex.clone_repo("https://github.com/o/r", "b1")

    async def test_create_pr_missing_branch_fails(self, tmp_path: Path) -> None:
        ex = AlgoraExecutor(_cfg())
        with patch("cores.opportunity.executors.algora_executor.subprocess.run") as run:
            run.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
            res = await ex.create_pr(tmp_path, "https://algora.io/issues/o/r/1", "fix")
        assert res.success is False


class TestPollMerge:
    async def test_bad_url_returns_false(self) -> None:
        ex = AlgoraExecutor(_cfg())
        assert await ex._poll_for_merge("not-a-pr-url") is False

    async def test_merged_true(self) -> None:
        ex = AlgoraExecutor(_cfg())
        fake = SimpleNamespace(status_code=200, json=lambda: {"merged": True, "state": "closed"})
        with patch.object(AlgoraExecutor, "client", new_callable=lambda: property(lambda self: _FakeClient(fake))):
            with patch("cores.opportunity.executors.algora_executor.asyncio.sleep", new=AsyncMock()):
                assert await ex._poll_for_merge("https://github.com/o/r/pull/7") is True

    async def test_closed_unmerged_false(self) -> None:
        ex = AlgoraExecutor(_cfg())
        fake = SimpleNamespace(status_code=200, json=lambda: {"merged": False, "state": "closed"})
        with patch.object(AlgoraExecutor, "client", new_callable=lambda: property(lambda self: _FakeClient(fake))):
            with patch("cores.opportunity.executors.algora_executor.asyncio.sleep", new=AsyncMock()):
                assert await ex._poll_for_merge("https://github.com/o/r/pull/7") is False


class TestAdapterCompat:
    def test_adapter_builds_and_build_fn_requires_token(self, monkeypatch) -> None:
        # Aislado de secretos locales: sin env, sin opportunity.env, sin vault.
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setattr(
            "cores.credentials.vault.get_credentials",
            lambda force_refresh=False: SimpleNamespace(github_token=""),
        )

        class _EmptyVault:
            def get_credentials(self, _key):
                return {}

        monkeypatch.setattr("cores.identity_vault.IdentityVault", lambda: _EmptyVault())
        with pytest.raises(ValueError, match="GitHub token"):
            build_algora_executor()

    def test_build_fn_reads_opportunity_env_vault(self, monkeypatch) -> None:
        # Token guardado vía opportunity.env (el path que detecta el checklist)
        # debe construir el executor aunque no haya env var.
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setattr(
            "cores.credentials.vault.get_credentials",
            lambda force_refresh=False: SimpleNamespace(github_token="ghp_from_file"),
        )
        ex = build_algora_executor()
        assert ex.config.github_token == "ghp_from_file"

    def test_build_fn_explicit_param_wins(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_from_env")
        monkeypatch.setattr(
            "cores.credentials.vault.get_credentials",
            lambda force_refresh=False: SimpleNamespace(github_token="ghp_from_file"),
        )
        ex = build_algora_executor(github_token="ghp_explicit")
        assert ex.config.github_token == "ghp_explicit"

    def test_build_fn_env_beats_vault_file(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_from_env")
        monkeypatch.setattr(
            "cores.credentials.vault.get_credentials",
            lambda force_refresh=False: SimpleNamespace(github_token="ghp_from_file"),
        )
        ex = build_algora_executor()
        assert ex.config.github_token == "ghp_from_env"

    async def test_submit_work_no_url_fails(self) -> None:
        ad = AlgoraDweAdapter(github_token="gh_test")
        prepared = SimpleNamespace(metadata={"opportunity": {}}, files={})
        res = await ad.submit_work(prepared, "key")
        assert res["success"] is False
        assert "issue_url" in res["error"]
