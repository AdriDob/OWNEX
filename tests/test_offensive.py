"""Tests for Offensive Intelligence v2+v3 — Relationship Engine, Contradiction Engine, Enhanced Triager, Planner, Curiosity, Transitive Ownership."""

from __future__ import annotations

from core.offensive.contradiction import ContradictionEngine
from core.offensive.curiosity import CuriosityEngine
from core.offensive.engine import OffensiveEngine
from core.offensive.models import (
    Contradiction,
    EndpointInfo,
    Hypothesis,
)
from core.offensive.planner import InvestigationPlanner
from core.offensive.relationship import EndpointRelationshipEngine
from core.offensive.triager import TriagerSimulator

# ── Relationship Engine ───────────────────────────────────────────────


class TestEndpointRelationshipEngine:
    def setup_method(self):
        self.engine = EndpointRelationshipEngine()

    def test_parent_child_detection(self):
        parent = EndpointInfo(path="/api/users", method="GET")
        child = EndpointInfo(path="/api/users/{id}", method="GET", params={"id": "{id}"})
        ctx = self.engine.analyze(child, [parent, child])
        assert ctx.parent_endpoint == "/api/users"

    def test_collection_detection(self):
        parent = EndpointInfo(path="/api/users", method="GET")
        child = EndpointInfo(path="/api/users/{id}", method="GET", params={"id": "{id}"})
        ctx = self.engine.analyze(parent, [parent, child])
        assert ctx.collection_endpoint == "/api/users"

    def test_child_endpoints_detected(self):
        parent = EndpointInfo(path="/api/users", method="GET")
        child1 = EndpointInfo(path="/api/users/{id}", method="GET", params={"id": "{id}"})
        child2 = EndpointInfo(path="/api/users/{id}/avatar", method="POST", params={"id": "{id}"})
        ctx = self.engine.analyze(parent, [parent, child1, child2])
        assert len(ctx.child_endpoints) >= 1

    def test_sibling_detection(self):
        ep1 = EndpointInfo(path="/api/users/{id}/profile", method="GET", params={"id": "{id}"})
        ep2 = EndpointInfo(path="/api/users/{id}/settings", method="GET", params={"id": "{id}"})
        ctx = self.engine.analyze(ep1, [ep1, ep2])
        assert "/api/users/{id}/settings" in ctx.siblings

    def test_ownership_graph(self):
        endpoints = [
            EndpointInfo(path="/api/users/{userId}/organizations/{orgId}", method="GET"),
            EndpointInfo(path="/api/organizations/{orgId}/projects/{projectId}", method="GET"),
        ]
        edges = self.engine.build_ownership_graph(endpoints)
        assert len(edges) >= 1
        assert any(e.parent_resource == "organizations" for e in edges)

    def test_similar_patterns(self):
        ep1 = EndpointInfo(path="/api/users/{id}", method="GET", params={"id": "{id}"})
        ep2 = EndpointInfo(path="/api/orders/{id}", method="GET", params={"id": "{id}"})
        ctx = self.engine.analyze(ep1, [ep1, ep2])
        assert len(ctx.similar_pattern_endpoints) >= 1

    def test_no_relationship_for_unrelated(self):
        ep1 = EndpointInfo(path="/api/health", method="GET")
        ep2 = EndpointInfo(path="/api/v1/status", method="GET")
        ctx = self.engine.analyze(ep1, [ep1, ep2])
        assert ctx.parent_endpoint == ""
        assert len(ctx.siblings) == 0

    def test_build_relationships(self):
        eps = [
            EndpointInfo(path="/api/users", method="GET"),
            EndpointInfo(path="/api/users/{id}", method="GET", params={"id": "{id}"}),
        ]
        rels = self.engine.build_relationships(eps)
        assert len(rels) >= 1
        assert any(r.relationship_type == "parent_child" for r in rels)


# ── Contradiction Engine ─────────────────────────────────────────────


