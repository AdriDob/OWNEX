"""Tests for Senior Copilot Agent — core, permissions, analysis, planning, review, audit."""

from __future__ import annotations

from typing import Any

import pytest

from core.copilot.agent import CopilotAgent
from core.copilot.analyzer import AnalysisResult, FindingAnalyzer
from core.copilot.auditor import (
    ArchitectureAuditor,
    AuditFinding,
    AuditReport,
    ConfigurationAuditor,
    HealthAuditor,
    IAuditor,
    SecurityAuditor,
)
from core.copilot.config import CopilotConfig
from core.copilot.context import CopilotContext
from core.copilot.explain import ExplanationEngine
from core.copilot.permissions import AuthorityLevel, DecisionConfidence, Policy, PolicyEngine
from core.copilot.planner import Plan, Planner, PlanStep
from core.copilot.recommender import Recommendation, Recommender
from core.copilot.review import CopilotReview, ReviewItem, ReviewReport

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_finding() -> dict[str, Any]:
    return {
        "id": "finding-001",
        "vulnerability_type": "idor",
        "severity": "high",
        "description": "IDOR in /api/users/:id allows accessing other users data",
        "cvss": 7.5,
        "cwe": "CWE-639",
        "impact": "Access to other users personal data",
        "remediation": "Implement ownership checks",
        "reproducibility": "Send GET /api/users/2 with user1 token",
        "evidence": [
            {
                "type": "request_response",
                "description": "GET /api/users/2 returned user2 data",
            },
        ],
    }


@pytest.fixture
def sample_verdict() -> dict[str, Any]:
    return {
        "status": "confirmed",
        "confidence": 0.88,
        "reasons": [{"description": "Ownership violation confirmed"}],
        "alternative_explanations": [
            {"description": "Public endpoint", "weight": 0.2},
        ],
    }


@pytest.fixture
def sample_evidence() -> list[dict[str, Any]]:
    return [
        {"type": "for", "source": "manual_test", "description": "GET returned different user data"},
    ]


@pytest.fixture
def sample_confidence_score() -> dict[str, Any]:
    return {
        "score": 0.85,
        "base_score": 0.90,
        "uncertainty_penalty": 0.05,
        "factors": [{"name": "evidence_quality", "value": 0.8}],
    }


@pytest.fixture
def agent() -> CopilotAgent:
    return CopilotAgent(config=CopilotConfig(), authority=AuthorityLevel.SENIOR_HUNTER)


# ── Tests: Authority Levels ───────────────────────────────────────────


class TestAuthorityLevel:
    def test_enum_values(self) -> None:
        assert AuthorityLevel.OBSERVER.value == "observer"
        assert AuthorityLevel.ADMINISTRATOR.value == "admin"

    def test_ordering(self) -> None:
        assert AuthorityLevel.OBSERVER < AuthorityLevel.ASSISTANT
        assert AuthorityLevel.OPERATOR > AuthorityLevel.OBSERVER
        assert AuthorityLevel.ADMINISTRATOR > AuthorityLevel.SENIOR_HUNTER
        assert AuthorityLevel.OBSERVER >= AuthorityLevel.OBSERVER

    def test_from_str_valid(self) -> None:
        assert AuthorityLevel.from_str("senior_hunter") == AuthorityLevel.SENIOR_HUNTER
        assert AuthorityLevel.from_str("SeniorHunter") == AuthorityLevel.SENIOR_HUNTER
        assert AuthorityLevel.from_str("admin") == AuthorityLevel.ADMINISTRATOR

    def test_from_str_invalid_defaults_observer(self) -> None:
        assert AuthorityLevel.from_str("god_mode") == AuthorityLevel.OBSERVER


# ── Tests: Decision Confidence ────────────────────────────────────────


