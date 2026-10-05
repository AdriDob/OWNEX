"""Tests for the Prompt Injection reasoner — LLM/AI-exposed surface.

Mirrors the mobile-reasoner suite style: positives pin detection,
negatives pin honest silence (no fabricated hypotheses), plus wiring
(engine count, VulnType, scorer defaults, feedback loop).
"""

from __future__ import annotations

from cores.offensive.engine import OffensiveEngine
from cores.offensive.models import EndpointInfo
from cores.offensive.reasoners.prompt_injection import PromptInjectionReasoner


class TestPromptInjectionReasoner:
    def test_detects_chat_completions(self):
        r = PromptInjectionReasoner()
        ep = EndpointInfo(
            path="/v1/chat/completions",
            method="POST",
            params={},
            body={"messages": [{"role": "user"}]},
        )
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].vulnerability_type == "prompt_injection"
        assert "messages" in hyps[0].parameters_of_interest
        assert hyps[0].confidence >= 0.1

    def test_detects_prompt_param_get(self):
        r = PromptInjectionReasoner()
        ep = EndpointInfo(path="/api/ask", method="GET", params={"prompt": "hello"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert "prompt" in hyps[0].parameters_of_interest

    def test_system_param_escalates_severity(self):
        r = PromptInjectionReasoner()
        ep = EndpointInfo(
            path="/api/generate",
            method="POST",
            params={},
            body={"system_prompt": "you are helpful", "input": "hi"},
        )
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert hyps[0].severity == "high"

    def test_scope_note_requires_authorization(self):
        r = PromptInjectionReasoner()
        ep = EndpointInfo(path="/api/chat", method="POST", params={}, body={"message": "hi"})
        hyps = r.analyze(ep)
        assert len(hyps) == 1
        assert "ONLY" in hyps[0].scope_check or "only" in hyps[0].scope_check.lower()
        assert hyps[0].alternative_explanations

    def test_silent_on_plain_endpoint(self):
        r = PromptInjectionReasoner()
        ep = EndpointInfo(path="/api/users", method="GET", params={"page": "1"})
        assert r.analyze(ep) == []

    def test_silent_on_crud_without_prompt_params(self):
        r = PromptInjectionReasoner()
        ep = EndpointInfo(path="/api/orders/42", method="GET", params={"id": "42"})
        assert r.analyze(ep) == []

    def test_supported_methods(self):
        assert set(PromptInjectionReasoner().supported_methods()) == {"GET", "POST"}


class TestPromptInjectionWiring:
    def test_engine_registers_nine(self):
        engine = OffensiveEngine()
        assert len(engine._reasoners) == 21
        assert engine.get_reasoner("prompt_injection") is not None

    def test_vuln_type_exists(self):
        from cores.validation.models import VulnType

        assert VulnType.PROMPT_INJECTION.value == "prompt_injection"

    def test_scorer_defaults(self):
        from cores.validation.economic_scorer import (
            BASE_ACCEPTANCE,
            VALIDATION_EFFORT_MINUTES,
            VULN_PAYOUT_MULTIPLIER,
        )
        from cores.validation.models import VulnType

        assert VULN_PAYOUT_MULTIPLIER.get(VulnType.PROMPT_INJECTION) == 1.2
        assert BASE_ACCEPTANCE.get(VulnType.PROMPT_INJECTION) == 0.50
        assert VALIDATION_EFFORT_MINUTES.get(VulnType.PROMPT_INJECTION) == 8.0

    def test_feedback_loop(self):
        engine = OffensiveEngine()
        engine.record_outcome("prompt_injection", "hyp-001", True)  # must not crash
        stats = engine.get_reasoner_stats()
        assert "prompt_injection" in stats

    def test_end_to_end_chat_endpoint(self):
        engine = OffensiveEngine()
        result = engine.analyze_endpoint(
            {
                "path": "/api/assistant/chat",
                "method": "POST",
                "params": {},
                "body": {"message": "hello"},
            }
        )
        types = [h.vulnerability_type for h in result.hypotheses]
        assert "prompt_injection" in types


class TestAiSurfaceDiscovery:
    def _eps(self):
        return [
            EndpointInfo(
                path="/v1/chat/completions",
                method="POST",
                params={},
                body={"messages": "hi", "tool": "query_db"},
            ),
            EndpointInfo(
                path="/api/docs/search",
                method="POST",
                params={"query": "x"},
                body={"retrieve": True},
            ),
            EndpointInfo(path="/api/health", method="GET", params={}),
        ]

    def test_discovers_ranked_surface(self):
        from cores.offensive.reasoners.prompt_injection import discover_ai_surface

        out = discover_ai_surface(self._eps())
        assert len(out) == 2  # health: fuera
        assert out[0]["ai_score"] >= out[1]["ai_score"]
        chat = next(e for e in out if e["endpoint"] == "/v1/chat/completions")
        assert "query_db" in chat["tool_hits"] or "tool" in chat["tool_hits"]
        docs = next(e for e in out if e["endpoint"] == "/api/docs/search")
        assert "retrieve" in docs["rag_hits"]

    def test_empty_and_noise(self):
        from cores.offensive.reasoners.prompt_injection import discover_ai_surface

        assert discover_ai_surface([]) == []
        assert discover_ai_surface(["nope"]) == []  # type: ignore[list-item]
        plain = [EndpointInfo(path="/api/users", method="GET", params={"id": "1"})]
        assert discover_ai_surface(plain) == []  # sin params IA: silencio honesto


class TestToolMatrix:
    def test_matrix_roles_and_priority(self):
        from cores.offensive.reasoners.prompt_injection import build_tool_matrix, discover_ai_surface

        eps = [
            EndpointInfo(path="/v1/agent/run", method="POST", params={}, body={"input": "x", "code_execution": True})
        ]
        surface = discover_ai_surface(eps)
        cases = build_tool_matrix(surface)
        assert cases
        assert {c["principal"] for c in cases} == {"low", "owner"}
        assert any(c["priority"] == "P1" for c in cases)  # code_execution
        assert all("transcript" in c["action"] for c in cases)

    def test_matrix_empty_without_tools(self):
        from cores.offensive.reasoners.prompt_injection import build_tool_matrix

        assert build_tool_matrix([]) == []
        assert build_tool_matrix([{"endpoint": "/x", "method": "GET", "tool_hits": []}]) == []


class TestRagPlaybook:
    def test_playbook_stages(self):
        from cores.offensive.reasoners.prompt_injection import discover_ai_surface, rag_poisoning_playbook

        eps = [EndpointInfo(path="/api/kb/ask", method="POST", params={"question": "x"}, body={"ingest": False})]
        steps = rag_poisoning_playbook(discover_ai_surface(eps))
        assert len(steps) == 1
        assert len(steps[0]["stages"]) == 5
        assert any("own" in s for s in steps[0]["stages"])  # solo fuentes propias

    def test_playbook_empty_without_rag(self):
        from cores.offensive.reasoners.prompt_injection import rag_poisoning_playbook

        assert rag_poisoning_playbook([]) == []