class TestContradictionEngine:
    def setup_method(self):
        self.engine = ContradictionEngine()

    def test_idor_contradictions(self):
        h = Hypothesis(vulnerability_type="idor", confidence=0.8, severity="high")
        contradictions = self.engine.attack(h)
        assert len(contradictions) >= 5
        assert any(c.label == "Ownership verified server-side" for c in contradictions)
        assert any(c.label == "UUID/GUID not enumerable" for c in contradictions)

    def test_low_confidence_contradiction(self):
        h = Hypothesis(vulnerability_type="idor", confidence=0.2, severity="low")
        contradictions = self.engine.attack(h)
        labels = [c.label for c in contradictions]
        assert "Low confidence hypothesis" in labels

    def test_missing_reproducibility(self):
        h = Hypothesis(vulnerability_type="idor", confidence=0.7, severity="high", reproducibility_notes="")
        contradictions = self.engine.attack(h)
        labels = [c.label for c in contradictions]
        assert "Missing reproduction steps" in labels

    def test_no_duplicates(self):
        h = Hypothesis(vulnerability_type="idor", confidence=0.8, severity="high")
        contradictions = self.engine.attack(h)
        labels = [c.label for c in contradictions]
        assert len(labels) == len(set(labels))

    def test_contradiction_has_rule_out(self):
        h = Hypothesis(vulnerability_type="idor", confidence=0.8, severity="high")
        contradictions = self.engine.attack(h)
        for c in contradictions:
            assert c.label  # non-empty label
            assert c.confidence_reduction > 0

    def test_confidence_reduction_applied(self):
        h = Hypothesis(
            vulnerability_type="idor",
            confidence=0.8,
            severity="high",
            alternative_explanations=[{"label": "test"}],
            reproducibility_notes="Step by step",
        )
        contradictions = self.engine.attack(h)
        total_reduction = sum(c.confidence_reduction for c in contradictions)
        assert total_reduction > 0.5  # multiple contradictions reduce significantly


# ── Enhanced Triager ─────────────────────────────────────────────────


class TestEnhancedTriager:
    def setup_method(self):
        self.triager = TriagerSimulator()

    def _make_hypothesis(self, complete: bool = True) -> Hypothesis:
        h = Hypothesis(
            vulnerability_type="idor",
            endpoint="/api/users/1",
            method="GET",
            confidence=0.85,
            severity="high",
            summary="IDOR in user endpoint",
            description="The endpoint does not verify ownership",
            test_instructions=["Create account A", "Create account B", "Swap IDs"],
            why_human_would_investigate="Strong IDOR indicators",
            why_triager_might_reject="Needs second account confirmation",
            scope_check="In scope for this program",
            reproducibility_notes="Use two accounts, swap user_id",
            alternative_explanations=[{"label": "Ownership verified"}],
            signals=["param:id", "method:GET", "path_depth:3"],
            contradictions=[Contradiction(label="Ownership verified", description="test", confidence_reduction=0.3)],
        )
        if not complete:
            h.test_instructions = []
            h.description = ""
            h.scope_check = ""
            h.reproducibility_notes = ""
            h.alternative_explanations = []
            h.contradictions = []
        return h

    def test_evidence_scoring_complete(self):
        h = self._make_hypothesis(complete=True)
        result = self.triager.evaluate(h)
        assert result["evidence_completeness"]["score"] >= 70

    def test_evidence_scoring_poor(self):
        h = self._make_hypothesis(complete=False)
        result = self.triager.evaluate(h)
        assert result["evidence_completeness"]["score"] < 50

    def test_acceptance_prediction_high(self):
        h = self._make_hypothesis(complete=True)
        result = self.triager.evaluate(h)
        assert result["acceptance_prediction"]["probability"] >= 0.4

    def test_acceptance_prediction_low(self):
        h = self._make_hypothesis(complete=False)
        h.confidence = 0.1
        h.severity = "low"
        result = self.triager.evaluate(h)
        assert result["acceptance_prediction"]["probability"] < 0.5

    def test_triager_questions_generated(self):
        h = self._make_hypothesis(complete=False)
        result = self.triager.evaluate(h)
        assert len(result["acceptance_prediction"]["questions_triager_will_ask"]) > 0

    def test_verdict_report_ready(self):
        h = self._make_hypothesis(complete=True)
        h.confidence = 0.95
        h.severity = "critical"
        h.signals = ["a", "b", "c", "d", "e"]
        result = self.triager.evaluate(h)
        assert result["verdict"] in ("report_ready", "needs_improvement")

    def test_verdict_insufficient(self):
        h = self._make_hypothesis(complete=False)
        h.confidence = 0.05
        h.severity = "low"
        result = self.triager.evaluate(h)
        assert result["verdict"] == "insufficient"

    def test_gaps_listed(self):
        h = self._make_hypothesis(complete=False)
        result = self.triager.evaluate(h)
        assert len(result["evidence_completeness"]["gaps"]) > 0

    def test_strong_points_listed(self):
        h = self._make_hypothesis(complete=True)
        result = self.triager.evaluate(h)
        assert len(result["evidence_completeness"]["strong_points"]) > 0

    def test_positive_signals_present(self):
        h = self._make_hypothesis(complete=True)
        result = self.triager.evaluate(h)
        assert len(result["acceptance_prediction"]["positive_signals"]) > 0

    def test_risk_factors_present(self):
        h = self._make_hypothesis(complete=False)
        result = self.triager.evaluate(h)
        assert len(result["acceptance_prediction"]["risk_factors"]) > 0