class TestDecisionConfidence:
    def test_bands(self) -> None:
        assert DecisionConfidence.band(0.20) == "no_action"
        assert DecisionConfidence.band(0.50) == "request_approval"
        assert DecisionConfidence.band(0.80) == "safe_execute"
        assert DecisionConfidence.band(0.95) == "auto_close"

    def test_needs_approval_observer(self) -> None:
        assert DecisionConfidence.needs_approval(0.99, AuthorityLevel.OBSERVER)

    def test_needs_approval_operator_low_confidence(self) -> None:
        assert DecisionConfidence.needs_approval(0.50, AuthorityLevel.OPERATOR)

    def test_needs_approval_operator_high_confidence(self) -> None:
        assert not DecisionConfidence.needs_approval(0.95, AuthorityLevel.OPERATOR)

    def test_needs_approval_senior_hunter_moderate(self) -> None:
        assert not DecisionConfidence.needs_approval(DecisionConfidence.REQUEST_APPROVAL, AuthorityLevel.SENIOR_HUNTER)

    def test_needs_approval_admin_never(self) -> None:
        assert not DecisionConfidence.needs_approval(0.10, AuthorityLevel.ADMINISTRATOR)


# ── Tests: Policy Engine ──────────────────────────────────────────────


class TestPolicyEngine:
    def test_default_policies_loaded(self) -> None:
        engine = PolicyEngine()
        assert len(engine.get_policies()) == 6

    def test_add_policy(self) -> None:
        engine = PolicyEngine()
        engine.add(Policy("test_policy", "Test policy"))
        assert "test_policy" in [p["name"] for p in engine.get_policies()]

    def test_remove_policy(self) -> None:
        engine = PolicyEngine()
        assert engine.remove("nonexistent") is False
        assert engine.remove("auto_report_min_confidence") is True

    def test_check_allows_admin(self) -> None:
        engine = PolicyEngine()
        blocked = engine.check(AuthorityLevel.ADMINISTRATOR, action="delete", resource="credentials")
        assert len(blocked) == 0

    def test_check_blocks_operator(self) -> None:
        engine = PolicyEngine()
        blocked = engine.check(AuthorityLevel.OPERATOR, action="delete")
        assert len(blocked) > 0

    def test_clear(self) -> None:
        engine = PolicyEngine()
        engine.clear()
        assert len(engine.get_policies()) == 0


# ── Tests: Copilot Context ────────────────────────────────────────────


class TestCopilotContext:
    def test_empty_context(self) -> None:
        ctx = CopilotContext(app_id="cateye")
        assert ctx.app_id == "cateye"
        assert ctx.finding is None
        assert ctx.decision_band() == "no_action"
        assert ctx.needs_approval() is True

    def test_context_with_verdict(self) -> None:
        ctx = CopilotContext(app_id="cateye", authority_level=AuthorityLevel.SENIOR_HUNTER)
        ctx.set_verdict({"confidence": 0.95})
        assert ctx.decision_band() == "auto_close"
        assert ctx.needs_approval() is False

    def test_context_with_confidence_score(self) -> None:
        ctx = CopilotContext(app_id="cateye")
        ctx.set_confidence_score({"score": 0.75})
        assert ctx.decision_band() == "safe_execute"

    def test_context_to_dict(self) -> None:
        ctx = CopilotContext(app_id="atlas")
        d = ctx.to_dict()
        assert d["app_id"] == "atlas"
        assert "timestamp" in d
        assert "decision_band" in d

    def test_context_to_json(self) -> None:
        ctx = CopilotContext(app_id="cateye")
        assert isinstance(ctx.to_json(), str)
        assert "cateye" in ctx.to_json()


# ── Tests: Explanation Engine ─────────────────────────────────────────


class TestExplanationEngine:
    def test_explain_verdict(self) -> None:
        eng = ExplanationEngine()
        text = eng.explain_verdict({"status": "confirmed", "confidence": 0.88, "reasons": []})
        assert "CONFIRMED" in text
        assert "88%" in text

    def test_explain_verdict_with_alternatives(self) -> None:
        eng = ExplanationEngine()
        text = eng.explain_verdict(
            {
                "status": "confirmed",
                "confidence": 0.75,
                "reasons": [{"description": "Ownership violation"}],
                "alternative_explanations": [
                    {"description": "Public endpoint", "weight": 0.8},
                ],
            }
        )
        assert "Ownership violation" in text
        assert "Public endpoint" in text

    def test_explain_confidence(self) -> None:
        eng = ExplanationEngine()
        text = eng.explain_confidence({"score": 0.75, "base_score": 0.80, "uncertainty_penalty": 0.05})
        assert "75.0%" in text
        assert "penalización" in text

    def test_explain_action(self) -> None:
        eng = ExplanationEngine()
        text = eng.explain_action("validate", "High confidence", 0.85, "senior_hunter")
        assert "validate" in text
        assert "senior_hunter" in text

    def test_explain_changes_no_previous(self) -> None:
        eng = ExplanationEngine()
        text = eng.explain_changes({"confidence": 0.9}, None)
        assert "Sin estado previo" in text

    def test_explain_changes_detected(self) -> None:
        eng = ExplanationEngine()
        text = eng.explain_changes({"confidence": 0.9}, {"confidence": 0.7, "status": "pending"})
        assert "subió" in text or "Cambios detectados" in text

    def test_explain_alternative_discarded(self) -> None:
        eng = ExplanationEngine()
        text = eng.explain_alternative_discarded("Public endpoint", 0.3, "Ownership violation", 0.85)
        assert "Public endpoint" in text
        assert "Ownership violation" in text


