"""Tests para el Validation Engine — ciclo completo de validación experimental.

Cubre:
  - Economic Scorer (cálculo de prioridad, payout, USD/h)
  - Validation Planner (planes por tipo de vulnerabilidad)
  - Confidence Engine (score basado en señales)
  - Promoter (decisión de promover/no promover)
  - HTTP Adapter (fire, build_url, compare_responses)
  - Validation Engine (dry run + ciclo completo con mock)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.validation.adapters import HTTPAdapter, ProbeResponse
from core.validation.confidence import ConfidenceEngine
from core.validation.economic_scorer import EconomicScorer
from core.validation.engine import ValidationEngine
from core.validation.models import (
    AttackCandidate,
    ConfidenceScore,
    EconomicScore,
    ProbeResult,
    ProbeType,
    ValidationPlan,
    ValidationResult,
    VulnType,
)
from core.validation.planner import ValidationPlanner
from core.validation.promoter import ValidationPromoter

# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def sample_candidate() -> AttackCandidate:
    return AttackCandidate(
        vulnerability_type=VulnType.IDOR,
        method="GET",
        endpoint_path="/api/users/123",
        host="api.target.com",
        base_url="https://api.target.com",
        parameters_of_interest=["user_id"],
        param_values={"user_id": "123"},
        requires_auth=True,
        auth_type="bearer",
        reasoner_confidence=0.75,
        signals=["Path contains object reference: user_id", "Numeric ID in route"],
        target_id=1,
    )


@pytest.fixture
def sample_plan(sample_candidate: AttackCandidate) -> ValidationPlan:
    planner = ValidationPlanner()
    return planner.plan(sample_candidate)


@pytest.fixture
def sample_baseline() -> ProbeResult:
    return ProbeResult(
        probe_type=ProbeType.BASELINE,
        success=True,
        status_code=200,
        response_time_ms=150.0,
        response_size=2048,
        response_preview='{"id":123,"name":"test_user","email":"test@test.com"}',
        headers={"content-type": "application/json"},
    )


@pytest.fixture
def sample_probe_data_leak() -> ProbeResult:
    return ProbeResult(
        probe_type=ProbeType.ID_SWAP,
        success=True,
        status_code=200,
        response_time_ms=155.0,
        response_size=2048,
        response_preview='{"id":124,"name":"other_user","email":"other@test.com"}',
        headers={"content-type": "application/json"},
        data_leaked=True,
        signals_detected=["Different user data returned"],
    )


@pytest.fixture
def sample_probe_auth_bypass() -> ProbeResult:
    return ProbeResult(
        probe_type=ProbeType.AUTH_BYPASS,
        success=True,
        status_code=200,
        response_time_ms=130.0,
        response_size=2048,
        response_preview='{"id":123,"name":"test_user","email":"test@test.com"}',
        headers={"content-type": "application/json"},
        auth_bypassed=True,
        signals_detected=["Endpoint accessible without auth"],
    )


@pytest.fixture
def sample_validation_result(
    sample_baseline: ProbeResult,
    sample_probe_data_leak: ProbeResult,
    sample_probe_auth_bypass: ProbeResult,
) -> ValidationResult:
    return ValidationResult(
        attack_candidate_id="ac-test-123",
        validation_plan_id="vp-test-123",
        baseline=sample_baseline,
        probes=[sample_probe_data_leak, sample_probe_auth_bypass],
        total_signals=[
            "Data leak: different user data returned",
            "Auth bypass: endpoint accessible without authentication",
            "IDOR confirmed via ID swap + auth bypass",
        ],
        evidence_summary="IDOR confirmed: swapping user_id returns data of different user, and endpoint works without auth.",
        reproducible=True,
        false_positive_risk="low",
        poc_curl='curl -X GET "https://api.target.com/api/users/124"',
        poc_python="import requests\nurl = 'https://api.target.com/api/users/124'\nresponse = requests.get(url)\nprint(response.text)",
    )


# ═══════════════════════════════════════════════════════════════
# Economic Scorer Tests
# ═══════════════════════════════════════════════════════════════


class TestEconomicScorer:
    def test_score_idor_returns_reasonable_values(self, sample_candidate: AttackCandidate):
        scorer = EconomicScorer()
        score = scorer.score(sample_candidate)

        assert isinstance(score, EconomicScore)
        assert score.expected_payout_avg > 0
        assert 0 < score.probability_acceptance <= 1.0
        assert score.effort_minutes > 0
        assert 1 <= score.priority <= 10
        assert len(score.reasoning) > 0

    def test_high_confidence_boosts_priority(self):
        candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR,
            method="GET",
            endpoint_path="/api/data",
            reasoner_confidence=0.9,
            param_values={"id": "1"},
        )
        scorer = EconomicScorer()
        high_score = scorer.score(candidate)

        low_candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR,
            method="GET",
            endpoint_path="/api/data",
            reasoner_confidence=0.2,
            param_values={"id": "1"},
        )
        low_score = scorer.score(low_candidate)

        assert high_score.priority >= low_score.priority

    def test_filter_candidates_returns_top_n(self):
        candidates = [
            AttackCandidate(vulnerability_type=VulnType.IDOR, method="GET", endpoint_path=f"/api/{i}")
            for i in range(10)
        ]
        scorer = EconomicScorer()
        filtered = scorer.filter_candidates(candidates, min_priority=1, max_candidates=5)
        assert len(filtered) <= 5

    def test_payout_by_severity_varies(self):
        """Payout crítico > payout bajo."""
        scorer = EconomicScorer()

        candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR,
            method="DELETE",  # DELETE → high severity
            endpoint_path="/api/admin/users/1",
            param_values={"id": "1"},
        )
        score = scorer.score(candidate)
        assert score.expected_payout_avg > 300  # high severity

    def test_usd_per_hour_formula(self, sample_candidate: AttackCandidate):
        scorer = EconomicScorer()
        score = scorer.score(sample_candidate)

        # USD/h = (avg_payout * acceptance) / (effort / 60)
        expected_ev = score.expected_payout_avg * score.probability_acceptance
        expected_usdph = expected_ev / (score.effort_minutes / 60)
        assert abs(score.usd_per_hour - expected_usdph) < 1.0


# ═══════════════════════════════════════════════════════════════
# Validation Planner Tests
# ═══════════════════════════════════════════════════════════════


class TestValidationPlanner:
    def test_plans_idor(self, sample_candidate: AttackCandidate):
        planner = ValidationPlanner()
        plan = planner.plan(sample_candidate)

        assert plan.vulnerability_type == VulnType.IDOR
        assert plan.requires_baseline
        assert len(plan.probes) >= 2
        assert plan.estimated_cost >= 3

        types = [p.probe_type for p in plan.probes]
        assert ProbeType.BASELINE in types
        assert ProbeType.ID_SWAP in types

    def test_plan_ssrf(self):
        candidate = AttackCandidate(
            vulnerability_type=VulnType.SSRF,
            method="GET",
            endpoint_path="/api/fetch",
            parameters_of_interest=["url"],
            param_values={"url": "https://example.com/data"},
        )
        planner = ValidationPlanner()
        plan = planner.plan(candidate)

        assert plan.vulnerability_type == VulnType.SSRF
        assert any("URL" in p.description for p in plan.probes)

    def test_plan_auth_bypass(self):
        candidate = AttackCandidate(
            vulnerability_type=VulnType.AUTH_BYPASS,
            method="GET",
            endpoint_path="/api/admin",
            requires_auth=True,
            headers_template={"Authorization": "Bearer test123"},
        )
        planner = ValidationPlanner()
        plan = planner.plan(candidate)

        assert plan.vulnerability_type == VulnType.AUTH_BYPASS
        assert any(p.probe_type == ProbeType.BASELINE for p in plan.probes)
        assert any(p.probe_type == ProbeType.AUTH_BYPASS for p in plan.probes)

    def test_plan_xss(self):
        candidate = AttackCandidate(
            vulnerability_type=VulnType.XSS,
            method="GET",
            endpoint_path="/api/search",
            parameters_of_interest=["q"],
            param_values={"q": "test"},
        )
        planner = ValidationPlanner()
        plan = planner.plan(candidate)

        assert plan.vulnerability_type == VulnType.XSS
        assert plan.estimated_cost <= 3

    def test_plan_sqli(self):
        candidate = AttackCandidate(
            vulnerability_type=VulnType.SQLI,
            method="GET",
            endpoint_path="/api/users",
            parameters_of_interest=["id"],
            param_values={"id": "1"},
        )
        planner = ValidationPlanner()
        plan = planner.plan(candidate)

        assert plan.vulnerability_type == VulnType.SQLI
        assert any(p.probe_type == ProbeType.SLEEP_DETECT for p in plan.probes)
        assert any(p.probe_type == ProbeType.ERROR_ANALYSIS for p in plan.probes)

    def test_generic_fallback(self):
        candidate = AttackCandidate(
            vulnerability_type=VulnType.GENERIC,
            method="GET",
            endpoint_path="/api/unknown",
            parameters_of_interest=["param"],
            param_values={"param": "val"},
        )
        planner = ValidationPlanner()
        plan = planner.plan(candidate)

        assert len(plan.probes) >= 1
        assert plan.estimated_cost >= 1


# ═══════════════════════════════════════════════════════════════
# Confidence Engine Tests
# ═══════════════════════════════════════════════════════════════


class TestConfidenceEngine:
    def test_high_confidence_with_strong_signals(self, sample_validation_result: ValidationResult):
        engine = ConfidenceEngine()
        score = engine.evaluate(sample_validation_result)

        assert score.score >= 0.7
        assert score.should_promote
        assert score.data_leak_confirmed
        assert score.auth_bypass_confirmed
        assert score.reproducible
        assert score.rejection_risk == "low"
        assert len(score.reasoning) > 0

    def test_no_baseline_returns_zero(self):
        engine = ConfidenceEngine()
        result = ValidationResult(probes=[ProbeResult()])
        score = engine.evaluate(result)

        assert score.score == 0.0
        assert not score.should_promote
        assert "Baseline missing" in score.gaps

    def test_no_probes_returns_zero(self):
        engine = ConfidenceEngine()
        result = ValidationResult(baseline=ProbeResult())
        score = engine.evaluate(result)

        assert score.score == 0.0
        assert not score.should_promote

    def test_mixed_signals_medium_confidence(self):
        engine = ConfidenceEngine()
        baseline = ProbeResult(
            probe_type=ProbeType.BASELINE, success=True, status_code=200, response_size=500
        )
        probe = ProbeResult(
            probe_type=ProbeType.ID_SWAP,
            success=True,
            status_code=200,
            response_size=550,
            data_leaked=False,
            auth_bypassed=False,
        )
        result = ValidationResult(baseline=baseline, probes=[probe])
        score = engine.evaluate(result)

        assert 0 <= score.score <= 0.8  # Señal débil
        assert not score.should_promote

    def test_sql_error_detection(self):
        engine = ConfidenceEngine()
        baseline = ProbeResult(
            probe_type=ProbeType.BASELINE, success=True, status_code=200, response_size=100
        )
        probe = ProbeResult(
            probe_type=ProbeType.ERROR_ANALYSIS,
            success=False,
            status_code=500,
            response_size=2000,
            response_preview="SQL syntax error near '1' at line 1...",
            signals_detected=["SQL error message in response"],
        )
        result = ValidationResult(
            baseline=baseline,
            probes=[probe],
            total_signals=["SQL error detected", "Error message contains SQL syntax"],
        )
        score = engine.evaluate(result)

        assert score.score > 0.2
        assert len(score.reasoning) > 0

    def test_confidence_label_mapping(self):
        labels = {
            0.95: "confirmed",
            0.75: "highly_probable",
            0.55: "probable",
            0.30: "unlikely",
            0.10: "negative",
        }
        for score_val, expected_label in labels.items():
            cs = ConfidenceScore(score=score_val)
            assert cs.label == expected_label, f"{score_val} → {cs.label} != {expected_label}"


class TestConfidencePromoteDecision:
    def test_promotes_when_confident_and_reproducible(self):
        cs = ConfidenceScore(score=0.85, reproducible=True)
        assert cs.should_promote

    def test_does_not_promote_when_low_confidence(self):
        cs = ConfidenceScore(score=0.3, reproducible=True)
        assert not cs.should_promote

    def test_does_not_promote_when_not_reproducible(self):
        cs = ConfidenceScore(score=0.85, reproducible=False)
        assert not cs.should_promote


# ═══════════════════════════════════════════════════════════════
# HTTP Adapter Tests
# ═══════════════════════════════════════════════════════════════


class TestHTTPAdapter:
    def test_build_url(self):
        adapter = HTTPAdapter()
        assert adapter.build_url("https://api.test.com", "/users/123") == "https://api.test.com/users/123"
        assert adapter.build_url("https://api.test.com/", "/users/123") == "https://api.test.com/users/123"
        assert adapter.build_url("https://api.test.com", "") == "https://api.test.com"

    def test_probe_response_has_data_leak_detection(self):
        # JSON response with multiple fields → data leak
        resp = ProbeResponse(
            status_code=200,
            body='{"id":1,"name":"test","email":"test@test.com"}',
            body_bytes=50,
            success=True,
        )
        assert resp.has_data_leak

        # Short response → no data leak
        resp2 = ProbeResponse(status_code=200, body="ok", body_bytes=2, success=True)
        assert not resp2.has_data_leak

        # Non-200 → no data leak
        resp3 = ProbeResponse(status_code=403, body="forbidden", body_bytes=9, success=True)
        assert not resp3.has_data_leak

        # JSON array with data → data leak
        resp4 = ProbeResponse(
            status_code=200,
            body='[{"id":1},{"id":2},{"id":3}]',
            body_bytes=55,
            success=True,
        )
        assert resp4.has_data_leak

    def test_compare_responses(self):
        adapter = HTTPAdapter()
        baseline = ProbeResponse(status_code=200, body="hello", body_bytes=5, elapsed_ms=100.0)
        probe = ProbeResponse(status_code=200, body="hello world!", body_bytes=12, elapsed_ms=200.0)

        diff = adapter.compare_responses(baseline, probe)
        assert diff["status_code_diff"] is False  # Same status
        assert diff["size_diff_bytes"] == 7  # 12 - 5
        assert diff["time_diff_ms"] == 100.0
        assert diff["body_changed"] is True

    def test_fire_to_httpbin(self):
        """Integration test real contra httpbin.org. Requiere que httpbin responda 200."""
        import socket

        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("httpbin.org", 443))
        except (TimeoutError, OSError):
            pytest.skip("httpbin.org no accesible")
            return
        adapter = HTTPAdapter(timeout=10)
        resp = adapter.fire("GET", "https://httpbin.org/get", params={"test": "123"})

        if resp.status_code != 200:
            pytest.skip(f"httpbin.org devolvió {resp.status_code}, no 200")
            return
        assert resp.success
        assert resp.status_code == 200
        assert resp.elapsed_ms > 0
        assert resp.body_bytes > 0
        assert "test" in resp.body or "123" in resp.body

    def test_fire_timeout(self):
        """Timeout en endpoint que no responde."""
        adapter = HTTPAdapter(timeout=2)
        resp = adapter.fire("GET", "https://192.0.2.1:9999/test")

        assert not resp.success
        assert "Timeout" in resp.error or "Connection error" in resp.error


# ═══════════════════════════════════════════════════════════════
# Validation Engine Tests
# ═══════════════════════════════════════════════════════════════


class TestValidationEngine:
    def test_dry_run_returns_plan_without_requests(self, sample_candidate: AttackCandidate):
        engine = ValidationEngine()
        result = engine.run(sample_candidate, dry_run=True)

        assert result.dry_run
        assert result.candidate is not None
        assert result.plan is not None
        assert len(result.plan.probes) > 0
        assert result.decision is not None
        assert not result.promoted

    def test_dry_run_economic_score_computed(self, sample_candidate: AttackCandidate):
        engine = ValidationEngine()
        result = engine.run(sample_candidate, dry_run=True)

        assert result.candidate.economic_score.priority > 0
        assert result.candidate.economic_score.expected_payout_avg > 0

    def test_score_only(self, sample_candidate: AttackCandidate):
        engine = ValidationEngine()
        score = engine.score(sample_candidate)

        assert isinstance(score, EconomicScore)
        assert score.priority >= 1
        assert score.usd_per_hour > 0

    def test_plan_only(self, sample_candidate: AttackCandidate):
        engine = ValidationEngine()
        plan = engine.plan_only(sample_candidate)

        assert isinstance(plan, ValidationPlan)
        assert len(plan.probes) > 0

    def test_real_http_validation_against_httpbin(self):
        """Test end-to-end real contra httpbin.org. Skip si httpbin no responde rápido."""
        import socket

        # Primero verificar conectividad TCP rápida
        try:
            socket.setdefaulttimeout(2)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("httpbin.org", 443))
            s.close()
        except (TimeoutError, OSError):
            pytest.skip("httpbin.org no accesible (TCP timeout)")
            return

        # Luego probar con un HEAD request rápido
        import httpx
        try:
            r = httpx.head("https://httpbin.org/get", timeout=5)
            if r.status_code != 200:
                pytest.skip(f"httpbin devolvió {r.status_code}")
                return
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError):
            pytest.skip("httpbin.org no responde HTTP rápido")
            return

        engine = ValidationEngine()
        candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR,
            method="GET",
            endpoint_path="/get",
            host="httpbin.org",
            base_url="https://httpbin.org",
            parameters_of_interest=["id"],
            param_values={"id": "1"},
            requires_auth=False,
            reasoner_confidence=0.5,
            signals=["Test candidate for httpbin validation"],
        )

        engine._adapter = engine._get_adapter()
        engine._adapter._timeout = 10

        plan = engine.plan_only(candidate)
        assert plan.estimated_cost >= 2

        result = engine.run(candidate, dry_run=False)
        assert result.result is not None
        assert result.result.baseline is not None
        assert result.result.baseline.status_code == 200
        assert result.result.baseline.success
        assert result.result.baseline.response_time_ms > 0

    def test_real_validation_cycle(self):
        """Ciclo completo real contra httpbin. Requiere httpbin 200."""
        import socket

        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("httpbin.org", 443))
        except (TimeoutError, OSError):
            pytest.skip("httpbin.org no accesible")
            return
        engine = ValidationEngine()
        candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR,
            method="GET",
            endpoint_path="/get",
            host="httpbin.org",
            base_url="https://httpbin.org",
            parameters_of_interest=["id"],
            param_values={"id": "1"},
            requires_auth=False,
            reasoner_confidence=0.6,
        )

        result = engine.run(candidate, dry_run=False)

        assert result.result is not None
        assert result.confidence is not None
        assert result.duration_ms > 0

        baseline = result.result.baseline
        assert baseline is not None
        if baseline.status_code != 200:
            pytest.skip(f"httpbin devolvió {baseline.status_code}")
            return
        assert baseline.success
        assert baseline.response_time_ms > 0

        for probe in result.result.probes:
            assert probe.status_code == 200
            assert probe.response_size > 0

    def test_promoter_rejects_low_confidence(self):
        promoter = ValidationPromoter()
        candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR,
            method="GET",
            endpoint_path="/api/test",
            target_id=1,
        )
        result = ValidationResult(
            baseline=ProbeResult(success=True, status_code=200, response_size=100),
            probes=[ProbeResult(success=True, status_code=200, response_size=100)],
            reproducible=False,
            false_positive_risk="high",
        )

        decision = promoter.promote(candidate, result)
        assert not decision.promoted
        assert len(decision.rejected_reason) > 0

    def test_promoter_creates_finding_with_db_session(self, sample_validation_result):
        """Verifica que promoter crea Finding en DB mockeada."""
        promoter = ValidationPromoter()
        candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR,
            method="GET",
            endpoint_path="/api/users/123",
            host="api.target.com",
            parameters_of_interest=["user_id"],
            signals=["IDOR detected"],
            target_id=1,
        )

        # Mock de sesión de DB con id real en el finding
        from database import models

        mock_session = MagicMock()

        # Interceptar session.add para asignar id al finding
        real_finding = None

        def _add_side_effect(obj):
            nonlocal real_finding
            if isinstance(obj, models.Finding):
                real_finding = obj

        mock_session.add.side_effect = _add_side_effect

        def _flush_side_effect():
            if real_finding is not None:
                real_finding.id = 42

        mock_session.flush.side_effect = _flush_side_effect

        decision = promoter.promote(candidate, sample_validation_result, session=mock_session)

        assert decision.promoted
        assert decision.finding_id == 42
        assert decision.target_id == 1
        assert VulnType.IDOR.value in decision.title.lower()
        assert decision.confidence.score >= 0.7


# ═══════════════════════════════════════════════════════════════
# Integration: Engine + Promoter (ciclo completo mockeado)
# ═══════════════════════════════════════════════════════════════


@patch("core.validation.adapters.HTTPAdapter.fire")
def test_engine_end_to_end_with_mock_http(mock_fire):
    """Ciclo completo: engine ejecuta probes mock → confidence → promote."""
    # Mock responses: baseline 200, probe 200 con data leak
    mock_fire.side_effect = [
        ProbeResponse(status_code=200, body='{"id":1,"name":"user1"}', body_bytes=30, elapsed_ms=100.0, success=True),
        ProbeResponse(status_code=200, body='{"id":2,"name":"user2"}', body_bytes=30, elapsed_ms=105.0, success=True),
        ProbeResponse(status_code=200, body='{"id":1,"name":"user1"}', body_bytes=30, elapsed_ms=95.0, success=True),
    ]

    engine = ValidationEngine()
    candidate = AttackCandidate(
        vulnerability_type=VulnType.IDOR,
        method="GET",
        endpoint_path="/api/users/1",
        host="api.test.com",
        base_url="https://api.test.com",
        parameters_of_interest=["id"],
        param_values={"id": "1"},
        requires_auth=True,
        auth_type="bearer",
        reasoner_confidence=0.8,
        signals=["Numeric ID in path", "Object reference"],
        target_id=1,
    )

    mock_session = MagicMock()
    mock_finding = MagicMock()
    mock_finding.id = 99
    mock_session.add.return_value = None
    mock_session.flush.return_value = None

    result = engine.run(candidate, session=mock_session)

    assert result.result is not None
    assert result.confidence is not None
    assert result.candidate.economic_score.priority >= 1


@patch("core.validation.adapters.HTTPAdapter.fire")
def test_engine_rejects_when_no_data_leak(mock_fire):
    """Si no hay data leak, no debe promover."""
    # Mismas respuestas en baseline y probe (sin señal)
    same_response = ProbeResponse(
        status_code=200, body='{"status":"ok"}', body_bytes=15, elapsed_ms=50.0, success=True
    )
    mock_fire.return_value = same_response

    engine = ValidationEngine()
    candidate = AttackCandidate(
        vulnerability_type=VulnType.IDOR,
        method="GET",
        endpoint_path="/api/data",
        parameters_of_interest=["id"],
        param_values={"id": "123"},
        target_id=1,
    )

    result = engine.run(candidate)
    assert not result.promoted
    if result.confidence:
        assert result.confidence.score < 0.4