# ── Integration: Engine v2 ───────────────────────────────────────────


class TestOffensiveEngineV2:
    def setup_method(self):
        self.engine = OffensiveEngine()

    def test_endpoint_relationship_context(self):
        self.engine.set_context(
            [
                {"path": "/api/users", "method": "GET"},
                {"path": "/api/users/{id}", "method": "GET", "params": {"id": "{id}"}},
            ]
        )
        result = self.engine.analyze_endpoint(
            {
                "path": "/api/users/{id}",
                "method": "GET",
                "params": {"id": "123"},
            }
        )
        assert result.hypotheses
        ctx = result.hypotheses[0].relationship_context
        assert ctx.parent_endpoint == "/api/users" or ctx.collection_endpoint == "/api/users"

    def test_contradictions_in_hypothesis(self):
        result = self.engine.analyze_endpoint(
            {
                "path": "/api/users/123",
                "method": "DELETE",
                "params": {"id": "123"},
            }
        )
        if result.hypotheses:
            assert len(result.hypotheses[0].contradictions) > 0

    def test_evidence_score_in_result(self):
        result = self.engine.analyze_endpoint(
            {
                "path": "/api/users/1",
                "method": "GET",
                "params": {"id": "1"},
            }
        )
        if result.hypotheses:
            assert result.hypotheses[0].evidence_completeness.score >= 0

    def test_acceptance_prediction_in_result(self):
        result = self.engine.analyze_endpoint(
            {
                "path": "/api/users/1",
                "method": "GET",
                "params": {"id": "1"},
            }
        )
        if result.hypotheses:
            assert result.hypotheses[0].acceptance_prediction.probability > 0

    def test_analyze_collection(self):
        endpoints = [
            {"path": "/api/users", "method": "GET"},
            {"path": "/api/users/{id}", "method": "GET", "params": {"id": "{id}"}},
            {"path": "/api/users/{id}/delete", "method": "DELETE", "params": {"id": "{id}"}},
            {"path": "/api/status", "method": "GET", "params": {"v": "1"}},
        ]
        result = self.engine.analyze_collection(endpoints)
        assert result["total_endpoints"] == 4
        assert "top_hypotheses" in result
        assert len(result["top_hypotheses"]) >= 1

    def test_collection_top_hypothesis_ordering(self):
        self.engine.set_context(
            [
                {"path": "/api/users/{id}", "method": "GET", "params": {"id": "{id}"}},
                {"path": "/api/public/status", "method": "GET", "params": {}},
            ]
        )
        r1 = self.engine.analyze_endpoint({"path": "/api/users/{id}", "method": "GET", "params": {"id": "1"}})
        r2 = self.engine.analyze_endpoint({"path": "/api/public/status", "method": "GET", "params": {}})
        assert r1.max_confidence >= r2.max_confidence

    def test_to_dict_includes_v2_fields(self):
        result = self.engine.analyze_endpoint(
            {
                "path": "/api/users/1",
                "method": "GET",
                "params": {"id": "1"},
            }
        )
        d = result.to_dict()
        assert "relationships" in d
        assert "ownership_edges" in d
        if result.hypotheses:
            hd = result.hypotheses[0].to_dict()
            assert "contradictions" in hd
            assert "evidence_completeness" in hd
            assert "acceptance_prediction" in hd
            assert "relationship_context" in hd