# ── Tests: Planner ────────────────────────────────────────────────────


class TestPlanner:
    def test_create_plan_idor(self) -> None:
        planner = Planner()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"vulnerability_type": "idor"})
        plan = planner.create_plan(ctx)
        assert isinstance(plan, Plan)
        assert len(plan.steps) == 4
        assert any("verify_ownership" in s.action for s in plan.steps)

    def test_create_plan_ssrf(self) -> None:
        planner = Planner()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"vulnerability_type": "ssrf"})
        plan = planner.create_plan(ctx)
        assert len(plan.steps) == 3
        assert any("verify_external_interaction" in s.action for s in plan.steps)

    def test_create_plan_xss(self) -> None:
        planner = Planner()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"type": "xss"})
        plan = planner.create_plan(ctx)
        assert len(plan.steps) == 3

    def test_create_plan_generic(self) -> None:
        planner = Planner()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"type": "unknown"})
        plan = planner.create_plan(ctx)
        assert len(plan.steps) == 3

    def test_plan_to_dict(self) -> None:
        planner = Planner()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"vulnerability_type": "idor"})
        plan = planner.create_plan(ctx)
        d = plan.to_dict()
        assert d["total_steps"] == 4
        assert d["app_id"] == "cateye"
        assert "steps" in d

    def test_plan_step_risk_default(self) -> None:
        step = PlanStep(action="test", description="Test")
        assert step.risk == 0.0

    def test_plan_step_to_dict(self) -> None:
        step = PlanStep(action="http", description="Test request", tool="curl", risk=0.5)
        d = step.to_dict()
        assert d["action"] == "http"
        assert d["risk"] == 0.5
        assert "id" in d


# ── Tests: Finding Analyzer ───────────────────────────────────────────


class TestFindingAnalyzer:
    def test_analyze_no_evidence(self) -> None:
        analyzer = FindingAnalyzer()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"id": "f-001", "vulnerability_type": "idor"})
        result = analyzer.analyze(ctx)
        assert result.status in ("needs_review", "pending")
        assert result.needs_human is True
        assert any("Sin evidencia" in r for r in result.inconsistencies)

    def test_analyze_with_evidence(
        self, sample_finding: dict[str, Any], sample_verdict: dict[str, Any], sample_evidence: list[dict[str, Any]]
    ) -> None:
        analyzer = FindingAnalyzer()
        ctx = CopilotContext(app_id="cateye", authority_level=AuthorityLevel.SENIOR_HUNTER)
        ctx.set_finding(sample_finding)
        ctx.set_verdict(sample_verdict)
        ctx.set_confidence_score({"score": 0.88})
        for e in sample_evidence:
            ctx.add_evidence(e)
        result = analyzer.analyze(ctx)
        assert result.confidence == 0.88

    def test_analyze_evidence_against(self) -> None:
        analyzer = FindingAnalyzer()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"id": "f-002"})
        ctx.add_evidence({"type": "against", "description": "Not reproducible"})
        result = analyzer.analyze(ctx)
        assert any("en contra" in r for r in result.inconsistencies)

    def test_analyze_alternatives_strong(self) -> None:
        analyzer = FindingAnalyzer()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"id": "f-003"})
        ctx.set_verdict(
            {
                "confidence": 0.6,
                "alternative_explanations": [
                    {"description": "Strong alternative", "weight": 0.8},
                ],
            }
        )
        result = analyzer.analyze(ctx)
        assert any("alternativa" in r for r in result.inconsistencies)

    def test_analyze_result_to_dict(self) -> None:
        result = AnalysisResult(
            finding_id="f-001",
            status="ready",
            confidence=0.85,
            reasons=["Good evidence"],
            inconsistencies=[],
            recommendations=["Report"],
            needs_human=False,
        )
        d = result.to_dict()
        assert d["status"] == "ready"
        assert d["finding_id"] == "f-001"


