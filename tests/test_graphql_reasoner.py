"""Tests for the GraphQL reasoner + upside tracker.

Positives pin detection (introspection/cost/batch/authz), negatives pin
honest silence, safety caps are pinned (no DoS-grade instructions), plus
wiring (engine count, VulnType, scorer, feedback) and the upside block.
"""

from __future__ import annotations

from cores.offensive.engine import OffensiveEngine
from cores.offensive.models import EndpointInfo
from cores.offensive.reasoners.graphql import MAX_SAFE_BATCH, MAX_SAFE_DEPTH, GraphQLReasoner


class TestGraphQLReasoner:
    def test_detects_graphql_post(self):
        r = GraphQLReasoner()
        ep = EndpointInfo(path="/graphql", method="POST", params={}, body={"query": "{ user { id } }"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "graphql"
        assert "query" in hyps[0].parameters_of_interest
        assert hyps[0].confidence >= 0.1

    def test_detects_mutation_with_id(self):
        r = GraphQLReasoner()
        ep = EndpointInfo(
            path="/api/gql",
            method="POST",
            params={},
            body={"mutation": "x", "variables": {"user_id": "1"}},
        )
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].severity == "high"

    def test_safety_caps_pinned(self):
        r = GraphQLReasoner()
        ep = EndpointInfo(path="/graphql", method="POST", params={}, body={"query": "q"})
        text = " ".join(r.analyze(ep)[0].test_instructions)
        assert str(MAX_SAFE_DEPTH) in text
        assert str(MAX_SAFE_BATCH) in text
        assert MAX_SAFE_DEPTH <= 10
        assert MAX_SAFE_BATCH <= 10

    def test_scope_note_authorized_only(self):
        r = GraphQLReasoner()
        ep = EndpointInfo(path="/graphql", method="POST", params={}, body={"query": "q"})
        hyps = r.analyze(ep)
        assert "ONLY" in hyps[0].scope_check or "only" in hyps[0].scope_check.lower()
        assert hyps[0].alternative_explanations

    def test_silent_on_plain_endpoint(self):
        r = GraphQLReasoner()
        ep = EndpointInfo(path="/api/users", method="GET", params={"page": "1"})
        assert r.analyze(ep) == []

    def test_ignores_non_graphql_methods(self):
        r = GraphQLReasoner()
        ep = EndpointInfo(path="/graphql", method="DELETE", params={}, body={"query": "q"})
        assert r.analyze(ep) == []

    def test_supported_methods(self):
        assert set(GraphQLReasoner().supported_methods()) == {"GET", "POST"}


class TestGraphQLWiring:
    def test_engine_registers_twelve(self):
        engine = OffensiveEngine()
        assert len(engine._reasoners) == 21
        assert engine.get_reasoner("graphql") is not None

    def test_vuln_type_exists(self):
        from cores.validation.models import VulnType

        assert VulnType.GRAPHQL.value == "graphql"

    def test_scorer_defaults(self):
        from cores.validation.economic_scorer import (
            BASE_ACCEPTANCE,
            VALIDATION_EFFORT_MINUTES,
            VULN_PAYOUT_MULTIPLIER,
        )
        from cores.validation.models import VulnType

        assert VULN_PAYOUT_MULTIPLIER.get(VulnType.GRAPHQL) == 1.4
        assert BASE_ACCEPTANCE.get(VulnType.GRAPHQL) == 0.50
        assert VALIDATION_EFFORT_MINUTES.get(VulnType.GRAPHQL) == 12.0

    def test_feedback_loop(self):
        engine = OffensiveEngine()
        engine.record_outcome("graphql", "hyp-001", True)  # must not crash
        assert "graphql" in engine.get_reasoner_stats()

    def test_end_to_end_graphql_endpoint(self):
        engine = OffensiveEngine()
        result = engine.analyze_endpoint(
            {"path": "/graphql", "method": "POST", "params": {}, "body": {"query": "{ me { id } }"}},
        )
        types = [h.vulnerability_type for h in result.hypotheses]
        assert "graphql" in types


class TestUpsideBlock:
    def test_snapshot_carries_upside(self, tmp_path, monkeypatch):
        from cores.direct_work_engine.income_dashboard import IncomeDashboard

        snapshot = IncomeDashboard().snapshot()
        assert "upside" in snapshot
        up = snapshot["upside"]
        assert {"open_confirmed", "by_severity", "upside_low_usd", "upside_high_usd", "note"} <= set(up)
        assert up["upside_low_usd"] >= 0.0
        assert up["upside_high_usd"] >= up["upside_low_usd"]
        assert "no promesa" in up["note"] or "Sin datos" in up["note"]