# ── Investigation Planner ──────────────────────────────────────────


class TestInvestigationPlanner:
    def setup_method(self):
        self.planner = InvestigationPlanner()

    def _make_hypothesis(self, vtype: str = "idor", confidence: float = 0.7, severity: str = "high") -> Hypothesis:
        return Hypothesis(
            id="test-hyp-1",
            vulnerability_type=vtype,
            endpoint="/api/users/123",
            method="GET",
            confidence=confidence,
            severity=severity,
            summary=f"Potential {vtype} in /api/users/123",
        )

    def test_plan_has_steps(self):
        hyp = self._make_hypothesis()
        plan = self.planner.plan(hyp)
        assert len(plan.steps) > 0
        assert plan.hypothesis_id == "test-hyp-1"

    def test_plan_has_all_phases(self):
        hyp = self._make_hypothesis()
        plan = self.planner.plan(hyp)
        phases = {s.phase for s in plan.steps}
        assert "recon" in phases
        assert "probe" in phases
        assert "attack" in phases
        assert "document" in phases

    def test_plan_priority_high_for_high_confidence(self):
        hyp = self._make_hypothesis(confidence=0.8)
        plan = self.planner.plan(hyp)
        assert plan.priority == "high"

    def test_plan_priority_medium_for_low_confidence(self):
        hyp = self._make_hypothesis(confidence=0.3)
        plan = self.planner.plan(hyp)
        assert plan.priority == "medium"

    def test_plan_per_vuln_type(self):
        for vtype in ("idor", "ssrf", "auth_bypass", "xss", "sqli"):
            hyp = self._make_hypothesis(vtype=vtype)
            plan = self.planner.plan(hyp)
            assert len(plan.steps) >= 5, f"{vtype} has only {len(plan.steps)} steps"

    def test_plan_to_dict(self):
        hyp = self._make_hypothesis()
        plan = self.planner.plan(hyp)
        d = plan.to_dict()
        assert "steps" in d
        assert "vulnerability_type" in d
        assert "estimated_effort" in d
        assert len(d["steps"]) > 0

    def test_plan_has_prerequisites(self):
        hyp = self._make_hypothesis(vtype="ssrf")
        plan = self.planner.plan(hyp)
        assert len(plan.prerequisites) >= 2

    def test_plan_has_alternative_approaches(self):
        hyp = self._make_hypothesis(vtype="idor")
        plan = self.planner.plan(hyp)
        assert len(plan.alternative_approaches) >= 2

    def test_plan_effort_high_for_critical_severity(self):
        hyp = self._make_hypothesis(severity="critical")
        plan = self.planner.plan(hyp)
        assert plan.estimated_effort == "high"


# ── Curiosity Engine ───────────────────────────────────────────────


