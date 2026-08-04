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


class TestRemotasksWorker:
    """Test RemotasksWorker functionality."""

    def test_worker_initialization(self):
        from cores.opportunity.executors.platform_workers import RemotasksWorker

        worker = RemotasksWorker({"email": "test@example.com", "password": "test"})
        assert worker.platform == "remotasks"
        assert worker.email == "test@example.com"
        assert worker.password == "test"

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        from cores.opportunity.executors.platform_workers import RemotasksWorker

        worker = RemotasksWorker()
        result = await worker.execute("unknown_action")
        assert not result.success
        assert "Unknown action" in result.error


class TestExecutorsRegistration:
    """Test that all platform workers are registered in get_executors."""

    def test_platform_workers_registered(self):
        from core.opportunity.executors import get_executors

        executors = get_executors()
        assert "dataannotation" in executors
        assert "outlier" in executors
        assert "mindrift_browser" in executors
        assert "remotasks" in executors

    def test_platform_workers_count(self):
        from core.opportunity.executors import get_executors

        executors = get_executors()
        # Should have: freelancer, algora, mindrift, opire, issuehunt, dataannotation, outlier, mindrift_browser, remotasks
        assert len(executors) >= 9