# ── Tests: Recommender ────────────────────────────────────────────────


class TestRecommender:
    def test_recommend_no_finding(self) -> None:
        rec = Recommender()
        ctx = CopilotContext(app_id="cateye")
        recommendations = rec.recommend(ctx)
        assert len(recommendations) == 1
        assert recommendations[0].action == "discover_targets"

    def test_recommend_finding_no_evidence(self) -> None:
        rec = Recommender()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"id": "f-001", "vulnerability_type": "idor"})
        recommendations = rec.recommend(ctx)
        actions = [r.action for r in recommendations]
        assert "gather_evidence" in actions

    def test_recommend_idor(self) -> None:
        rec = Recommender()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"id": "f-001", "vulnerability_type": "idor"})
        ctx.set_verdict({"confidence": 0.9})
        recommendations = rec.recommend(ctx)
        actions = [r.action for r in recommendations]
        assert "verify_ownership" in actions

    def test_recommend_high_confidence(self) -> None:
        rec = Recommender()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"id": "f-001", "vulnerability_type": "xss"})
        ctx.set_confidence_score({"score": 0.90})
        recommendations = rec.recommend(ctx)
        actions = [r.action for r in recommendations]
        assert "consider_report" in actions

    def test_recommend_low_confidence(self) -> None:
        rec = Recommender()
        ctx = CopilotContext(app_id="cateye")
        ctx.set_finding({"id": "f-001"})
        ctx.set_confidence_score({"score": 0.30})
        recommendations = rec.recommend(ctx)
        actions = [r.action for r in recommendations]
        assert "human_review" in actions

    def test_recommendation_to_dict(self) -> None:
        r = Recommendation("test", "Test", priority=5, reason="Testing", risk=0.5)
        d = r.to_dict()
        assert d["action"] == "test"
        assert d["priority"] == 5
        assert d["risk"] == 0.5


# ── Tests: Copilot Review ─────────────────────────────────────────────


class TestCopilotReview:
    def test_review_passes_good_finding(self, sample_finding: dict[str, Any], sample_verdict: dict[str, Any]) -> None:
        reviewer = CopilotReview()
        report = reviewer.review(sample_finding, sample_verdict)
        assert isinstance(report, ReviewReport)
        assert report.passed

    def test_review_fails_no_evidence(self) -> None:
        reviewer = CopilotReview()
        report = reviewer.review({"id": "f-001", "description": "Finding"})
        assert not report.passed

    def test_review_reports_failed_items(self) -> None:
        reviewer = CopilotReview()
        report = reviewer.review({"id": "f-001", "description": "Short"})
        assert len(report.failed_items) > 0

    def test_review_to_dict(self, sample_finding: dict[str, Any]) -> None:
        reviewer = CopilotReview()
        report = reviewer.review(sample_finding)
        d = report.to_dict()
        assert "finding_id" in d
        assert "passed" in d
        assert "items" in d

    def test_review_item_lifecycle(self) -> None:
        item = ReviewItem("test", "Test item")
        assert item.status == "pending"
        item.pass_("All good")
        assert item.status == "passed"
        item.fail("Something wrong")
        assert item.status == "failed"
        item.skip("Not applicable")
        assert item.status == "skipped"

    def test_review_highlights_strong_alternatives(self) -> None:
        reviewer = CopilotReview()
        finding = {
            "id": "f-001",
            "description": "Test finding with evidence and all fields complete",
            "evidence": [{"type": "request_response"}],
            "reproducibility": "Easy",
            "cvss": 7.5,
            "cwe": "CWE-79",
            "impact": "High",
            "remediation": "Fix it",
        }
        verdict = {
            "confidence": 0.85,
            "alternative_explanations": [
                {"description": "Strong alt", "weight": 0.7},
            ],
        }
        report = reviewer.review(finding, verdict)
        # Should fail because of strong alternative
        assert len(report.failed_items) > 0