class TestCuriosityEngine:
    def setup_method(self):
        self.engine = CuriosityEngine()

    def _make_hypothesis(self, vtype: str = "idor") -> Hypothesis:
        return Hypothesis(
            vulnerability_type=vtype,
            endpoint="/api/users/123",
            method="GET",
            confidence=0.7,
            severity="high",
            summary=f"Potential {vtype} in /api/users/123",
        )

    def test_explore_returns_questions(self):
        hyp = self._make_hypothesis()
        result = self.engine.explore(hyp)
        assert len(result.questions) > 0

    def test_explore_has_blind_spots(self):
        hyp = self._make_hypothesis()
        result = self.engine.explore(hyp)
        assert len(result.blind_spots) > 0

    def test_explore_has_recommended_focus(self):
        hyp = self._make_hypothesis()
        result = self.engine.explore(hyp)
        assert len(result.recommended_focus) > 0

    def test_explore_by_type(self):
        for vtype in ("idor", "ssrf", "auth_bypass", "xss", "sqli", "generic"):
            hyp = self._make_hypothesis(vtype=vtype)
            result = self.engine.explore(hyp)
            assert len(result.questions) >= 1, f"{vtype} has no questions"

    def test_question_has_all_fields(self):
        hyp = self._make_hypothesis()
        result = self.engine.explore(hyp)
        q = result.questions[0]
        assert q.question
        assert q.category
        assert q.rationale
        assert q.test_suggestion

    def test_question_categories_valid(self):
        hyp = self._make_hypothesis()
        result = self.engine.explore(hyp)
        valid = {"auth", "logic", "business", "technical", "edge_case"}
        for q in result.questions:
            assert q.category in valid, f"Invalid category: {q.category}"

    def test_explore_endpoint_direct(self):
        result = self.engine.explore_endpoint("/api/users/123", "GET", "idor")
        assert len(result.questions) >= 3
        assert result.endpoint == "/api/users/123"
        assert result.method == "GET"

    def test_to_dict_includes_questions(self):
        hyp = self._make_hypothesis()
        result = self.engine.explore(hyp)
        d = result.to_dict()
        assert "questions" in d
        assert "blind_spots" in d
        assert "recommended_focus" in d
        assert len(d["questions"]) > 0


# ── Transitive Ownership ───────────────────────────────────────────


class TestTransitiveOwnership:
    def setup_method(self):
        self.engine = EndpointRelationshipEngine()

    def _make_edges(self):
        from core.offensive.models import OwnershipEdge

        return [
            OwnershipEdge(parent_resource="user", child_resource="organization", confidence=0.55, via_param="userId"),
            OwnershipEdge(parent_resource="organization", child_resource="project", confidence=0.55, via_param="orgId"),
        ]

    def test_transitive_chain_detected(self):
        edges = self._make_edges()
        transitive = self.engine.build_transitive_ownership_graph(edges)
        assert any(e.parent_resource == "user" and e.child_resource == "project" for e in transitive)

    def test_transitive_confidence_decay(self):
        edges = self._make_edges()
        transitive = self.engine.build_transitive_ownership_graph(edges, confidence_decay=0.5)
        for e in transitive:
            if e.parent_resource == "user" and e.child_resource == "project":
                expected = 0.55 * 0.5 * 0.55 * 0.5
                assert abs(e.confidence - expected) < 0.01

    def test_no_false_edges(self):
        from core.offensive.models import OwnershipEdge

        edges = [
            OwnershipEdge(parent_resource="a", child_resource="b", confidence=0.5, via_param="aId"),
        ]
        transitive = self.engine.build_transitive_ownership_graph(edges)
        assert all(e.parent_resource != "b" for e in transitive)

    def test_deep_chain(self):
        from core.offensive.models import OwnershipEdge

        edges = [
            OwnershipEdge(parent_resource="a", child_resource="b", confidence=0.5, via_param="aId"),
            OwnershipEdge(parent_resource="b", child_resource="c", confidence=0.5, via_param="bId"),
            OwnershipEdge(parent_resource="c", child_resource="d", confidence=0.5, via_param="cId"),
        ]
        transitive = self.engine.build_transitive_ownership_graph(edges)
        assert any(e.parent_resource == "a" and e.child_resource == "d" for e in transitive)
        assert any(e.parent_resource == "a" and e.child_resource == "c" for e in transitive)
        assert any(e.parent_resource == "b" and e.child_resource == "d" for e in transitive)

    def test_to_dict_includes_transitive(self):
        engine = OffensiveEngine()
        engine.set_context(
            [
                {"path": "/api/users/{userId}/organizations/{orgId}", "method": "GET"},
                {"path": "/api/organizations/{orgId}/projects/{projectId}", "method": "GET"},
            ]
        )
        result = engine.analyze_endpoint(
            {
                "path": "/api/users/1",
                "method": "GET",
                "params": {"id": "1"},
            }
        )
        d = result.to_dict()
        assert "transitive_ownership" in d


