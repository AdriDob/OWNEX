"""Tests for COPILOT ecosystem modules: providers, context, bridges, bayesian, connections."""

from __future__ import annotations

import pytest

from core.copilot.bayesian import BayesianLearner, BetaPosterior, beta_posterior
from core.copilot.connections import _normalize_path, run_connection_audit
from core.copilot.orion_context import OrionContext
from core.copilot.providers.base import ProviderConfig, ProviderResponse
from core.copilot.providers.router import TASK_CHAT, ProviderRouter


class TestBetaPosterior:
    def test_mean_zero_observations(self):
        bp = BetaPosterior(alpha=2, beta=2, total=0)
        assert bp.mean == 0.5

    def test_mean_all_successes(self):
        bp = beta_posterior(successes=10, failures=0)
        assert 0.8 < bp.mean < 1.0

    def test_mean_all_failures(self):
        bp = beta_posterior(successes=0, failures=10)
        assert 0.0 < bp.mean < 0.2

    def test_variance_decreases_with_more_data(self):
        low_n = beta_posterior(successes=2, failures=2)
        high_n = beta_posterior(successes=20, failures=20)
        assert high_n.variance < low_n.variance

    def test_credible_interval(self):
        bp = beta_posterior(successes=10, failures=5)
        lower, upper = bp.credible_interval()
        assert lower < upper
        assert lower >= 0.0
        assert upper <= 1.0

    def test_probability_above(self):
        bp = beta_posterior(successes=50, failures=50)
        prob = bp.probability_above(0.5)
        assert 0.4 < prob < 0.6

    def test_mode(self):
        bp = beta_posterior(successes=8, failures=2)
        assert bp.mode > 0.5


class TestBayesianLearner:
    def test_initial_prediction_unreliable(self):
        bl = BayesianLearner()
        pred = bl.predict("hackerone", 70.0)
        assert pred.is_reliable is False
        assert pred.n_observations == 0

    def test_prediction_improves_with_data(self):
        bl = BayesianLearner()
        for _ in range(15):
            bl.observe("hackerone", True)
        pred = bl.predict("hackerone", 70.0)
        assert pred.is_reliable is True
        assert pred.n_observations >= 10

    def test_different_platforms_independent(self):
        bl = BayesianLearner()
        for _ in range(10):
            bl.observe("hackerone", True)
            bl.observe("bugcrowd", False)
        h1 = bl.predict("hackerone", 50.0)
        bc = bl.predict("bugcrowd", 50.0)
        assert h1.probability > bc.probability

    def test_observation_with_dimensions(self):
        bl = BayesianLearner()
        bl.observe("hackerone", True, {"evidence": 0.8, "clarity": 0.9})
        bl.observe("hackerone", True, {"evidence": 0.7, "clarity": 0.8})
        bl.observe("hackerone", False, {"evidence": 0.3, "clarity": 0.4})
        dims = bl.get_dimension_weights("hackerone")
        assert len(dims) > 0

    def test_posterior_summary(self):
        bl = BayesianLearner()
        bl.observe("hackerone", True)
        bl.observe("bugcrowd", False)
        summary = bl.get_posterior_summary()
        assert "hackerone" in summary
        assert "bugcrowd" in summary


class TestNormalizePath:
    def test_clean_path(self):
        assert _normalize_path("/api/targets") == "/api/targets"

    def test_with_method_prefix(self):
        assert _normalize_path("GET /api/targets") == "/api/targets"

    def test_colon_to_braces(self):
        assert _normalize_path("/api/targets/:id") == "/api/targets/{id}"

    def test_trailing_slash(self):
        assert _normalize_path("/api/targets/") == "/api/targets"

    def test_no_leading_slash(self):
        assert _normalize_path("api/targets") == "/api/targets"


class TestConnectionAudit:
    def test_run_audit_returns_dict(self):
        audit = run_connection_audit()
        assert isinstance(audit, dict)
        assert "summary" in audit
        assert "frontend_calls_count" in audit
        assert "backend_routes_count" in audit

    def test_audit_has_counts(self):
        audit = run_connection_audit()
        assert isinstance(audit["frontend_calls_count"], int)
        assert isinstance(audit["backend_routes_count"], int)

    def test_summary_has_keys(self):
        audit = run_connection_audit()
        s = audit["summary"]
        assert "matched" in s
        assert "frontend_orphans" in s
        assert "backend_orphans" in s


class TestProviderRouter:
    @pytest.mark.asyncio
    async def test_route_fallback_when_no_providers(self):
        router = ProviderRouter()
        router._providers = []
        result = await router.route(TASK_CHAT, [{"role": "user", "content": "hi"}])
        assert result.error == "all providers unavailable"

    def test_get_provider_nonexistent(self):
        router = ProviderRouter()
        assert router.get_provider("nonexistent") is None

    def test_get_provider_by_name(self):
        router = ProviderRouter()
        fcc = router.get_provider("fcc")
        assert fcc is not None
        assert fcc.name == "fcc"


class TestOrionContext:
    def test_context_without_db(self):
        ctx = OrionContext(db_factory=None)
        context = ctx.get_context()
        assert "timestamp" in context
        assert "system" in context

    def test_format_for_llm(self):
        ctx = OrionContext()
        text = ctx.format_for_llm()
        assert isinstance(text, str)
        assert "ORION System Context" in text

    def test_cache_reuses_result(self):
        ctx = OrionContext()
        first = ctx.get_context()
        second = ctx.get_context()
        assert first["timestamp"] == second["timestamp"]


class TestProviderResponse:
    def test_default_values(self):
        r = ProviderResponse(content="hello", provider="test")
        assert r.content == "hello"
        assert r.provider == "test"
        assert r.error is None
        assert r.duration_ms == 0.0

    def test_with_error(self):
        r = ProviderResponse(content="", provider="test", error="timeout")
        assert r.error == "timeout"


class TestProviderConfig:
    def test_defaults(self):
        c = ProviderConfig(name="test")
        assert c.name == "test"
        assert c.enabled is True
        assert c.priority == 10
        assert c.timeout_s == 60
