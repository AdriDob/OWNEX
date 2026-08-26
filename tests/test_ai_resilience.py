"""Tests para OAR Resilience Layer (ErrorClassifier + QuotaTracker + DegradedMode)
y ObservabilitySink (redacción de secretos + agregados).

Spec: AI FREE-CLOUD ROUTER §9, §11, §18, §25.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cores.ai.runtime.observability import (
    AIEventRecord,
    ObservabilitySink,
    aggregate,
    redact_secrets,
)
from cores.ai.runtime.resilience import (
    UNKNOWN_QUOTA_FACTOR,
    AISystemMode,
    DegradedMode,
    ErrorClassifier,
    QuotaTracker,
    RetryPolicy,
    get_error_classifier,
    get_quota_tracker,
)

# ── ErrorClassifier ──────────────────────────────────────────────────


class TestErrorClassifier:
    def setup_method(self) -> None:
        self.cls = ErrorClassifier()

    def test_429_is_rate_limited_circuit(self):
        r = self.cls.classify("Too many requests", status_code=429)
        assert r.status == "quota_exceeded"
        assert r.policy is RetryPolicy.CIRCUIT

    def test_429_with_retry_after_extracts_seconds(self):
        r = self.cls.classify("rate limited, retry after 30 seconds", status_code=429)
        assert r.retry_after_seconds == 30.0

    def test_401_auth_failed_permanent(self):
        r = self.cls.classify("Unauthorized", status_code=401)
        assert r.status == "auth_failed"
        assert r.policy is RetryPolicy.PERMANENT
        assert r.is_permanent

    def test_403_forbidden_permanent(self):
        r = self.cls.classify("", status_code=403)
        assert r.is_permanent

    def test_402_quota_permanent(self):
        r = self.cls.classify("", status_code=402)
        assert r.status == "quota_exceeded"
        assert r.is_permanent

    def test_5xx_fallback(self):
        for code in (500, 502, 503):
            r = self.cls.classify("server exploded", status_code=code)
            assert r.policy is RetryPolicy.FALLBACK

    def test_context_length_permanent_no_retry(self):
        """Context overflow no se reintenta: cambiar provider o recortar contexto."""
        r = self.cls.classify("This model's maximum context length is exceeded")
        assert r.policy is RetryPolicy.PERMANENT
        assert r.status == "degraded"

    def test_model_not_found_permanent(self):
        r = self.cls.classify("model gpt-99 does not exist")
        assert r.policy is RetryPolicy.PERMANENT
        assert r.status == "unhealthy"

    def test_timeout_retries_same_provider(self):
        r = self.cls.classify(TimeoutError("read timed out"))
        assert r.policy is RetryPolicy.RETRY_SAME

    def test_connection_error_fallbacks(self):
        r = self.cls.classify("connection refused")
        assert r.policy is RetryPolicy.FALLBACK

    def test_billing_message_permanent(self):
        r = self.cls.classify("You have insufficient credits for this request")
        assert r.is_permanent

    def test_unknown_error_conservative_fallback(self):
        r = self.cls.classify(RuntimeError("weird cosmic ray"))
        assert r.policy is RetryPolicy.FALLBACK  # jamás CIRCUIT ni PERMANENT por defecto
        assert r.status == "unknown"

    def test_none_input_safe(self):
        r = self.cls.classify(None, None)
        assert r.policy is RetryPolicy.FALLBACK

    def test_http_code_beats_message_pattern(self):
        """Código HTTP conocido en el mapa gana sobre el patrón del mensaje."""
        self.cls.classify("warning: unauthorized style", status_code=200)
        # 429 + texto de otro patrón → gana el código (quota_exceeded, no degraded):
        r2 = self.cls.classify("context length exceeded", status_code=429)
        assert r2.status == "quota_exceeded"


# ── QuotaTracker ─────────────────────────────────────────────────────


class TestQuotaTracker:
    def test_unknown_limit_returns_honest_factor(self):
        qt = QuotaTracker()
        factor = qt.quota_factor("provider_x")
        assert factor == UNKNOWN_QUOTA_FACTOR == 0.85

    def test_never_assumes_unlimited(self):
        """Spec §11: UNKNOWN jamás se trata como ilimitado (factor < 1.0)."""
        qt = QuotaTracker()
        assert qt.quota_factor("any") < 1.0

    def test_known_limit_full_headroom(self):
        qt = QuotaTracker()
        qt.set_declared_limit("p1", rpm=100)
        assert qt.quota_factor("p1") == 1.0  # sin consumo → margen completo

    def test_rpm_window_counts_and_decays(self):
        qt = QuotaTracker()
        qt.set_declared_limit("p1", rpm=10)
        now = 1000.0
        for i in range(6):
            qt.record_request("p1", ts=now - i)  # dentro de la ventana de 60s
        assert qt.observed_rpm("p1", now) == 6
        factor = qt.quota_factor("p1", now)
        assert factor == round(1.0 - 6 / 10, 3)

    def test_old_requests_expire_from_window(self):
        qt = QuotaTracker()
        qt.set_declared_limit("p1", rpm=10)
        now = 1000.0
        qt.record_request("p1", ts=now - 300)  # hace 5 min → fuera de ventana
        assert qt.observed_rpm("p1", now) == 0
        assert qt.quota_factor("p1", now) == 1.0

    def test_exceeded_limit_zeroes_factor(self):
        qt = QuotaTracker()
        qt.set_declared_limit("p1", rpm=5)
        now = 1000.0
        for i in range(8):
            qt.record_request("p1", ts=now - i)
        assert qt.quota_factor("p1", now) == 0.0

    def test_tokens_today_tracked(self):
        qt = QuotaTracker()
        qt.set_declared_limit("p1", tpd=1000)
        qt.record_request("p1", tokens=400)
        qt.record_request("p1", tokens=400)
        snap = qt.snapshot("p1")
        assert snap["tokens_today"] == 800
        assert qt.quota_factor("p1") == round(1.0 - 800 / 1000, 3)

    def test_set_declared_limit_marks_known(self):
        qt = QuotaTracker()
        assert qt.snapshot("p1")["limits_known"] is False
        qt.set_declared_limit("p1", rpm=60)
        assert qt.snapshot("p1")["limits_known"] is True


# ── DegradedMode ─────────────────────────────────────────────────────

TIER_LOCAL, TIER_FREE, TIER_CHEAP = 1, 2, 3


class TestDegradedMode:
    def test_normal_with_free_provider(self):
        dm = DegradedMode()
        mode = dm.evaluate(["ollama"], {"ollama": TIER_LOCAL})
        assert mode is AISystemMode.NORMAL

    def test_degraded_only_paid_healthy(self):
        """Solo providers pagos healthy = calidad reducida, no normal (spec §25)."""
        dm = DegradedMode()
        mode = dm.evaluate(["openrouter"], {"openrouter": TIER_CHEAP})
        assert mode is AISystemMode.DEGRADED

    def test_offline_when_nothing_healthy(self):
        dm = DegradedMode()
        mode = dm.evaluate([], {})
        assert mode is AISystemMode.OFFLINE_AI

    def test_recovery_to_normal(self):
        dm = DegradedMode()
        dm.evaluate([], {})
        assert dm.mode is AISystemMode.OFFLINE_AI
        mode = dm.evaluate(["opencode"], {"opencode": TIER_FREE})
        assert mode is AISystemMode.NORMAL

    def test_status_shape(self):
        dm = DegradedMode()
        dm.evaluate(["ollama"], {"ollama": TIER_LOCAL})
        st = dm.status()
        assert st["mode"] == "normal"
        assert "since" in st and "reason" in st

    def test_events_recorded_on_change_only(self):
        dm = DegradedMode()
        dm.evaluate(["ollama"], {"ollama": TIER_LOCAL})  # NORMAL inicial (primer set)
        dm.evaluate(["ollama"], {"ollama": TIER_LOCAL})  # sin cambio → sin evento
        events = dm.recent_events()
        assert len(events) <= 1  # solo el estado inicial si cambió desde default


# ── Observability: redacción ─────────────────────────────────────────


class TestSecretRedaction:
    def test_openai_key_redacted(self):
        text = "failed with key sk-proj-abc123def456ghi789 at endpoint"
        out = redact_secrets(text)
        assert "sk-proj-abc123def456ghi789" not in out
        assert "[REDACTED]" in out

    def test_bearer_token_redacted(self):
        out = redact_secrets("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6")
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6" not in out

    def test_api_key_header_redacted(self):
        out = redact_secrets("x-api-key: supersecretkey123")
        assert "supersecretkey123" not in out

    def test_json_style_key_redacted(self):
        out = redact_secrets('config api_key = "sk-live-abcdefgh123456"')
        assert "sk-live-abcdefgh123456" not in out

    def test_clean_text_untouched(self):
        original = "latency 240ms, task CODE, success true"
        assert redact_secrets(original) == original

    def test_idempotent(self):
        once = redact_secrets("key sk-abcdef1234567890 here")
        twice = redact_secrets(once)
        assert once == twice


# ── Observability: record + aggregates ───────────────────────────────


def _event(**overrides: object) -> AIEventRecord:
    base: dict = {
        "timestamp": "2026-08-25T12:00:00+00:00",
        "task": "CODE",
        "provider": "opencode",
        "model": "deepseek-v4-flash-free",
        "success": True,
        "latency_ms": 500.0,
    }
    base.update(overrides)
    return AIEventRecord(**base)  # type: ignore[arg-type]


class TestObservabilitySink:
    def test_record_writes_jsonl_and_survives_restart(self, tmp_path: Path):
        path = tmp_path / "obs.jsonl"
        sink1 = ObservabilitySink(path=path)
        sink1.record(_event())
        sink1.record(_event(task="REASONING", success=False, error="boom"))

        raw_lines = path.read_text().strip().split("\n")
        assert len(raw_lines) == 2
        parsed = json.loads(raw_lines[0])
        assert parsed["task"] == "CODE"

        # nueva instancia (simula restart) lee el historial
        sink2 = ObservabilitySink(path=path)
        history = sink2.load_history()
        assert len(history) == 2
        assert {e.task for e in history} == {"CODE", "REASONING"}

    def test_corrupt_line_skipped_not_fatal(self, tmp_path: Path):
        path = tmp_path / "obs.jsonl"
        path.write_text('{"broken json\n' + _event().to_json() + "\n")
        sink = ObservabilitySink(path=path)
        history = sink.load_history()
        assert len(history) == 1

    def test_secrets_redacted_in_written_file(self, tmp_path: Path):
        """Spec §24: tokens/keys jamás llegan a disco."""
        path = tmp_path / "obs.jsonl"
        sink = ObservabilitySink(path=path)
        sink.record(_event(error="auth failed with sk-proj-secret12345678 key"))
        content = path.read_text()
        assert "sk-proj-secret12345678" not in content
        assert "[REDACTED]" in content

    def test_aggregate_empty_honest_nones(self):
        agg = aggregate([])
        assert agg["total"] == 0
        assert agg["success_rate"] is None
        assert agg["avg_latency_ms"] is None

    def test_aggregate_rates(self):
        events = [
            _event(success=True),
            _event(success=True, fallback_used=True),
            _event(success=False, error="x"),
        ]
        agg = aggregate(events)
        assert agg["total"] == 3
        assert agg["success_rate"] == round(2 / 3, 3)
        assert agg["fallback_rate"] == round(1 / 3, 3)

    def test_aggregate_by_task_learning_view(self):
        """§19: learning consume success_rate por tarea — datos reales."""
        events = [
            _event(task="CODE", success=True),
            _event(task="CODE", success=False),
            _event(task="SUMMARIZATION", success=True),
        ]
        agg = aggregate(events, by_task=True)
        assert agg["by_task"]["CODE"]["success_rate"] == 0.5
        assert agg["by_task"]["SUMMARIZATION"]["success_rate"] == 1.0

    def test_aggregate_by_provider(self):
        events = [
            _event(provider="a", success=True, latency_ms=100.0),
            _event(provider="a", success=False, latency_ms=300.0),
            _event(provider="b", success=True, latency_ms=50.0),
        ]
        agg = aggregate(events)
        assert agg["by_provider"]["a"]["success_rate"] == 0.5
        assert agg["by_provider"]["b"]["avg_latency_ms"] == 50.0

    def test_disk_failure_never_raises(self, tmp_path: Path):
        """Resiliencia: observabilidad rota NUNCA rompe la request de IA."""
        sink = ObservabilitySink(path=tmp_path / "no_dir" / "deeper" / "f.jsonl")
        # forzar fallo: path es un directorio, open() fallará
        bad = ObservabilitySink(path=tmp_path)
        bad.record(_event())  # debe tragarse el error silenciosamente
        # y el sink bueno sigue funcionando
        sink.record(_event())
        assert sink.path.exists()


# ── Adapters nuevos (factories OpenAI-compatible) ────────────────────


class TestNewAdapters:
    def test_ollama_cloud_adapter_factory(self):
        from cores.ai.runtime.adapters import create_ollama_cloud_adapter

        adapter = create_ollama_cloud_adapter(api_key="oc-test")
        assert adapter.provider_id == "ollama_cloud"
        assert "ollama.com" in adapter._base_url

    def test_freecloud_adapter_requires_base_url(self):
        from cores.ai.runtime.adapters import create_freecloud_adapter

        with pytest.raises(ValueError):
            create_freecloud_adapter(base_url="")

    def test_freecloud_adapter_configurable(self):
        from cores.ai.runtime.adapters import create_freecloud_adapter

        adapter = create_freecloud_adapter(
            base_url="https://some-aggregator.example/v1/",
            api_key="fc-key",
            model="free-model-x",
            provider_id="my_aggregator",
        )
        assert adapter.provider_id == "my_aggregator"
        assert adapter._base_url == "https://some-aggregator.example/v1"


# ── Singletons ───────────────────────────────────────────────────────


class TestSingletons:
    def test_getters_return_same_instance(self):
        assert get_error_classifier() is get_error_classifier()
        assert get_quota_tracker() is get_quota_tracker()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