# ── Integration: v3 fields in pipeline ────────────────────────────


class TestOffensiveEngineV3:
    def setup_method(self):
        self.engine = OffensiveEngine()

    def test_investigation_plan_in_result(self):
        result = self.engine.analyze_endpoint(
            {
                "path": "/api/users/1",
                "method": "GET",
                "params": {"id": "1"},
            }
        )
        if result.hypotheses:
            assert result.investigation_plan is not None

    def test_curiosity_in_result(self):
        result = self.engine.analyze_endpoint(
            {
                "path": "/api/users/1",
                "method": "GET",
                "params": {"id": "1"},
            }
        )
        if result.hypotheses:
            assert result.curiosity is not None

    def test_to_dict_includes_v3_fields(self):
        result = self.engine.analyze_endpoint(
            {
                "path": "/api/users/1",
                "method": "GET",
                "params": {"id": "1"},
            }
        )
        d = result.to_dict()
        assert "investigation_plan" in d
        assert "curiosity" in d
        assert "transitive_ownership" in d

    def test_v3_pipeline_no_crash(self):
        endpoints = [
            {"path": "/api/users/{userId}/organizations/{orgId}", "method": "GET"},
            {"path": "/api/users/1", "method": "GET", "params": {"id": "1"}},
            {"path": "/api/users", "method": "GET"},
            {"path": "/api/public/status", "method": "GET"},
            {"path": "/api/users/{id}/delete", "method": "DELETE", "params": {"id": "{id}"}},
        ]
        collection = self.engine.analyze_collection(endpoints)
        assert collection["total_endpoints"] == 5
        assert "ownership_graph" in collection
        assert collection["total_hypotheses"] >= 0


# ── New Reasoners (v3.5) ─────────────────────────────────────────