# ── Tests: Auditors ───────────────────────────────────────────────────


class TestAuditors:
    def test_health_auditor_green(self) -> None:
        auditor = HealthAuditor()
        report = auditor.audit({"health": {"status": "green", "checks": []}})
        assert len(report.findings) == 1
        assert report.findings[0].severity == "info"

    def test_health_auditor_red(self) -> None:
        auditor = HealthAuditor()
        report = auditor.audit({"health": {"status": "red", "checks": []}})
        assert any(f.severity == "critical" for f in report.findings)

    def test_health_auditor_failed_checks(self) -> None:
        auditor = HealthAuditor()
        report = auditor.audit(
            {
                "health": {
                    "status": "yellow",
                    "checks": [{"name": "database", "status": "error", "message": "Connection failed"}],
                },
            }
        )
        assert any(f.category == "health" for f in report.findings)

    def test_configuration_auditor_missing_keys(self) -> None:
        auditor = ConfigurationAuditor()
        report = auditor.audit({"config": {}, "env": {}})
        assert len(report.findings) >= 1

    def test_security_auditor_unverified_findings(self) -> None:
        auditor = SecurityAuditor()
        findings_list = [{"status": "pending"} for _ in range(15)]
        report = auditor.audit({"findings": {"items": findings_list}, "auth": {"csrf_enabled": True}})
        assert any(f.severity == "medium" for f in report.findings)

    def test_security_auditor_csrf_disabled(self) -> None:
        auditor = SecurityAuditor()
        report = auditor.audit({"findings": {"items": []}, "auth": {"csrf_enabled": False}})
        assert any(f.severity == "high" for f in report.findings)

    def test_architecture_auditor_disconnected(self) -> None:
        auditor = ArchitectureAuditor()
        report = auditor.audit(
            {
                "modules": {"cateye": {"status": "disconnected"}},
            }
        )
        assert len(report.findings) == 1

    def test_audit_report_severity_counts(self) -> None:
        report = AuditReport("test")
        report.add(AuditFinding("critical", "test", "Critical issue", "Desc"))
        report.add(AuditFinding("high", "test", "High issue", "Desc"))
        report.add(AuditFinding("info", "test", "Info", "Desc"))
        assert report.severity_count("critical") == 1
        assert report.severity_count("high") == 1
        assert report.severity_count("info") == 1
        assert report.severity_count("medium") == 0

    def test_audit_finding_to_dict(self) -> None:
        f = AuditFinding("high", "security", "Test", "Description", "Fix it")
        d = f.to_dict()
        assert d["severity"] == "high"
        assert d["recommendation"] == "Fix it"


# ── Tests: Copilot Agent (integration) ────────────────────────────────


