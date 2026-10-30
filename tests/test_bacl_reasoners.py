"""Tests for BACL matrix + business-flow reasoners.

Positives pin detection, negatives pin honest silence, wiring pins
engine count, VulnType, scorer defaults and the feedback loop.
"""

from __future__ import annotations

from cores.offensive.engine import OffensiveEngine
from cores.offensive.models import EndpointInfo
from cores.offensive.reasoners.bacl import BaclMatrixReasoner, BusinessFlowReasoner


class TestBaclMatrixReasoner:
    def test_detects_role_param_with_object_ref(self):
        r = BaclMatrixReasoner()
        ep = EndpointInfo(
            path="/api/users/42",
            method="GET",
            params={"id": "42", "role": "admin"},
        )
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "bacl"
        assert "role" in hyps[0].parameters_of_interest
        assert hyps[0].confidence >= 0.1

    def test_detects_admin_path_split(self):
        r = BaclMatrixReasoner()
        ep = EndpointInfo(
            path="/admin/users/42",
            method="GET",
            params={"id": "42"},
            headers={"Authorization": "Bearer x"},
        )
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].severity == "high"

    def test_scope_note_requires_two_accounts(self):
        r = BaclMatrixReasoner()
        ep = EndpointInfo(path="/api/orders/7", method="GET", params={"order_id": "7", "tier": "pro"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert "two accounts" in hyps[0].test_instructions[0]
        assert hyps[0].alternative_explanations

    def test_silent_on_plain_endpoint(self):
        r = BaclMatrixReasoner()
        ep = EndpointInfo(path="/api/health", method="GET", params={})
        assert r.analyze(ep) == []

    def test_supported_methods(self):
        assert set(BaclMatrixReasoner().supported_methods()) == {"GET", "POST", "PUT", "PATCH", "DELETE"}


class TestBusinessFlowReasoner:
    def test_detects_checkout_with_price(self):
        r = BusinessFlowReasoner()
        ep = EndpointInfo(
            path="/api/checkout",
            method="POST",
            params={},
            body={"price": "99.99", "coupon": "WELCOME"},
        )
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "business_logic"
        assert hyps[0].severity == "high"
        assert "price" in hyps[0].parameters_of_interest

    def test_ignores_safe_methods(self):
        r = BusinessFlowReasoner()
        ep = EndpointInfo(path="/api/checkout", method="GET", params={"price": "10"})
        assert r.analyze(ep) == []

    def test_silent_without_flow_params(self):
        r = BusinessFlowReasoner()
        ep = EndpointInfo(path="/api/users", method="POST", params={}, body={"name": "x"})
        assert r.analyze(ep) == []

    def test_supported_methods(self):
        assert set(BusinessFlowReasoner().supported_methods()) == {"POST", "PUT", "PATCH", "DELETE"}


class TestBaclWiring:
    def test_engine_registers_eleven(self):
        engine = OffensiveEngine()
        assert len(engine._reasoners) == 21
        assert engine.get_reasoner("bacl") is not None
        assert engine.get_reasoner("business_logic") is not None

    def test_vuln_type_exists(self):
        from cores.validation.models import VulnType

        assert VulnType.BACL.value == "bacl"

    def test_scorer_defaults(self):
        from cores.validation.economic_scorer import (
            BASE_ACCEPTANCE,
            VALIDATION_EFFORT_MINUTES,
            VULN_PAYOUT_MULTIPLIER,
        )
        from cores.validation.models import VulnType

        assert VULN_PAYOUT_MULTIPLIER.get(VulnType.BACL) == 1.3
        assert BASE_ACCEPTANCE.get(VulnType.BACL) == 0.55
        assert VALIDATION_EFFORT_MINUTES.get(VulnType.BACL) == 10.0

    def test_feedback_loop(self):
        engine = OffensiveEngine()
        engine.record_outcome("bacl", "hyp-001", True)  # must not crash
        stats = engine.get_reasoner_stats()
        assert "bacl" in stats
        assert "business_logic" in stats

    def test_end_to_end_matrix_endpoint(self):
        engine = OffensiveEngine()
        result = engine.analyze_endpoint(
            {
                "path": "/api/admin/orders/9",
                "method": "GET",
                "params": {"order_id": "9"},
                "headers": {"Authorization": "Bearer x"},
            }
        )
        types = [h.vulnerability_type for h in result.hypotheses]
        assert "bacl" in types


class TestBaclTestMatrix:
    def _eps(self):
        from cores.offensive.models import EndpointInfo

        return [
            EndpointInfo(path="/api/users/42", method="GET", params={"id": "42"}),
            EndpointInfo(path="/api/users/42", method="PUT", params={"id": "42", "role": "user"}),
            EndpointInfo(path="/api/admin/users/42", method="GET", params={"id": "42"}),
            EndpointInfo(path="/api/health", method="GET", params={}),
        ]

    def test_matrix_groups_and_prioritizes(self):
        from cores.offensive.reasoners.bacl import build_bacl_test_matrix

        cases = build_bacl_test_matrix(self._eps())
        by_res = {c["resource"] for c in cases}
        assert "/api/users/{}" in by_res  # mismo objeto, 2 endpoints agrupados
        assert "/api/health" not in by_res  # sin refs ni roles: fuera
        kinds = {c["kind"] for c in cases}
        assert "cross_role_replay" in kinds
        assert "role_param_tamper" in kinds
        assert "dual_path_cross" in kinds  # user + admin twins
        assert any(c["priority"] == "P1" for c in cases)

    def test_matrix_empty_and_capped(self):
        from cores.offensive.models import EndpointInfo
        from cores.offensive.reasoners.bacl import MAX_MATRIX_CASES, build_bacl_test_matrix

        assert build_bacl_test_matrix([]) == []
        assert build_bacl_test_matrix(["nope"]) == []  # type: ignore[list-item]
        many = [EndpointInfo(path=f"/api/o{i}/1", method="GET", params={"id": "1"}) for i in range(200)]
        assert len(build_bacl_test_matrix(many)) <= MAX_MATRIX_CASES
