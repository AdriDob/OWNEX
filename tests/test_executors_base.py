"""Tests for BaseExecutor, ExecutionResult, and get_executors()."""

from __future__ import annotations

from datetime import datetime

import pytest

from core.opportunity.executors import BaseExecutor, ExecutionResult, get_executors


@pytest.fixture
def executor():
    return BaseExecutor()


class TestExecutionResult:
    def test_success_result(self):
        r = ExecutionResult(success=True, action="test", target="t1")
        assert r.success is True
        assert r.action == "test"
        assert r.target == "t1"
        assert r.error is None
        assert r.created_at is not None

    def test_error_result(self):
        r = ExecutionResult(success=False, action="fail", target="t1", error="something went wrong")
        assert r.success is False
        assert r.error == "something went wrong"

    def test_with_data(self):
        r = ExecutionResult(success=True, action="fetch", target="t1", data={"key": "value"})
        assert r.data == {"key": "value"}

    def test_created_at_is_iso_format(self):
        r = ExecutionResult(success=True, action="a", target="t")
        datetime.fromisoformat(r.created_at)

    def test_default_created_at_is_utc(self):
        r = ExecutionResult(success=True, action="a", target="t")
        assert r.created_at.endswith("+00:00") or r.created_at.endswith("Z")


class TestBaseExecutor:
    def test_default_platform(self, executor):
        assert executor.platform == "unknown"

    def test_default_enabled(self, executor):
        assert executor.is_enabled() is True

    def test_disabled_via_config(self):
        e = BaseExecutor({"enabled": False})
        assert e.is_enabled() is False

    def test_get_config_returns_value(self, executor):
        e = BaseExecutor({"key": "value"})
        assert e.get_config("key") == "value"

    def test_get_config_returns_default(self, executor):
        assert executor.get_config("nonexistent", "fallback") == "fallback"

    def test_get_config_returns_none(self, executor):
        assert executor.get_config("nonexistent") is None

    def test_execute_raises_not_implemented(self, executor):
        with pytest.raises(NotImplementedError, match="Action test not implemented"):
            import asyncio

            asyncio.run(executor.execute("test"))

    def test_health_check_returns_success(self, executor):
        import asyncio

        result = asyncio.run(executor.health_check())
        assert result.success is True
        assert "healthy" in result.message

    def test_health_check_has_platform_in_message(self):
        e = BaseExecutor()
        e.platform = "custom"
        import asyncio

        result = asyncio.run(e.health_check())
        assert "custom executor healthy" in result.message


class TestGetExecutors:
    def test_returns_dict(self):
        executors = get_executors()
        assert isinstance(executors, dict)

    def test_returns_known_platforms(self):
        executors = get_executors()
        assert "algora" in executors
        assert "freelancer" in executors
        assert "mindrift" in executors
        assert "opire" in executors
        assert "issuehunt" in executors

    def test_all_executors_have_platform(self):
        executors = get_executors()
        for name, inst in executors.items():
            assert inst.platform == name

    def test_all_executors_are_enabled_by_default(self):
        executors = get_executors()
        for inst in executors.values():
            assert inst.is_enabled() is True

    def test_all_executors_inherit_base(self):
        executors = get_executors()
        for inst in executors.values():
            assert isinstance(inst, BaseExecutor)

    def test_outlier_in_default_executors(self):
        executors = get_executors()
        assert "outlier" in executors
        assert "remotasks" in executors
        assert "dataannotation" in executors
        assert "mindrift_browser" in executors
