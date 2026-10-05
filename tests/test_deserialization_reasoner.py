"""Tests for the deserialization/SSTI reasoner.

Positives pin detection (template engine, sink params, deser hints),
negatives pin honest silence, safety pins benign-only instructions, plus
wiring (engine count, VulnType, scorer, feedback).
"""

from __future__ import annotations

from cores.offensive.engine import OffensiveEngine
from cores.offensive.models import EndpointInfo
from cores.offensive.reasoners.deserialization import DeserializationReasoner


class TestDeserializationReasoner:
    def test_detects_template_engine_path(self):
        r = DeserializationReasoner()
        ep = EndpointInfo(path="/jinja2/render", method="GET", params={"q": "hi"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "deserialization"
        assert hyps[0].confidence >= 0.1

    def test_detects_sink_param_and_pickle(self):
        r = DeserializationReasoner()
        ep = EndpointInfo(path="/api/load", method="POST", params={}, body={"object": "x", "state": "y"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert "object" in hyps[0].parameters_of_interest

    def test_engine_visible_es_suficiente(self):
        r = DeserializationReasoner()
        ep = EndpointInfo(path="/jinja2/view", method="GET", params={"name": "home"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert "jinja2" in hyps[0].parameters_of_interest
        assert hyps[0].severity in ("low", "medium", "high")

    def test_safety_benign_payloads(self):
        r = DeserializationReasoner()
        ep = EndpointInfo(path="/twig/render", method="GET", params={"template": "t"})
        text = " ".join(r.analyze(ep)[0].test_instructions).lower()
        assert "benign" in text
        assert "7*7" in text or "math" in text
        assert "never exfiltrate" in text or "no exfiltration" in text

    def test_scope_note_authorized_only(self):
        r = DeserializationReasoner()
        ep = EndpointInfo(path="/freemarker/x", method="GET", params={"template": "t"})
        assert "ONLY" in r.analyze(ep)[0].scope_check or "only" in r.analyze(ep)[0].scope_check.lower()

    def test_silent_on_plain_endpoint(self):
        r = DeserializationReasoner()
        ep = EndpointInfo(path="/api/users", method="GET", params={"page": "1"})
        assert r.analyze(ep) == []

    def test_silent_get_sin_sinks(self):
        r = DeserializationReasoner()
        ep = EndpointInfo(path="/api/health", method="GET", params={})
        assert r.analyze(ep) == []

    def test_supported_methods(self):
        assert set(DeserializationReasoner().supported_methods()) == {"GET", "POST", "PUT", "PATCH"}


class TestDeserializationWiring:
    def test_engine_registers_fourteen(self):
        engine = OffensiveEngine()
        assert len(engine._reasoners) == 21
        assert engine.get_reasoner("deserialization") is not None

    def test_vuln_type_exists(self):
        from cores.validation.models import VulnType

        assert VulnType.DESERIALIZATION.value == "deserialization"

    def test_scorer_defaults(self):
        from cores.validation.economic_scorer import (
            BASE_ACCEPTANCE,
            VALIDATION_EFFORT_MINUTES,
            VULN_PAYOUT_MULTIPLIER,
        )
        from cores.validation.models import VulnType

        assert VULN_PAYOUT_MULTIPLIER.get(VulnType.DESERIALIZATION) == 2.0
        assert BASE_ACCEPTANCE.get(VulnType.DESERIALIZATION) == 0.45
        assert VALIDATION_EFFORT_MINUTES.get(VulnType.DESERIALIZATION) == 12.0

    def test_feedback_loop(self):
        engine = OffensiveEngine()
        engine.record_outcome("deserialization", "hyp-001", True)  # must not crash
        assert "deserialization" in engine.get_reasoner_stats()

    def test_end_to_end_template_endpoint(self):
        engine = OffensiveEngine()
        result = engine.analyze_endpoint(
            {"path": "/jinja2/preview", "method": "GET", "params": {"template": "hi"}},
        )
        types = [h.vulnerability_type for h in result.hypotheses]
        assert "deserialization" in types
