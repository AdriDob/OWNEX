"""Tests para el Validation Bridge — conexión Offensive Intelligence → Validation Engine.

Cubre:
  - Conversión Hypothesis → AttackCandidate
  - ReasonerResult → AttackCandidate (batch)
  - from_endpoint (ciclo completo con mock)
  - validate_endpoint (ciclo completo)
  - Mapeo de todos los tipos de vulnerabilidad
  - Filtro por prioridad económica
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.offensive.models import (
    Contradiction,
    EndpointInfo,
    Hypothesis,
    ReasonerResult,
)
from core.validation.bridge import (
    SEVERITY_PAYOUT_BASE,
    VULN_MAP,
    ValidationBridge,
)
from core.validation.models import AttackCandidate, VulnType

# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def sample_hypothesis() -> Hypothesis:
    return Hypothesis(
        vulnerability_type="idor",
        endpoint="/api/users/123",
        method="GET",
        confidence=0.75,
        severity="medium",
        summary="Possible IDOR on user profile",
        description="The endpoint returns user data based on a numeric user_id",
        why_triager_might_reject="Requires authentication",
        parameters_of_interest=["user_id"],
        test_instructions=["Try changing user_id to 124 and compare responses"],
        signals=["Path contains numeric ID reference", "User object returned"],
        contradictions=[
            Contradiction(
                label="Possible rate limiting",
                description="Endpoint may return 429 for rapid requests",
                confidence_reduction=0.1,
                how_to_rule_out="Test with delays between requests",
            )
        ],
    )


@pytest.fixture
def sample_hypothesis_no_auth() -> Hypothesis:
    return Hypothesis(
        vulnerability_type="ssrf",
        endpoint="/api/fetch?url=https://example.com",
        method="GET",
        confidence=0.65,
        severity="medium",
        summary="Possible SSRF in fetch endpoint",
        parameters_of_interest=["url"],
        test_instructions=["Try changing url to internal IP"],
        signals=["URL parameter controls external request"],
        why_triager_might_reject="URL validation may be in place",
    )


@pytest.fixture
def mock_offensive_engine() -> MagicMock:
    engine = MagicMock()
    return engine


# ═══════════════════════════════════════════════════════════════
# VULN_MAP Coverage
# ═══════════════════════════════════════════════════════════════


class TestVulnMap:
    def test_known_types_are_mapped(self):
        """Todos los tipos que usan los reasoners existentes están mapeados."""
        assert VULN_MAP["idor"] == VulnType.IDOR
        assert VULN_MAP["ssrf"] == VulnType.SSRF
        assert VULN_MAP["xss"] == VulnType.XSS
        assert VULN_MAP["sqli"] == VulnType.SQLI
        assert VULN_MAP["auth_bypass"] == VulnType.AUTH_BYPASS

    def test_extended_types_are_mapped(self):
        """Tipos adicionales también están mapeados para futuros reasoners."""
        assert VULN_MAP["csrf"] == VulnType.CSRF
        assert VULN_MAP["lfi"] == VulnType.LFI
        assert VULN_MAP["cmdi"] == VulnType.CMDI
        assert VULN_MAP["graphql"] == VulnType.GRAPHQL
        assert VULN_MAP["race_condition"] == VulnType.RACE_CONDITION
        assert VULN_MAP["cors"] == VulnType.CORS
        assert VULN_MAP["open_redirect"] == VulnType.OPEN_REDIRECT
        assert VULN_MAP["business_logic"] == VulnType.BUSINESS_LOGIC

    def test_unknown_type_returns_none(self):
        """Tipo desconocido no rompe el bridge."""
        assert "unknown" not in VULN_MAP
        assert "rce" not in VULN_MAP


class TestSeverityPayoutBase:
    def test_all_severities_have_payout(self):
        assert SEVERITY_PAYOUT_BASE["critical"] == 5000.0
        assert SEVERITY_PAYOUT_BASE["high"] == 1500.0
        assert SEVERITY_PAYOUT_BASE["medium"] == 400.0
        assert SEVERITY_PAYOUT_BASE["low"] == 100.0
        assert SEVERITY_PAYOUT_BASE["info"] == 0.0


# ═══════════════════════════════════════════════════════════════
# Hypothesis → AttackCandidate
# ═══════════════════════════════════════════════════════════════


class TestFromHypothesis:
    def test_basic_conversion(self, sample_hypothesis: Hypothesis):
        bridge = ValidationBridge()
        candidate = bridge.from_hypothesis(sample_hypothesis, target_id=42)

        assert candidate is not None
        assert candidate.vulnerability_type == VulnType.IDOR
        assert candidate.method == "GET"
        assert candidate.endpoint_path == "/api/users/123"
        assert candidate.parameters_of_interest == ["user_id"]
        assert candidate.original_hypothesis_id == sample_hypothesis.id
        assert candidate.reasoner_confidence == 0.75
        assert candidate.signals == sample_hypothesis.signals
        assert candidate.target_id == 42
        assert len(candidate.contradictions) == 1
        assert candidate.economic_score is not None
        assert candidate.economic_score.priority > 0

    def test_unknown_vuln_type_returns_none(self):
        bridge = ValidationBridge()
        hyp = Hypothesis(vulnerability_type="unknown_type", endpoint="/test", method="GET")
        candidate = bridge.from_hypothesis(hyp)
        assert candidate is None

    def test_auth_detection_via_rejection_reason(self, sample_hypothesis: Hypothesis):
        bridge = ValidationBridge()
        candidate = bridge.from_hypothesis(sample_hypothesis)

        assert candidate is not None
        # "Requires authentication" in why_triager_might_reject → requires_auth=True
        assert candidate.requires_auth is True

    def test_no_auth_detection(self, sample_hypothesis_no_auth: Hypothesis):
        bridge = ValidationBridge()
        candidate = bridge.from_hypothesis(sample_hypothesis_no_auth)

        assert candidate is not None
        # No auth keywords in rejection reason → requires_auth=False
        assert candidate.requires_auth is False

    def test_method_fallback_to_get(self):
        bridge = ValidationBridge()
        hyp = Hypothesis(
            vulnerability_type="xss",
            endpoint="/api/search",
            # No method set
        )
        candidate = bridge.from_hypothesis(hyp)

        assert candidate is not None
        assert candidate.method == "GET"

    def test_params_default_to_fuzz(self, sample_hypothesis: Hypothesis):
        bridge = ValidationBridge()
        candidate = bridge.from_hypothesis(sample_hypothesis)

        assert candidate is not None
        assert candidate.param_values.get("user_id") == "FUZZ"


# ═══════════════════════════════════════════════════════════════
# ReasonerResult → AttackCandidate batch
# ═══════════════════════════════════════════════════════════════


class TestFromReasonerResult:
    def test_multiple_hypotheses(self, sample_hypothesis: Hypothesis):
        hyp2 = Hypothesis(
            vulnerability_type="ssrf",
            endpoint="/api/fetch",
            method="GET",
            confidence=0.5,
        )
        result = ReasonerResult(
            endpoint=EndpointInfo(path="/api/users/123", method="GET"),
            hypotheses=[sample_hypothesis, hyp2],
        )
        bridge = ValidationBridge()
        candidates = bridge.from_reasoner_result(result, target_id=1)

        assert len(candidates) == 2
        assert candidates[0].vulnerability_type == VulnType.IDOR
        assert candidates[1].vulnerability_type == VulnType.SSRF

    def test_empty_hypotheses_returns_empty(self):
        result = ReasonerResult(endpoint=EndpointInfo(path="/api/test", method="GET"))
        bridge = ValidationBridge()
        candidates = bridge.from_reasoner_result(result)

        assert len(candidates) == 0

    def test_filters_by_priority(self, sample_hypothesis: Hypothesis):
        # Create hypothesis with very low confidence → low priority
        low_hyp = Hypothesis(
            vulnerability_type="idor",
            endpoint="/api/trivial",
            method="GET",
            confidence=0.05,  # Muy baja
        )
        result = ReasonerResult(
            endpoint=EndpointInfo(path="/api/test", method="GET"),
            hypotheses=[sample_hypothesis, low_hyp],
        )
        bridge = ValidationBridge()
        candidates = bridge.from_reasoner_result(result, target_id=1, min_priority=5)

        # Solo candidates con prioridad >= 5
        assert all(c.economic_score.priority >= 5 for c in candidates)

    def test_limits_max_candidates(self, sample_hypothesis: Hypothesis):
        hyps = [
            Hypothesis(
                vulnerability_type="idor" if i % 2 == 0 else "ssrf",
                endpoint=f"/api/endpoint/{i}",
                method="GET",
                confidence=0.7,
            )
            for i in range(10)
        ]
        result = ReasonerResult(endpoint=EndpointInfo(path="/api/test", method="GET"), hypotheses=hyps)
        bridge = ValidationBridge()
        candidates = bridge.from_reasoner_result(result, target_id=1, max_candidates=3)

        assert len(candidates) <= 3


# ═══════════════════════════════════════════════════════════════
# from_endpoint — ciclo completo con mock
# ═══════════════════════════════════════════════════════════════


class TestFromEndpoint:
    @patch("core.validation.bridge.OffensiveEngine")
    def test_from_endpoint_basic(self, mock_engine_cls: MagicMock):
        """from_endpoint llama a analyze_endpoint y devuelve candidates."""
        # Setup mock
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_result = ReasonerResult(
            endpoint=EndpointInfo(path="/api/users/123", method="GET"),
            hypotheses=[
                Hypothesis(
                    vulnerability_type="idor",
                    endpoint="/api/users/123",
                    method="GET",
                    confidence=0.75,
                )
            ],
        )
        mock_engine.analyze_endpoint.return_value = mock_result

        bridge = ValidationBridge()
        candidates = bridge.from_endpoint(
            {"path": "/api/users/123", "method": "GET", "host": "api.target.com"},
            target_id=1,
        )

        assert len(candidates) == 1
        assert candidates[0].vulnerability_type == VulnType.IDOR
        assert candidates[0].target_id == 1
        mock_engine.analyze_endpoint.assert_called_once_with(
            {"path": "/api/users/123", "method": "GET", "host": "api.target.com"}
        )


# ═══════════════════════════════════════════════════════════════
# validate_endpoint — ciclo completo con mock
# ═══════════════════════════════════════════════════════════════


class TestValidateEndpoint:
    @patch("core.validation.bridge.OffensiveEngine")
    @patch("core.validation.bridge.ValidationEngine")
    def test_validate_endpoint_cycle(self, mock_val_cls: MagicMock, mock_eng_cls: MagicMock):
        """validate_endpoint ejecuta el ciclo completo con mock."""
        # Mock OffensiveEngine
        mock_engine = MagicMock()
        mock_eng_cls.return_value = mock_engine
        mock_result = ReasonerResult(
            endpoint=EndpointInfo(path="/api/users/123", method="GET"),
            hypotheses=[
                Hypothesis(
                    vulnerability_type="idor",
                    endpoint="/api/users/123",
                    method="GET",
                    confidence=0.75,
                    parameters_of_interest=["user_id"],
                )
            ],
        )
        mock_engine.analyze_endpoint.return_value = mock_result

        # Mock ValidationEngine
        mock_validator = MagicMock()
        mock_val_cls.return_value = mock_validator
        mock_vresult = MagicMock()
        mock_vresult.candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR,
            method="GET",
            endpoint_path="/api/users/123",
        )
        mock_vresult.promoted = False
        mock_vresult.confidence = MagicMock()
        mock_vresult.confidence.score = 0.3
        mock_vresult.confidence.should_promote = False
        mock_validator.run.return_value = mock_vresult

        bridge = ValidationBridge()
        results = bridge.validate_endpoint(
            {"path": "/api/users/123", "method": "GET", "host": "api.target.com", "params": {"user_id": "123"}},
            target_id=1,
            dry_run=False,
        )

        assert len(results) == 1
        assert results[0].candidate.vulnerability_type == VulnType.IDOR
        mock_engine.analyze_endpoint.assert_called_once()
        mock_validator.run.assert_called_once()

    @patch("core.validation.bridge.ValidationBridge.from_reasoner_result")
    @patch("core.validation.bridge.OffensiveEngine")
    def test_no_candidates_when_none_qualify(self, mock_eng_cls: MagicMock, mock_from_reasoner: MagicMock):
        """Si ninguna hypothesis pasa el filtro económico, no se ejecuta validación."""
        mock_from_reasoner.return_value = []

        bridge = ValidationBridge()
        results = bridge.validate_endpoint(
            {"path": "/api/trivial", "method": "GET"},
            target_id=1,
        )

        assert len(results) == 0

    @patch("core.validation.bridge.OffensiveEngine")
    @patch("core.validation.bridge.ValidationEngine")
    def test_batch_validation(self, mock_val_cls: MagicMock, mock_eng_cls: MagicMock):
        """validate_batch maneja múltiples endpoints."""
        mock_engine = MagicMock()
        mock_eng_cls.return_value = mock_engine

        def _analyze_side_effect(ep):
            return ReasonerResult(
                endpoint=EndpointInfo(path=ep.get("path", ""), method=ep.get("method", "GET")),
                hypotheses=[
                    Hypothesis(
                        vulnerability_type="idor" if "user" in ep.get("path", "") else "ssrf",
                        endpoint=ep.get("path", ""),
                        method=ep.get("method", "GET"),
                        confidence=0.7,
                    )
                ],
            )

        mock_engine.analyze_endpoint.side_effect = _analyze_side_effect

        mock_validator = MagicMock()
        mock_val_cls.return_value = mock_validator
        mock_vresult = MagicMock()
        mock_vresult.candidate = AttackCandidate(
            vulnerability_type=VulnType.IDOR, method="GET", endpoint_path="/api/users/123"
        )
        mock_vresult.promoted = False
        mock_vresult.confidence = MagicMock()
        mock_vresult.confidence.score = 0.5
        mock_vresult.confidence.should_promote = False
        mock_validator.run.return_value = mock_vresult

        bridge = ValidationBridge()
        results = bridge.validate_batch(
            [
                {"path": "/api/users/123", "method": "GET"},
                {"path": "/api/fetch", "method": "POST"},
            ],
            target_id=1,
        )

        assert len(results) >= 1
        mock_engine.set_context.assert_called_once()