class TestSSRFReasoner:
    def setup_method(self):
        from core.offensive.reasoners.ssrf import SSRFReasoner

        self.reasoner = SSRFReasoner()

    def _ep(self, **kw):
        from core.offensive.models import EndpointInfo

        default = {"path": "/api/proxy", "method": "GET", "params": {"url": "http://example.com"}}
        default.update(kw)
        return EndpointInfo(**default)

    def test_url_param_detected(self):
        ep = self._ep(params={"url": "http://evil.com"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1
        assert hyps[0].vulnerability_type == "ssrf"

    def test_target_param_detected(self):
        ep = self._ep(params={"target": "http://internal"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_webhook_param_detected(self):
        ep = self._ep(params={"webhook": "https://callback.example.com"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_proxy_path_indicator(self):
        ep = self._ep(path="/api/fetch-external", params={"url": "http://test.com"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_no_url_params_returns_empty(self):
        ep = self._ep(params={"name": "hello", "age": "25"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) == 0

    def test_body_url_detected(self):
        ep = self._ep(body={"image_url": "http://evil.com/photo.jpg"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_alternative_explanations(self):
        ep = self._ep(params={"url": "http://test.com"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1
        assert len(hyps[0].alternative_explanations) >= 2

    def test_supported_methods(self):
        methods = self.reasoner.supported_methods()
        assert "GET" in methods
        assert "POST" in methods


class TestAuthBypassReasoner:
    def setup_method(self):
        from core.offensive.reasoners.auth_bypass import AuthBypassReasoner

        self.reasoner = AuthBypassReasoner()

    def _ep(self, **kw):
        from core.offensive.models import EndpointInfo

        default = {"path": "/api/admin/users", "method": "GET"}
        default.update(kw)
        return EndpointInfo(**default)

    def test_admin_path_detected(self):
        ep = self._ep(path="/api/admin/dashboard")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1
        assert hyps[0].vulnerability_type == "auth_bypass"

    def test_internal_path_detected(self):
        ep = self._ep(path="/internal/health")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_debug_path_detected(self):
        ep = self._ep(path="/api/debug/config")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_no_public_path_returns_empty(self):
        ep = self._ep(path="/api/public/status")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) == 0

    def test_path_traversal_detected(self):
        ep = self._ep(path="/api/users/../admin/panel")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_env_endpoint_high_confidence(self):
        ep = self._ep(path="/api/v1/.env")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1
        assert hyps[0].confidence >= 0.25  # .env is a strong signal

    def test_options_method_signal(self):
        ep = self._ep(path="/api/admin/users", method="OPTIONS")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_deep_path_signal(self):
        ep = self._ep(path="/api/v1/users/1/organizations/2/projects/3/settings")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_alternative_explanations(self):
        ep = self._ep(path="/api/admin/users")
        hyps = self.reasoner.analyze(ep)
        assert len(hyps[0].alternative_explanations) >= 2


class TestXSSReasoner:
    def setup_method(self):
        from core.offensive.reasoners.xss import XSSReasoner

        self.reasoner = XSSReasoner()

    def _ep(self, **kw):
        from core.offensive.models import EndpointInfo

        default = {"path": "/api/search", "method": "GET", "params": {"q": "test"}}
        default.update(kw)
        return EndpointInfo(**default)

    def test_search_param_detected(self):
        ep = self._ep(params={"q": "hello"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1
        assert hyps[0].vulnerability_type == "xss"

    def test_comment_param_detected(self):
        ep = self._ep(path="/api/comment", params={"message": "hello"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_callback_param_detected(self):
        ep = self._ep(params={"callback": "myFunc"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_html_in_value_detected(self):
        ep = self._ep(params={"name": "<script>alert(1)</script>"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_response_reflection_detected(self):
        ep = self._ep(
            params={"name": "John"},
            response_sample={"result": "Hello John, welcome!"},
        )
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_irrelevant_params_return_empty(self):
        ep = self._ep(path="/api/status", params={"version": "1.0"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) == 0

    def test_body_text_fields_detected(self):
        ep = self._ep(method="POST", body={"comment": "Nice post!", "author": "test"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_alternative_explanations(self):
        ep = self._ep(params={"q": "search"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps[0].alternative_explanations) >= 2


class TestSQLiReasoner:
    def setup_method(self):
        from core.offensive.reasoners.sqli import SQLiReasoner

        self.reasoner = SQLiReasoner()

    def _ep(self, **kw):
        from core.offensive.models import EndpointInfo

        default = {"path": "/api/users", "method": "GET", "params": {"id": "1"}}
        default.update(kw)
        return EndpointInfo(**default)

    def test_id_param_detected(self):
        ep = self._ep(params={"id": "1"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1
        assert hyps[0].vulnerability_type == "sqli"

    def test_search_param_detected(self):
        ep = self._ep(path="/api/search", params={"q": "test"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_sql_error_in_response_detected(self):
        ep = self._ep(
            params={"id": "1"},
            response_sample={"error": "SQL syntax error near '1'' at line 1"},
        )
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_sqli_chars_in_value_detected(self):
        ep = self._ep(params={"id": "1' OR '1'='1"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1

    def test_irrelevant_params_low_confidence(self):
        ep = self._ep(params={"format": "json", "pretty": "true"})
        hyps = self.reasoner.analyze(ep)
        # /api/users path is database-backed, so low confidence hypothesis is acceptable
        if hyps:
            assert hyps[0].confidence <= 0.3  # Should not be high confidence

    def test_sql_error_high_confidence(self):
        ep = self._ep(
            params={"id": "1"},
            response_sample={"sql": "ORA-01756: quoted string not properly terminated"},
        )
        hyps = self.reasoner.analyze(ep)
        assert len(hyps) >= 1
        assert hyps[0].severity in ("high", "critical")

    def test_alternative_explanations(self):
        ep = self._ep(params={"id": "1"})
        hyps = self.reasoner.analyze(ep)
        assert len(hyps[0].alternative_explanations) >= 2

    def test_supported_methods(self):
        methods = self.reasoner.supported_methods()
        assert "GET" in methods
        assert "POST" in methods


class TestReasonerFeedback:
    def setup_method(self):
        from core.offensive.reasoners.idor import IDORReasoner

        self.reasoner = IDORReasoner()

    def test_record_outcome_confirmed(self):
        self.reasoner.record_outcome("hyp-001", True)
        stats = self.reasoner.get_outcome_stats()
        assert stats["confirmed"] == 1
        assert stats["multiplier"] >= 1.0

    def test_record_outcome_rejected(self):
        self.reasoner.record_outcome("hyp-002", False)
        stats = self.reasoner.get_outcome_stats()
        assert stats["rejected"] == 1

    def test_confidence_multiplier_effect(self):
        self.reasoner.record_outcome("hyp-003", True)
        self.reasoner.record_outcome("hyp-004", True)
        adjusted = self.reasoner.apply_confidence_multiplier(0.5)
        assert adjusted > 0.5
        assert adjusted <= 1.0

    def test_stats_empty_initially(self):
        from core.offensive.reasoners.idor import IDORReasoner

        r = IDORReasoner()
        stats = r.get_outcome_stats()
        assert stats["total"] == 0

    def test_engine_records_outcome(self):
        from core.offensive.engine import OffensiveEngine

        engine = OffensiveEngine()
        engine.record_outcome("idor", "hyp-005", True)
        stats = engine.get_reasoner_stats()
        assert "idor" in stats
        assert stats["idor"]["confirmed"] >= 1

    def test_engine_outcome_unknown_reasoner(self):
        from core.offensive.engine import OffensiveEngine

        engine = OffensiveEngine()
        engine.record_outcome("nonexistent", "hyp-006", True)  # Should not crash


class TestEngineV3ReasonerRegistration:
    def setup_method(self):
        from core.offensive.engine import OffensiveEngine

        self.engine = OffensiveEngine()

    def test_five_reasoners_registered(self):
        assert len(self.engine._reasoners) == 5

    def test_reasoner_types(self):
        types = [r.vulnerability_type for r in self.engine._reasoners]
        assert "idor" in types
        assert "ssrf" in types
        assert "auth_bypass" in types
        assert "xss" in types
        assert "sqli" in types

    def test_each_reasoner_generates_hypotheses(self):
        ep = {
            "path": "/api/users/1/admin/webhook",
            "method": "GET",
            "params": {
                "id": "1",
                "url": "http://evil.com",
                "q": "<script>alert(1)</script>",
            },
        }
        result = self.engine.analyze_endpoint(ep)
        assert len(result.hypotheses) >= 1

    def test_batch_parallel(self):
        endpoints = [
            {"path": "/api/users/1", "method": "GET", "params": {"id": "1"}},
            {"path": "/api/search", "method": "GET", "params": {"q": "test"}},
            {"path": "/api/proxy", "method": "POST", "params": {"url": "http://test.com"}},
        ]
        results = self.engine.analyze_batch(endpoints)
        assert len(results) == 3
