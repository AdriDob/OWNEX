"""Tests for Platform Browser Workers (DataAnnotation, Outlier, Mindrift, Remotasks)."""

from __future__ import annotations

import pytest


class TestDataAnnotationWorker:
    """Test DataAnnotationWorker functionality."""

    def test_worker_initialization(self):
        from cores.opportunity.executors.platform_workers import DataAnnotationWorker

        worker = DataAnnotationWorker({"email": "test@example.com", "password": "test"})
        assert worker.platform == "dataannotation"
        assert worker.email == "test@example.com"
        assert worker.password == "test"

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        from cores.opportunity.executors.platform_workers import DataAnnotationWorker

        worker = DataAnnotationWorker()
        result = await worker.execute("unknown_action")
        assert not result.success
        assert "Unknown action" in result.error

    @pytest.mark.skip(reason="Requires playwright")
    async def test_login_without_credentials(self):
        from cores.opportunity.executors.platform_workers import DataAnnotationWorker

        worker = DataAnnotationWorker()
        result = await worker.login()
        assert not result.success
        assert "not configured" in result.error


class TestOutlierWorker:
    """Test OutlierWorker functionality."""

    def test_worker_initialization(self):
        from cores.opportunity.executors.platform_workers import OutlierWorker

        worker = OutlierWorker({"email": "test@example.com", "password": "test"})
        assert worker.platform == "outlier"
        assert worker.email == "test@example.com"
        assert worker.password == "test"

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        from cores.opportunity.executors.platform_workers import OutlierWorker

        worker = OutlierWorker()
        result = await worker.execute("unknown_action")
        assert not result.success
        assert "Unknown action" in result.error


class TestMindriftBrowserWorker:
    """Test MindriftBrowserWorker functionality."""

    def test_worker_initialization(self):
        from cores.opportunity.executors.platform_workers import MindriftBrowserWorker

        worker = MindriftBrowserWorker({"email": "test@example.com", "password": "test"})
        assert worker.platform == "mindrift_browser"
        assert worker.email == "test@example.com"
        assert worker.password == "test"

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        from cores.opportunity.executors.platform_workers import MindriftBrowserWorker

        worker = MindriftBrowserWorker()
        result = await worker.execute("unknown_action")
        assert not result.success
        assert "Unknown action" in result.error


class TestExecutorsRegistration:
    """Headless registry + browser registry contracts (remotasks purged 2026-09)."""

    def test_platform_workers_registered(self):
        from cores.opportunity.executors import get_executors

        executors = get_executors()
        assert {"freelancer", "mindrift", "opire", "issuehunt"} <= set(executors)
        assert "remotasks" not in executors

    def test_browser_workers_registered(self):
        from cores.automation.workers import get_browser_workers

        workers = get_browser_workers()
        assert set(workers) == {"dataannotation", "outlier", "mindrift_browser"}

    def test_platform_workers_count(self):
        from cores.automation.workers import get_browser_workers
        from cores.opportunity.executors import get_executors

        total = len(get_executors()) + len(get_browser_workers())
        # 4 headless + 3 browser = 7 (algora via adapter, never the registry)
        assert total >= 7


class TestCredentialResolution:
    """Secrets: explicit wins, else IdentityVault, else honest empty (never logged)."""

    def test_explicit_wins_over_vault(self):
        from unittest.mock import MagicMock, patch

        from cores.automation.browser_agent import resolve_credential

        fake_vault = MagicMock()
        fake_vault.get_credentials.return_value = {"password": "vault-pw"}
        with patch("cores.identity_vault.get_identity_vault", return_value=fake_vault):
            assert resolve_credential("explicit-pw", "dataannotation") == "explicit-pw"
            fake_vault.get_credentials.assert_not_called()

    def test_vault_fallback(self):
        from unittest.mock import MagicMock, patch

        from cores.automation.browser_agent import resolve_credential

        fake_vault = MagicMock()
        fake_vault.get_credentials.return_value = {"email": "a@x.com", "password": "vault-pw"}
        with patch("cores.identity_vault.get_identity_vault", return_value=fake_vault):
            assert resolve_credential("", "dataannotation") == "vault-pw"
            assert resolve_credential("", "dataannotation", "email") == "a@x.com"
            fake_vault.get_credentials.assert_called_with("dataannotation", "")

    def test_empty_when_vault_missing(self):
        from unittest.mock import patch

        from cores.automation.browser_agent import resolve_credential

        with patch("cores.identity_vault.get_identity_vault", side_effect=RuntimeError("no vault")):
            assert resolve_credential("", "dataannotation") == ""

    @pytest.mark.asyncio
    async def test_login_without_creds_is_honest(self):
        from unittest.mock import patch

        from cores.automation.browser_agent import BrowserAgent

        with patch("cores.identity_vault.get_identity_vault", side_effect=RuntimeError("no vault")):
            result = await BrowserAgent({}).login_dataannotation()
        assert result.success is False
        assert "not configured" in (result.error or "")

    def test_worker_init_without_config_never_crashes(self):
        from cores.automation.workers.dataannotation_worker import DataAnnotationWorker

        worker = DataAnnotationWorker()
        assert worker.email == "" or isinstance(worker.email, str)
        assert worker.password == "" or isinstance(worker.password, str)
