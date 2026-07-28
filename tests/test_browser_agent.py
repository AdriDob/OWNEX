"""Tests for BrowserAgent — Playwright-based browser automation."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.automation.browser_agent import BrowserAgent, BrowserResult


@pytest.fixture
def agent():
    return BrowserAgent({"headless": True, "storage_dir": "/tmp/test_browser_sessions"})


def test_import_error_without_playwright():
    agent = BrowserAgent()
    with patch("core.automation.browser_agent.async_playwright", None):
        with pytest.raises(ImportError, match="playwright not installed"):
            asyncio.run(agent.start())


class TestBrowserAgentStartStop:
    def test_start_creates_browser_and_context(self, agent):
        async def run():
            mock_playwright = MagicMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_playwright.start = AsyncMock(return_value=mock_playwright)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)

            with patch("core.automation.browser_agent.async_playwright", lambda: mock_playwright):
                await agent.start()
                assert agent._browser is not None
                assert agent._context is not None
                assert agent._page is not None

        asyncio.run(run())

    def test_start_without_playwright_raises(self, agent):
        with patch("core.automation.browser_agent.async_playwright", None):
            with pytest.raises(ImportError):
                asyncio.run(agent.start())


class TestBrowserAgentPlatformMethods:
    def test_login_linkedin_without_browser(self, agent):
        result = asyncio.run(agent.login_linkedin("user@test.com", "pass123"))
        assert result.success is False
        assert isinstance(result, BrowserResult)

    def test_easy_apply_linkedin_without_browser(self, agent):
        result = asyncio.run(agent.easy_apply_linkedin("https://example.com/job"))
        assert result.success is False
        assert isinstance(result, BrowserResult)

    def test_goto_without_browser(self, agent):
        result = asyncio.run(agent.goto("https://example.com"))
        assert result.success is False

    def test_click_without_browser(self, agent):
        result = asyncio.run(agent.click("button.submit"))
        assert result.success is False

    def test_fill_without_browser(self, agent):
        result = asyncio.run(agent.fill("input[name=email]", "test@test.com"))
        assert result.success is False

    def test_get_text_without_browser(self, agent):
        result = asyncio.run(agent.get_text(".title"))
        assert result.success is False


class TestBrowserAgentOutlierMethods:
    def test_outlier_claim_task_without_browser(self, agent):
        result = asyncio.run(agent.outlier_claim_task("task1"))
        assert result.success is False
        assert isinstance(result, BrowserResult)


class TestBrowserAgentDataAnnotation:
    def test_dataannotation_claim_task_without_browser(self, agent):
        result = asyncio.run(agent.dataannotation_claim_task("task1"))
        assert result.success is False
        assert isinstance(result, BrowserResult)


class TestBrowserAgentSession:
    def test_save_session_without_browser(self, agent):
        result = asyncio.run(agent.save_session("test"))
        assert result.success is False

    def test_load_session_without_browser(self, agent):
        result = asyncio.run(agent.load_session("test"))
        assert result.success is False
