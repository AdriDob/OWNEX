"""Tests for AI Router — intelligent model fallback for ORION ecosystem."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# ── Model tests ───────────────────────────────────────────────


class TestAIProviderStatus:
    def test_to_dict_roundtrip(self):
        from core.ai_router.engine import AIProviderStatus

        p = AIProviderStatus(name="test", tier="free", available=True, current_model="m", latency_ms=12.3)
        d = p.to_dict()
        assert d["name"] == "test"
        assert d["tier"] == "free"
        assert d["available"] is True
        assert d["latency_ms"] == 12.3

    def test_to_dict_rounds_latency(self):
        from core.ai_router.engine import AIProviderStatus

        p = AIProviderStatus(name="x", tier="local", available=False, latency_ms=12.345)
        assert p.to_dict()["latency_ms"] == 12.3


class TestAIPolicy:
    def test_default_values(self):
        from core.ai_router.engine import AIPolicy

        p = AIPolicy()
        assert p.fallback_enabled is True
        assert "opencode_free" in p.providers_priority
        assert "fcc_proxy" in p.providers_priority
        assert "ollama" in p.providers_priority
        assert p.never_use_openrouter_directly is True

    def test_to_dict_contains_all_keys(self):
        from core.ai_router.engine import AIPolicy

        d = AIPolicy().to_dict()
        assert "fallback_enabled" in d
        assert "providers_priority" in d
        assert "never_use_openrouter_directly" in d

    def test_prefer_lists(self):
        from core.ai_router.engine import AIPolicy

        p = AIPolicy()
        assert "architecture" in p.prefer_quality_for
        assert "security" in p.prefer_quality_for
        assert "search" in p.prefer_speed_for


class TestAIHealth:
    def test_to_dict(self):
        from core.ai_router.engine import AIHealth, AIProviderStatus

        h = AIHealth(
            status="green",
            current_provider="opencode_free",
            near_limit=False,
            available_providers=[AIProviderStatus(name="opencode_free", tier="free", available=True)],
        )
        d = h.to_dict()
        assert d["status"] == "green"
        assert d["current_provider"] == "opencode_free"

    def test_red_when_no_providers(self):
        from core.ai_router.engine import AIHealth

        h = AIHealth(status="red")
        assert h.to_dict()["status"] == "red"


class TestFallbackRecommendation:
    def test_to_dict(self):
        from core.ai_router.engine import FallbackRecommendation

        r = FallbackRecommendation(
            should_switch=True,
            reason="test",
            from_provider="a",
            to_provider="b",
        )
        d = r.to_dict()
        assert d["should_switch"] is True
        assert d["from_provider"] == "a"
        assert d["to_provider"] == "b"


class TestSwitchRecord:
    def test_to_dict(self):
        from core.ai_router.engine import SwitchRecord

        r = SwitchRecord(
            timestamp="now", from_provider="a", from_model="m1", to_provider="b", to_model="m2", reason="test"
        )
        d = r.to_dict()
        assert d["timestamp"] == "now"
        assert d["success"] is True
        assert d["duration_ms"] == 0.0


# ── Policy persistence ────────────────────────────────────────


class TestCreateDefaultPolicy:
    def test_returns_valid_policy(self):
        from core.ai_router.engine import create_default_policy

        p = create_default_policy()
        assert p.fallback_enabled is True
        assert isinstance(p.providers_priority, list)


class TestLoadPolicy:
    def test_no_file_returns_default(self):
        from core.ai_router.engine import load_policy

        with patch("pathlib.Path.exists", return_value=False):
            p = load_policy()
            assert p.fallback_enabled is True

    def test_load_from_file(self):
        from core.ai_router.engine import load_policy

        with patch("yaml.safe_load", return_value={"fallback_enabled": False, "switch_before_limit_percentage": 50}):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", MagicMock()):
                    p = load_policy()
                    assert p.fallback_enabled is False
                    assert p.switch_before_limit_percentage == 50

    def test_load_missing_keys_falls_back(self):
        from core.ai_router.engine import load_policy

        with patch("yaml.safe_load", return_value={}):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", MagicMock()):
                    p = load_policy()
                    assert p.fallback_enabled is True


class TestSavePolicy:
    def test_saves_to_disk(self):
        from core.ai_router.engine import AIPolicy, save_policy

        p = AIPolicy(fallback_enabled=False)
        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.ai_router.engine.POLICY_PATH", os.path.join(tmp, "policy.yaml")):
                save_policy(p)
                assert os.path.isfile(os.path.join(tmp, "policy.yaml"))

    def test_creates_parent_dir(self):
        from core.ai_router.engine import AIPolicy, save_policy

        p = AIPolicy()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "policy.yaml")
            with patch("core.ai_router.engine.POLICY_PATH", path):
                save_policy(p)
                assert os.path.isfile(path)


# ── VALID_CHAIN guard ─────────────────────────────────────────


class TestValidChain:
    def test_never_contains_openrouter(self):
        from core.ai_router.engine import _VALID_CHAIN, AIPolicy

        assert "openrouter" not in str(_VALID_CHAIN).lower()
        assert AIPolicy().never_use_openrouter_directly is True


# ── Engine tests ──────────────────────────────────────────────


@pytest.fixture
def engine():
    from core.ai_router.engine import AIRouterEngine

    e = AIRouterEngine.__new__(AIRouterEngine)
    e._history = []
    e._event_bus = None
    return e


class TestAIRouterEngine:
    def test_init_loads_policy(self):
        from core.ai_router.engine import AIRouterEngine

        with patch("core.ai_router.engine.load_policy") as mock_load:
            mock_load.return_value = MagicMock()
            e = AIRouterEngine()
            assert e._policy is not None

    def test_policy_property(self):
        from core.ai_router.engine import AIPolicy, AIRouterEngine

        p = AIPolicy(fallback_enabled=False)
        e = AIRouterEngine(policy=p)
        assert e.policy.fallback_enabled is False

    def test_reload_policy(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        e._policy = MagicMock(fallback_enabled=True)
        with patch("core.ai_router.engine.load_policy") as mock_load:
            mock_load.return_value = MagicMock(fallback_enabled=False)
            e.reload_policy()
            assert e._policy.fallback_enabled is False

    def test_save_policy_calls_module_function(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with patch("core.ai_router.engine.save_policy") as mock_save:
            e.save_policy()
            mock_save.assert_called_once_with(e._policy)

    def test_discover_providers_returns_three(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with (
            patch.object(e, "_check_proxy", return_value=(False, "", 0.0)),
            patch.object(e, "_check_ollama", return_value=(False, [], 0.0)),
            patch.object(e, "_check_gooseai", return_value=(False, [], 0.0)),
            patch.object(e, "_check_nvidia_nim", return_value=(False, [], 0.0)),
        ):
            providers = e._discover_providers()
            assert len(providers) == 5
            names = [p.name for p in providers]
            assert "opencode_free" in names
            assert "fcc_proxy" in names
            assert "ollama" in names
            assert "gooseai" in names
            assert "nvidia_nim" in names

    def test_discover_opencode_free_always_available(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with (
            patch.object(e, "_check_proxy", return_value=(False, "", 0.0)),
            patch.object(e, "_check_ollama", return_value=(False, [], 0.0)),
        ):
            providers = e._discover_providers()
            free = [p for p in providers if p.name == "opencode_free"]
            assert len(free) == 1
            assert free[0].available is True
            assert free[0].current_model == "opencode/deepseek-v4-flash-free"

    @pytest.mark.parametrize("available,latency", [(True, 5.0), (False, 100.0)])
    def test_check_proxy(self, available, latency, engine):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200 if available else 500
            mock_resp.json.return_value = {"default_model": "claude-sonnet-4.5"} if available else {}
            mock_get.return_value = mock_resp
            ok, model, lat = engine._check_proxy()
            assert ok is available
            if available:
                assert model == "claude-sonnet-4.5"

    @pytest.mark.parametrize("available,count", [(True, 3), (False, 0)])
    def test_check_ollama(self, available, count, engine):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200 if available else 500
            mock_resp.json.return_value = {"models": [{"name": f"m{i}"} for i in range(count)]} if available else {}
            mock_get.return_value = mock_resp
            ok, models, _ = engine._check_ollama()
            assert ok is available
            assert len(models) == count

    def test_check_proxy_connection_error_returns_false(self, engine):
        with patch("httpx.get", side_effect=ConnectionError("refused")):
            ok, model, lat = engine._check_proxy()
            assert ok is False
            assert model == ""

    def test_check_ollama_connection_error_returns_false(self, engine):
        with patch("httpx.get", side_effect=ConnectionError("refused")):
            ok, models, lat = engine._check_ollama()
            assert ok is False
            assert models == []

    @patch("os.path.isfile")
    def test_is_proxy_locked_returns_true(self, mock_isfile, engine):
        mock_isfile.return_value = True
        assert engine.is_proxy_locked() is True

    @patch("os.path.isfile")
    def test_is_proxy_locked_returns_false(self, mock_isfile, engine):
        mock_isfile.return_value = False
        assert engine.is_proxy_locked() is False

    def test_check_health_green_all_available(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with (
            patch.object(e, "_check_proxy", return_value=(True, "claude-sonnet-4.5", 5.0)),
            patch.object(e, "_check_ollama", return_value=(True, ["llama3"], 3.0)),
        ):
            h = e.check_health()
            assert h.status == "green"
            assert h.current_provider == "fcc_proxy"

    def test_check_health_green_with_only_free(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with (
            patch.object(e, "_check_proxy", return_value=(False, "", 0.0)),
            patch.object(e, "_check_ollama", return_value=(False, [], 0.0)),
        ):
            h = e.check_health()
            assert h.status == "green"
            assert h.current_provider == "opencode_free"

    def test_check_health_yellow_when_near_limit(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with (
            patch.object(e, "_check_proxy", return_value=(False, "", 0.0)),
            patch.object(e, "_check_ollama", return_value=(False, [], 0.0)),
            patch.object(e, "_estimate_near_limit", return_value=True),
        ):
            h = e.check_health()
            assert h.status == "yellow"

    def test_recommend_fallback_no_alternatives(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with (
            patch.object(e, "_check_proxy", return_value=(False, "", 0.0)),
            patch.object(e, "_check_ollama", return_value=(False, [], 0.0)),
        ):
            r = e.recommend_fallback()
            assert r.should_switch is False
            assert "No alternative providers" in r.reason

    def test_recommend_fallback_policy_disabled(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine.__new__(AIRouterEngine)
        e._policy = MagicMock(fallback_enabled=False)
        e._history = []
        e._event_bus = None
        with (
            patch.object(e, "_check_proxy", return_value=(True, "claude", 5.0)),
            patch.object(e, "_check_ollama", return_value=(True, ["llama3"], 3.0)),
        ):
            r = e.recommend_fallback()
            assert r.should_switch is False
            assert "disabled" in r.reason

    def test_recommend_fallback_switches_when_near_limit(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with (
            patch.object(e, "_check_proxy", return_value=(True, "claude", 5.0)),
            patch.object(e, "_check_ollama", return_value=(True, ["llama3"], 3.0)),
            patch.object(e, "_estimate_near_limit", return_value=True),
        ):
            r = e.recommend_fallback()
            assert r.should_switch is True
            assert r.to_provider in ("opencode_free", "fcc_proxy", "ollama")

    def test_get_status_returns_dict(self):
            from core.ai_router.engine import AIRouterEngine

            e = AIRouterEngine()
            with (
                patch.object(e, "_check_proxy", return_value=(True, "claude", 5.0)),
                patch.object(e, "_check_ollama", return_value=(True, ["llama3"], 3.0)),
            ):
                s = e.check_health().to_dict()
                assert "status" in s
                assert "current_provider" in s
                assert "current_model" in s
                assert "available_providers" in s

    def test_record_switch_appends_to_history(self, engine):
        from core.ai_router.engine import SwitchRecord

        r = SwitchRecord(
            timestamp="now", from_provider="a", from_model="m1", to_provider="b", to_model="m2", reason="test"
        )
        engine.record_switch(r)
        assert len(engine._history) == 1
        assert engine._history[0].from_provider == "a"

    def test_get_history_returns_limited(self, engine):
        from core.ai_router.engine import SwitchRecord

        for i in range(5):
            r = SwitchRecord(
                timestamp=str(i), from_provider="a", from_model="m", to_provider="b", to_model="m", reason="x"
            )
            engine._history.append(r)
        assert len(engine.get_history(limit=3)) == 3
        assert len(engine.get_history(limit=10)) == 5

    def test_clear_history_empties(self, engine):
        from core.ai_router.engine import SwitchRecord

        engine._history.append(
            SwitchRecord(timestamp="t", from_provider="a", from_model="m", to_provider="b", to_model="m", reason="x")
        )
        engine._history.append(
            SwitchRecord(timestamp="t2", from_provider="a", from_model="m", to_provider="b", to_model="m", reason="x")
        )
        engine.clear_history()
        assert len(engine._history) == 0

    def test_publish_event_no_bus_doesnt_crash(self, engine):
        engine.publish_event("test:event", foo="bar")

    def test_register_capabilities(self):
        from core.ai_router.engine import AIRouterEngine

        mock_registry = MagicMock()
        with patch("cores.capabilities.registry.get_capability_registry", return_value=mock_registry):
            e = AIRouterEngine()
            e.register_capabilities()
            assert mock_registry.register.call_count == 1

    def test_estimate_near_limit(self):
        from core.ai_router.engine import AIRouterEngine

        e = AIRouterEngine()
        with patch("os.path.isfile", return_value=False):
            assert e._estimate_near_limit() is False

    def test_get_proxy_models_returns_list(self, engine):
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": "claude-sonnet-4.5"}]}
            mock_get.return_value = mock_resp
            models = engine._get_proxy_models()
            assert isinstance(models, list)

    def test_get_proxy_models_connection_error(self, engine):
        with patch("httpx.get", side_effect=ConnectionError):
            models = engine._get_proxy_models()
            assert models == []


# ── Module-level registration ─────────────────────────────────


class TestModuleRegistration:
    def test_import_does_not_crash(self):
        with patch("core.ai_router.engine.AIRouterEngine.register_capabilities"):
            from core.ai_router import engine  # noqa: F811

            assert hasattr(engine, "AIRouterEngine")