class TestCopilotAgent:
    def test_agent_initialization(self) -> None:
        agent = CopilotAgent()
        assert agent.app_id == "copilot"
        assert agent.agent_id.startswith("copilot-")
        assert agent.authority == AuthorityLevel.OBSERVER

    def test_agent_custom_authority(self) -> None:
        agent = CopilotAgent(authority=AuthorityLevel.SENIOR_HUNTER)
        assert agent.authority == AuthorityLevel.SENIOR_HUNTER

    def test_authority_change(self) -> None:
        agent = CopilotAgent()
        agent.authority = "senior_hunter"
        assert agent.authority == AuthorityLevel.SENIOR_HUNTER

    def test_analyze_finding(self, agent: CopilotAgent, sample_finding: dict[str, Any]) -> None:
        import asyncio

        result = asyncio.run(agent.analyze_finding(sample_finding))
        assert isinstance(result, AnalysisResult)
        assert result.finding_id == "finding-001"

    def test_analyze_finding_with_verdict(
        self,
        agent: CopilotAgent,
        sample_finding: dict[str, Any],
        sample_verdict: dict[str, Any],
        sample_evidence: list[dict[str, Any]],
        sample_confidence_score: dict[str, Any],
    ) -> None:
        import asyncio

        result = asyncio.run(
            agent.analyze_finding(
                sample_finding,
                sample_verdict,
                sample_evidence,
                sample_confidence_score,
            )
        )
        assert result.confidence == 0.85

    def test_create_plan(self, agent: CopilotAgent, sample_finding: dict[str, Any]) -> None:
        plan = agent.create_plan(sample_finding)
        assert isinstance(plan, Plan)
        assert len(plan.steps) > 0

    def test_recommend(self, agent: CopilotAgent, sample_finding: dict[str, Any]) -> None:
        ctx = CopilotContext(app_id="cateye", authority_level=AuthorityLevel.SENIOR_HUNTER)
        ctx.set_finding(sample_finding)
        ctx.set_verdict({"confidence": 0.9})
        recs = agent.recommend_next(ctx)
        assert len(recs) > 0
        assert isinstance(recs[0], Recommendation)

    def test_explain_decision(self, agent: CopilotAgent) -> None:
        # First log a decision
        agent._log_decision("test_action", {"key": "value"})
        journal = agent.get_decision_journal()
        assert len(journal) >= 1
        decision_id = journal[-1]["decision_id"]
        explanation = agent.explain(decision_id)
        assert explanation is not None
        assert "test_action" in explanation

    def test_explain_nonexistent_decision(self, agent: CopilotAgent) -> None:
        assert agent.explain("nonexistent") is None

    def test_pre_report_review(self, agent: CopilotAgent, sample_finding: dict[str, Any]) -> None:
        from core.reports.acceptance.learner import AcceptanceLearner

        AcceptanceLearner().reset()
        review = agent.pre_report_review(sample_finding)
        assert isinstance(review, ReviewReport)
        assert review.passed

    def test_audit_system(self, agent: CopilotAgent) -> None:
        state = {
            "health": {"status": "green", "checks": []},
            "config": {"authority_level": "senior_hunter", "min_confidence_auto": 0.7},
            "env": {"COPILOT_AUTHORITY": "senior_hunter"},
            "findings": {"items": []},
            "auth": {"csrf_enabled": True},
            "modules": {},
        }
        report = agent.audit_system(state)
        assert report.auditor_name == "copilot_full_audit"
        assert isinstance(report.findings, list)

    def test_check_permission(self, agent: CopilotAgent) -> None:
        blocked = agent.check_permission(action="delete")
        # Senior hunter should be blocked by never_delete_data
        assert len(blocked) > 0

    def test_check_permission_admin(self) -> None:
        agent = CopilotAgent(authority=AuthorityLevel.ADMINISTRATOR)
        blocked = agent.check_permission(action="delete")
        # Admin should not be blocked by most policies
        assert len(blocked) == 0

    def test_needs_approval(self, agent: CopilotAgent) -> None:
        assert agent.needs_approval(0.50) is True
        assert agent.needs_approval(0.85) is False

    def test_get_decision_journal(self, agent: CopilotAgent) -> None:
        agent._log_decision("a1", {})
        agent._log_decision("a2", {})
        entries = agent.get_decision_journal(limit=1)
        assert len(entries) == 1
        assert entries[0]["action"] == "a2"

    def test_get_decision_journal_filtered(self, agent: CopilotAgent) -> None:
        agent._log_decision("analyze_finding", {})
        agent._log_decision("audit_system", {})
        entries = agent.get_decision_journal(action="audit_system")
        assert all(e["action"] == "audit_system" for e in entries)

    def test_register_auditor(self, agent: CopilotAgent) -> None:
        class TestAuditor(IAuditor):
            name = "test"

            def audit(self, system_state):  # type: ignore
                return AuditReport("test")

        agent.register_auditor(TestAuditor())
        assert any(a.name == "test" for a in agent._auditors)

    def test_to_dict(self, agent: CopilotAgent) -> None:
        d = agent.to_dict()
        assert d["app_id"] == "copilot"
        assert "authority" in d
        assert "config" in d
        assert "policies" in d
        assert "decision_count" in d

    def test_agent_not_connected_to_apps_directly(self) -> None:
        """Verify Copilot does not import apps directly."""
        import inspect

        import core.copilot.agent as agent_module

        source = inspect.getsource(agent_module)
        # Should not import cateye, atlas, odyssey directly
        assert "import cores" not in source
        assert "from apps" not in source
