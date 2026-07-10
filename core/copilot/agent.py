"""Senior Copilot Agent — the transversal reasoning and quality center of ORION."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from core.copilot.analyzer import AnalysisResult, FindingAnalyzer
from core.copilot.auditor import AuditReport, IAuditor, get_all_auditors
from core.copilot.config import CopilotConfig
from core.copilot.context import CopilotContext
from core.copilot.explain import ExplanationEngine
from core.copilot.permissions import AuthorityLevel, DecisionConfidence, PolicyEngine
from core.copilot.planner import Plan, Planner
from core.copilot.recommender import Recommendation, Recommender
from core.copilot.review import CopilotReview, ReviewReport
from core.evidence_graph.graph import get_evidence_graph
from core.memory.store import get_memory_store

logger = logging.getLogger("orion.core.copilot.agent")


class CopilotAgent:
    """Senior Copilot Agent — transversal reasoning and quality center.

    The Copilot does not access apps directly. It consumes Core Services
    (EventBus, Decision Journal, Memory, System State) through their
    public interfaces.
    """

    def __init__(
        self,
        app_id: str = "copilot",
        config: CopilotConfig | None = None,
        authority: AuthorityLevel | None = None,
    ) -> None:
        self.app_id = app_id
        self.agent_id = f"copilot-{uuid.uuid4().hex[:8]}"
        self.config = config or CopilotConfig()
        self._authority = authority or self.config.authority_level

        # Sub-modules
        self.explainer = ExplanationEngine()
        self.analyzer = FindingAnalyzer(self.explainer)
        self.planner = Planner()
        self.recommender = Recommender()
        self.reviewer = CopilotReview()
        self.policies = PolicyEngine()
        self._auditors: list[IAuditor] = get_all_auditors()

        self._decision_journal: list[dict[str, Any]] = []
        self._context: CopilotContext | None = None
        self._evidence_graph = get_evidence_graph()
        self._memory = get_memory_store()

        logger.info("CopilotAgent initialized: %s (authority=%s)", self.agent_id, self._authority.value)

    # ── Authority ──────────────────────────────────────────────

    @property
    def authority(self) -> AuthorityLevel:
        return self._authority

    @authority.setter
    def authority(self, level: AuthorityLevel | str) -> None:
        if isinstance(level, str):
            level = AuthorityLevel.from_str(level)
        old = self._authority
        self._authority = level
        logger.info("Authority changed: %s → %s", old.value, level.value)

    def get_authority_levels(self) -> list[str]:
        return [level.value for level in AuthorityLevel]

    # ── Core: Analyze ──────────────────────────────────────────

    async def analyze_finding(
        self,
        finding: dict[str, Any],
        verdict: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        confidence_score: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        """Analyze a finding with full context, querying the Evidence Graph."""
        context = self._build_context("cateye")
        finding_id = finding.get("id", "unknown")
        context.set_finding(finding)
        if evidence:
            for e in evidence:
                context.add_evidence(e)

        # Query Evidence Graph for existing evidence
        graph_evidence = self._evidence_graph.get_evidence(finding_id)
        for ev in graph_evidence.get("for", []):
            context.add_evidence(ev)
        for ev in graph_evidence.get("against", []):
            context.add_evidence({**ev, "type": "against"})
        balance = self._evidence_graph.get_balance(finding_id)
        context.set_system_state({"evidence_balance": balance})

        if verdict:
            context.set_verdict(verdict)
        if confidence_score:
            context.set_confidence_score(confidence_score)

        self._context = context
        result = self.analyzer.analyze(context)
        self._log_decision("analyze_finding", result.to_dict())

        # Record analysis back into Evidence Graph
        self._evidence_graph.record_from_copilot(finding_id, result.to_dict())

        # Store in Unified Memory for future reference
        self.remember_analysis(finding_id, result.to_dict())

        return result

    # ── Core: Plan ─────────────────────────────────────────────

    def create_plan(self, finding: dict[str, Any] | None = None) -> Plan:
        """Create an investigation plan."""
        context = self._build_context("cateye")
        if finding:
            context.set_finding(finding)
        plan = self.planner.create_plan(context)
        self._log_decision("create_plan", plan.to_dict())
        return plan

    # ── Core: Recommend ────────────────────────────────────────

    def recommend_next(self, context: CopilotContext | None = None) -> list[Recommendation]:
        """Get next-step recommendations."""
        ctx = context or self._context or self._build_context("cateye")
        recs = self.recommender.recommend(ctx)
        self._log_decision("recommend", {"recommendations": [r.to_dict() for r in recs]})
        return recs

    # ── Core: Explain ──────────────────────────────────────────

    def explain(self, decision_id: str) -> str | None:
        """Retrieve explanation for a previous decision."""
        entry = self._find_decision(decision_id)
        if entry is None:
            return None
        return self.explainer.explain_action(
            action=entry.get("action", "unknown"),
            reason=entry.get("reason", ""),
            confidence=entry.get("confidence", 0.0),
            authority=entry.get("authority", "observer"),
        )

    def explain_verdict(self, verdict: dict[str, Any]) -> str:
        return self.explainer.explain_verdict(verdict)

    def explain_confidence(self, score: dict[str, Any], evidence_count: int = 0) -> str:
        return self.explainer.explain_confidence(score, evidence_count)

    # ── Core: Review ───────────────────────────────────────────

    def pre_report_review(
        self,
        finding: dict[str, Any],
        verdict: dict[str, Any] | None = None,
    ) -> ReviewReport:
        """Run the pre-report quality checklist."""
        review = self.reviewer.review(finding, verdict)
        self._log_decision("pre_report_review", review.to_dict())
        return review

    # ── Core: Audit ────────────────────────────────────────────

    def audit_system(self, system_state: dict[str, Any]) -> AuditReport:
        """Run all registered auditors."""
        combined = AuditReport("copilot_full_audit")
        for auditor in self._auditors:
            try:
                report = auditor.audit(system_state)
                combined.findings.extend(report.findings)
                logger.debug("Auditor %s: %d findings", auditor.name, len(report.findings))
            except Exception as exc:
                logger.error("Auditor %s failed: %s", auditor.name, exc)
        self._log_decision("audit_system", combined.to_dict())
        return combined

    def register_auditor(self, auditor: IAuditor) -> None:
        self._auditors.append(auditor)
        logger.info("Auditor registered: %s", auditor.name)

    # ── Core: Check permissions ────────────────────────────────

    def check_permission(self, action: str = "", **context: Any) -> list[str]:
        """Check if the current authority allows an action.

        Returns list of blocking policy names (empty = allowed).
        """
        return self.policies.check(self._authority, action, **context)

    def needs_approval(self, confidence: float) -> bool:
        return DecisionConfidence.needs_approval(confidence, self._authority)

    # ── Evidence Graph ─────────────────────────────────────────

    def evidence_balance(self, hypothesis_id: str) -> dict:
        """Get the evidence balance for a hypothesis from the Evidence Graph."""
        return self._evidence_graph.get_balance(hypothesis_id)

    def evidence_for(self, hypothesis_id: str) -> list[dict]:
        return self._evidence_graph.get_evidence_for(hypothesis_id)

    def evidence_against(self, hypothesis_id: str) -> list[dict]:
        return self._evidence_graph.get_evidence_against(hypothesis_id)

    # ── Unified Memory ────────────────────────────────────────

    def remember(
        self, namespace: str, key: str, content: str, tags: list[str] | None = None, priority: float = 0.0
    ) -> int:
        """Store an analysis result in Unified Memory."""
        return self._memory.store(
            namespace=namespace,
            key=key,
            content=content,
            metadata={"agent_id": self.agent_id, "authority": self._authority.value},
            tags=tags,
            priority=priority,
        )

    def recall(self, namespace: str, search: str = "", tags: list[str] | None = None, limit: int = 10) -> list[dict]:
        """Query Unified Memory for relevant past entries."""
        return self._memory.query(
            namespace=namespace,
            search=search,
            tags=tags,
            limit=limit,
        )

    def remember_analysis(self, finding_id: str, analysis: dict[str, Any]) -> int:
        """Store a complete analysis result in memory for future reference."""
        return self._memory.store(
            namespace="copilot",
            key=f"analysis:{finding_id}",
            content=analysis.get("status", "unknown"),
            tags=["analysis", analysis.get("status", "unknown")],
            priority=max(analysis.get("confidence", 0.0) * 10, 0.1),
            metadata={
                "finding_id": finding_id,
                "inconsistencies": analysis.get("inconsistencies", []),
                "recommendations": analysis.get("recommendations", []),
                "agent_id": self.agent_id,
            },
        )

    # ── Internal ───────────────────────────────────────────────

    def _build_context(self, app_id: str) -> CopilotContext:
        return CopilotContext(
            app_id=app_id,
            authority_level=self._authority,
            config=self.config,
        )

    def _log_decision(self, action: str, data: dict[str, Any]) -> str:
        decision_id = f"{self.agent_id}-{uuid.uuid4().hex[:12]}"
        entry = {
            "decision_id": decision_id,
            "agent_id": self.agent_id,
            "action": action,
            "reason": f"Copilot {action} at {datetime.now(timezone.utc).isoformat()}",
            "data": data,
            "confidence": 0.0,
            "authority": self._authority.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._decision_journal.append(entry)
        if len(self._decision_journal) > self.config.max_decisions_logged:
            self._decision_journal.pop(0)
        logger.debug("Decision logged: %s — %s", decision_id, action)
        return decision_id

    def _find_decision(self, decision_id: str) -> dict[str, Any] | None:
        for entry in reversed(self._decision_journal):
            if entry.get("decision_id") == decision_id:
                return entry
        return None

    def get_decision_journal(
        self,
        limit: int = 100,
        action: str | None = None,
    ) -> list[dict[str, Any]]:
        entries = self._decision_journal[-limit:]
        if action:
            entries = [e for e in entries if e.get("action") == action]
        return entries

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "app_id": self.app_id,
            "authority": self._authority.value,
            "config": self.config.to_dict(),
            "policies": self.policies.get_policies(),
            "decision_count": len(self._decision_journal),
        }
