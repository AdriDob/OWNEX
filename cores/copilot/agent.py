"""Senior Copilot Agent — the transversal reasoning and quality center of ORION."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from core.capabilities.registry import get_capability_registry
from core.copilot.analyzer import AnalysisResult, FindingAnalyzer
from core.copilot.auditor import AuditReport, IAuditor, get_all_auditors
from core.copilot.config import CopilotConfig
from core.copilot.context import CopilotContext
from core.copilot.executor import ExecutionReport, PlanExecutor
from core.copilot.explain import ExplanationEngine
from core.copilot.permissions import AuthorityLevel, DecisionConfidence, PolicyEngine
from core.copilot.planner import Plan, Planner
from core.copilot.publisher import publish_copilot_event
from core.copilot.recommender import Recommendation, Recommender
from core.copilot.review import CopilotReview, ReviewItem, ReviewReport
from core.copilot.system_context import SystemContextBuilder
from core.evidence_graph.graph import get_evidence_graph
from core.memory.store import get_memory_store
from cores.events.correlation import get_or_create_correlation_id
from cores.events.types import Decision, Events
from cores.knowledge_core import get_knowledge_graph

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

        # Sub-modules (order matters: _memory before executor)
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
        self._knowledge = get_knowledge_graph()
        self._memory = get_memory_store()
        self.executor = PlanExecutor(memory=self._memory)

        self._event_count = 0

        # Register COPILOT's own capabilities
        self._register_capabilities()

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

        # Record finding in Knowledge Graph
        try:
            target = finding.get("target", {})
            target_id = target.get("id") if isinstance(target, dict) else None
            self._knowledge.record_finding(
                target_id=target_id or "orphan",
                finding_id=finding_id,
                finding_name=finding.get("name") or finding.get("vulnerability_type", "unknown"),
                severity=finding.get("severity", "medium"),
            )
        except Exception as exc:
            logger.debug("Failed to record finding in Knowledge Graph: %s", exc)

        # Store in Unified Memory for future reference
        self.remember_analysis(finding_id, result.to_dict())

        publish_copilot_event(
            Events.COPILOT_ANALYSIS_COMPLETED,
            {
                "finding_id": finding_id,
                "status": result.status,
                "confidence": result.confidence,
                "needs_human": result.needs_human,
                "inconsistencies": result.inconsistencies or [],
                "recommendations": result.recommendations or [],
            },
        )

        return result

    # ── Core: Plan ─────────────────────────────────────────────

    def create_plan(self, finding: dict[str, Any] | None = None) -> Plan:
        """Create an investigation plan."""
        context = self._build_context("cateye")
        if finding:
            context.set_finding(finding)
        plan = self.planner.create_plan(context)
        self._log_decision("create_plan", plan.to_dict())

        vuln_type = (finding.get("vulnerability_type") or finding.get("type") or "generic") if finding else "generic"
        publish_copilot_event(
            Events.COPILOT_PLAN_CREATED,
            {
                "plan_id": plan.id,
                "finding_id": finding.get("id") if finding else "",
                "vuln_type": vuln_type,
                "steps": len(plan.steps),
            },
        )

        return plan

    # ── Core: Execute Plan ─────────────────────────────────────

    def execute_plan(self, plan: Plan) -> ExecutionReport:
        """Execute all steps of a plan and return results."""
        report = self.executor.execute(plan)
        self._log_decision(
            "execute_plan",
            {
                "plan_id": plan.id,
                "status": report.status,
                "success_rate": report.success_rate,
                "steps_completed": len(report.step_results),
            },
        )

        publish_copilot_event(
            Events.COPILOT_PLAN_EXECUTED,
            {
                "plan_id": plan.id,
                "status": report.status,
                "success_rate": report.success_rate,
                "steps_completed": len(report.step_results),
            },
        )

        return report

    # ── Core: Recommend ────────────────────────────────────────

    def recommend_next(self, context: CopilotContext | None = None) -> list[Recommendation]:
        """Get next-step recommendations."""
        ctx = context or self._context or self._build_context("cateye")
        recs = self.recommender.recommend(ctx)
        self._log_decision("recommend", {"recommendations": [r.to_dict() for r in recs]})
        return recs

    # ── Core: System-wide Recommendation ───────────────────────

    def recommend_for_system(
        self,
        db_factory: Any | None = None,
        extra_state: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get top actions based on full system state (targets, findings, scheduler)."""
        builder = SystemContextBuilder(db_factory)
        ctx = builder.build(authority=self._authority, extra=extra_state)
        actions = builder.top_actions(ctx)
        self._log_decision("recommend_for_system", {"actions": actions})
        return actions

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

        # Record report in Knowledge Graph
        try:
            finding_id = finding.get("id", "unknown")
            report_id = f"report_{finding_id}"
            self._knowledge.record_report(
                finding_id=finding_id,
                report_id=report_id,
                report_name=f"Report for {finding.get('vulnerability_type', 'finding')}",
            )
        except Exception as exc:
            logger.debug("Failed to record report in Knowledge Graph: %s", exc)

        # Add acceptance probability prediction
        try:
            from core.reports.acceptance.learner import AcceptanceLearner

            platform = finding.get("platform", "hackerone")
            score = finding.get("quality_score", 0.0) or 0.0
            dimensions = finding.get("quality_dimensions", {}) or {}
            evidence_count = finding.get("evidence_count", 0) or 0

            learner = AcceptanceLearner()
            prediction = learner.predict(platform, score, dimensions, evidence_count)

            acc_item = ReviewItem(
                "acceptance_probability",
                f"Probabilidad de aceptación en {platform}: {prediction.probability}% "
                f"(confianza: {prediction.confidence})",
            )
            if prediction.confidence in ("low", "medium") or prediction.probability >= 60:
                acc_item.pass_(f"Aceptación estimada: {prediction.probability}% ({prediction.confidence} confianza)")
            else:
                notes = f"Solo {prediction.probability}% de probabilidad"
                if prediction.recommendations:
                    notes += ". " + "; ".join(prediction.recommendations[:3])
                acc_item.fail(notes)
            review.add_item(acc_item)

            # Publish acceptance prediction event
            publish_copilot_event(
                Events.COPILOT_ANALYSIS_COMPLETED,
                {
                    "finding_id": finding.get("id", "unknown"),
                    "acceptance_probability": prediction.probability,
                    "acceptance_confidence": prediction.confidence,
                    "weak_dimensions": prediction.weak_dimensions[:3],
                },
            )
        except Exception as exc:
            logger.debug("Acceptance prediction unavailable: %s", exc)

        rd = review.to_dict()
        publish_copilot_event(
            Events.COPILOT_REVIEW_COMPLETED,
            {
                "finding_id": finding.get("id", "unknown"),
                "passed": rd.get("passed_count", 0),
                "total": rd.get("total_items", 0),
                "recommendation": "passed" if rd.get("passed", False) else "needs_revision",
            },
        )

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

        status_by_auditor = {a.name: "ok" for a in self._auditors}
        publish_copilot_event(
            Events.COPILOT_AUDIT_COMPLETED,
            {
                "findings_count": len(combined.findings),
                "status_by_auditor": status_by_auditor,
            },
        )

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

    # ── Decision Engine ─────────────────────────────────────────

    def make_decision(
        self,
        event_type: str,
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Decision:
        """Produce a standardized Decision from an event.

        Queries the Knowledge Graph for related entities to enrich
        reasoning, and records every decision back into the KG.
        """
        cid = correlation_id or get_or_create_correlation_id()
        ctx = context or {}

        # Enrich context with Knowledge Graph data
        kg_context = self._knowledge_context(event_type, ctx)
        if kg_context:
            ctx.setdefault("_kg_context", kg_context)

        # Determine priority from event type
        priority = self._decision_priority(event_type)

        # Build reason from context
        reason = self._decision_reason(event_type, ctx)

        # Confidence depends on how much context we have
        confidence = self._decision_confidence(event_type, ctx)

        # Recommended actions
        actions = self._decision_actions(event_type, ctx)

        decision = Decision(
            event_type=event_type,
            correlation_id=cid,
            priority=priority,
            reason=reason,
            confidence=confidence,
            actions=actions,
            eta=self._estimate_eta(actions),
            roi=self._estimate_roi(event_type, ctx),
            human_required=confidence < 0.5,
            source="copilot",
        )

        # Record decision in Knowledge Graph
        try:
            kg_context_for_record = kg_context or {}
            decision_data = {
                "decision_id": f"{cid}_{event_type.replace(':', '_')}",
                "event_type": event_type,
                "priority": priority,
                "reason": reason,
                "confidence": confidence,
                "actions": actions,
                "related_nodes": kg_context_for_record.get("related_node_ids", []),
            }
            self._knowledge.record_decision(decision_data)
        except Exception as exc:
            logger.warning("Failed to record decision in Knowledge Graph: %s", exc)

        publish_copilot_event(
            Events.COPILOT_DECISION,
            decision.to_envelope().payload,
            correlation_id=cid,
            duration_ms=decision.duration_ms,
            user=decision.user,
        )

        # Log decision internally
        self._log_decision("make_decision", decision.to_dict())

        return decision

    @staticmethod
    def _decision_priority(event_type: str) -> str:
        critical = {
            Events.SYSTEM_ERROR,
            Events.SYSTEM_DEGRADED,
            Events.SYSTEM_ALERT,
            Events.RECOVERY_FAILED,
            Events.ANOMALY_DETECTED,
        }
        high = {
            Events.FINDING_CONFIRMED,
            Events.FINDING_STATUS_CHANGED,
            Events.PAYOUT_RECEIVED,
            Events.REPORT_ACCEPTED,
            Events.REPORT_REJECTED,
            Events.QUICK_WIN_DETECTED,
        }
        medium = {
            Events.FINDING_CREATED,
            Events.REPORT_GENERATED,
            Events.OPPORTUNITY_FOUND,
            Events.OPPORTUNITY_UPDATED,
            Events.TARGET_CREATED,
            Events.HEALTH_SCORE_UPDATED,
        }
        if event_type in critical:
            return "critical"
        if event_type in high:
            return "high"
        if event_type in medium:
            return "medium"
        return "low"

    @staticmethod
    def _decision_reason(event_type: str, ctx: dict[str, Any]) -> str:
        reasons = {
            Events.FINDING_CONFIRMED: "Finding confirmed — ready for reporting pipeline",
            Events.FINDING_CREATED: "New finding detected — analysis required",
            Events.FINDING_STATUS_CHANGED: f"Finding status changed to {ctx.get('new_status', 'unknown')}",
            Events.SYSTEM_ERROR: f"System error: {ctx.get('error', 'unknown')}",
            Events.SYSTEM_DEGRADED: f"System degraded: {ctx.get('reason', 'unknown')}",
            Events.SYSTEM_ALERT: f"Alert: {ctx.get('message', 'unknown')}",
            Events.REPORT_GENERATED: "Report ready for review",
            Events.REPORT_ACCEPTED: "Report accepted — payment expected",
            Events.PAYOUT_RECEIVED: f"Payout received: {ctx.get('amount', 'unknown')}",
            Events.OPPORTUNITY_FOUND: "New opportunity detected — evaluate priority",
            Events.QUICK_WIN_DETECTED: "Quick win opportunity — high value, low effort",
            Events.HEALTH_SCORE_UPDATED: f"Health score: {ctx.get('score', 'unknown')}",
            Events.RECOVERY_FAILED: "Recovery failed — manual intervention required",
            Events.RECOVERY_SUCCESS: "Recovery completed successfully",
            Events.TARGET_CREATED: f"New target: {ctx.get('target_name', 'unknown')}",
            Events.AUTO_OPTIMIZATION_APPLIED: "Auto-optimization applied",
        }
        return reasons.get(event_type, f"Event {event_type} received — evaluating")

    @staticmethod
    def _decision_confidence(event_type: str, ctx: dict[str, Any]) -> float:
        if event_type in {Events.SYSTEM_ERROR, Events.SYSTEM_DEGRADED}:
            prio = 0.85
        elif event_type in {Events.FINDING_CONFIRMED, Events.FINDING_STATUS_CHANGED}:
            prio = 0.70
        elif event_type in {Events.PAYOUT_RECEIVED, Events.REPORT_ACCEPTED, Events.REPORT_REJECTED}:
            prio = 0.80
        else:
            prio = 0.50
        # Adjust based on how much context we have
        score = ctx.get("confidence_score")
        if score is not None:
            prio = (prio + float(score)) / 2
        return min(prio, 0.95)

    @staticmethod
    def _decision_actions(event_type: str, ctx: dict[str, Any]) -> list[dict[str, Any]]:
        actions_map = {
            Events.FINDING_CONFIRMED: [{"action": "generate_report", "target": ctx.get("finding_id")}],
            Events.FINDING_CREATED: [{"action": "analyze", "target": ctx.get("finding_id")}],
            Events.SYSTEM_ERROR: [{"action": "diagnose", "target": "system"}],
            Events.SYSTEM_DEGRADED: [{"action": "investigate_degradation", "target": ctx.get("component", "unknown")}],
            Events.SYSTEM_ALERT: [{"action": "respond_to_alert", "target": ctx.get("alert_type", "unknown")}],
            Events.REPORT_GENERATED: [{"action": "review_report", "target": ctx.get("report_id")}],
            Events.REPORT_ACCEPTED: [{"action": "log_payment", "target": ctx.get("report_id")}],
            Events.PAYOUT_RECEIVED: [{"action": "update_financials", "target": "portfolio"}],
            Events.OPPORTUNITY_FOUND: [{"action": "evaluate_opportunity", "target": ctx.get("opportunity_id")}],
            Events.RECOVERY_FAILED: [{"action": "manual_intervention", "target": "system", "urgent": True}],
        }
        return actions_map.get(event_type, [{"action": "assess", "target": "unknown"}])

    @staticmethod
    def _estimate_eta(actions: list[dict[str, Any]]) -> str:
        eta_map = {
            "generate_report": "30m",
            "analyze": "15m",
            "diagnose": "10m",
            "investigate_degradation": "20m",
            "respond_to_alert": "5m",
            "review_report": "20m",
            "log_payment": "5m",
            "update_financials": "10m",
            "evaluate_opportunity": "15m",
            "manual_intervention": "1h",
            "assess": "10m",
        }
        if not actions:
            return "10m"
        action = actions[0].get("action", "assess")
        return eta_map.get(action, "15m")

    @staticmethod
    def _estimate_roi(event_type: str, ctx: dict[str, Any]) -> str:
        roi_map = {
            Events.FINDING_CONFIRMED: "potential_payout",
            Events.PAYOUT_RECEIVED: "confirmed_income",
            Events.REPORT_ACCEPTED: "confirmed_income",
            Events.QUICK_WIN_DETECTED: "high_effort_ratio",
            Events.OPPORTUNITY_FOUND: "potential_future_income",
        }
        return roi_map.get(event_type, "indirect")

    # ── Knowledge Graph Integration ─────────────────────────────

    def _knowledge_context(self, event_type: str, ctx: dict[str, Any]) -> dict[str, Any] | None:
        """Query the Knowledge Graph for context relevant to this event.

        Returns related nodes, graph stats, and connections that help
        COPILOT make a more informed decision.
        """
        try:
            result: dict[str, Any] = {"related_node_ids": [], "node_count": 0}
            finding_id = ctx.get("finding_id") or ctx.get("id")
            target_id = ctx.get("target_id") or ctx.get("target")
            report_id = ctx.get("report_id")

            if finding_id:
                finding_node = self._knowledge.get_node(finding_id)
                if finding_node:
                    result["finding"] = self._knowledge._node_to_dict(finding_node)
                    result["related_node_ids"].append(finding_id)
                    neighbors = self._knowledge.get_neighbors(finding_id, max_depth=1)
                    result["finding_neighbors"] = neighbors
                    for n in neighbors:
                        nid = n.get("node", {}).get("id")
                        if nid:
                            result["related_node_ids"].append(nid)

            if target_id and target_id != finding_id:
                target_node = self._knowledge.get_node(target_id)
                if target_node:
                    result["target"] = self._knowledge._node_to_dict(target_node)
                    result["related_node_ids"].append(target_id)

            if report_id:
                report_node = self._knowledge.get_node(report_id)
                if report_node:
                    result["report"] = self._knowledge._node_to_dict(report_node)
                    result["related_node_ids"].append(report_id)

            stats = self._knowledge.get_stats()
            result["graph_stats"] = {
                "total_nodes": stats["total_nodes"],
                "total_edges": stats["total_edges"],
            }
            result["node_count"] = len(result["related_node_ids"])
            return result
        except Exception as exc:
            logger.debug("Knowledge Graph query failed: %s", exc)
            return None

    # ── Event Listener ───────────────────────────────────────────

    def on_event(self, event_type: str, correlation_id: str | None = None, **data: Any) -> Decision | None:
        """Receive a system event, decide if COPILOT should act.

        Called by the EventBus subscriber when important events occur.
        For high-priority events, produces a Decision.
        """
        self._event_count += 1

        important_events = {
            Events.FINDING_CONFIRMED,
            Events.FINDING_CREATED,
            Events.FINDING_STATUS_CHANGED,
            Events.SYSTEM_ERROR,
            Events.SYSTEM_DEGRADED,
            Events.SYSTEM_ALERT,
            Events.HEALTH_SCORE_UPDATED,
            Events.REPORT_GENERATED,
            Events.REPORT_ACCEPTED,
            Events.REPORT_REJECTED,
            Events.PAYOUT_RECEIVED,
            Events.OPPORTUNITY_FOUND,
            Events.QUICK_WIN_DETECTED,
            Events.RECOVERY_STARTED,
            Events.RECOVERY_SUCCESS,
            Events.RECOVERY_FAILED,
            Events.TARGET_CREATED,
            Events.AUTO_OPTIMIZATION_APPLIED,
        }

        if event_type not in important_events:
            return None

        return self.make_decision(
            event_type=event_type,
            correlation_id=correlation_id,
            context=data,
        )

    # ── Heartbeat ────────────────────────────────────────────────

    def publish_heartbeat(self) -> None:
        publish_copilot_event(
            Events.COPILOT_HEARTBEAT,
            {
                "agent_id": self.agent_id,
                "authority": self._authority.value,
                "events_processed": self._event_count,
            },
        )

    # ── Capabilities ────────────────────────────────────────────

    def _register_capabilities(self) -> None:
        """Register COPILOT's own capabilities in the CapabilityRegistry."""
        reg = get_capability_registry()
        reg.register(
            "analyze_finding",
            "copilot",
            {"confidence_range": "0.0-1.0", "types": "all"},
            description="Analyze findings with full Evidence Graph context",
        )
        reg.register(
            "create_plan",
            "copilot",
            {"vuln_types": ["IDOR", "SSRF", "XSS", "SQLi", "Auth Bypass", "Generic"]},
            description="Create multi-step investigation plans",
        )
        reg.register(
            "execute_plan",
            "copilot",
            {"tools": ["http", "scan", "analyze", "memory"]},
            description="Execute investigation plan steps",
        )
        reg.register(
            "pre_report_review", "copilot", {"checklist_items": 9}, description="Run pre-report quality checklist"
        )
        reg.register(
            "audit_system",
            "copilot",
            {"auditors": ["health", "configuration", "security", "architecture"]},
            description="Run all registered system auditors",
        )
        reg.register(
            "recommend_next",
            "copilot",
            {"scope": "finding_level"},
            description="Get next-step recommendations per finding",
        )
        reg.register(
            "recommend_for_system", "copilot", {"scope": "system_level"}, description="Get system-wide top actions"
        )
        reg.register(
            "make_decision",
            "copilot",
            {"events": list(Events.ALL)},
            description="Decision Engine: produce standardized decisions from events",
        )
        logger.info("Registered %d capabilities in CapabilityRegistry", reg.count())

    # ── Internal ───────────────────────────────────────────────

    def _build_context(self, app_id: str) -> CopilotContext:
        return CopilotContext(
            app_id=app_id,
            authority_level=self._authority,
            config=self.config,
        )

    def _log_decision(self, action: str, data: dict[str, Any]) -> str:
        decision_id = f"{self.agent_id}-{uuid.uuid4().hex[:12]}"
        reason = f"Copilot {action} at {datetime.now(UTC).isoformat()}"
        confidence = data.get("confidence", 0.0) if isinstance(data, dict) else 0.0
        entry = {
            "decision_id": decision_id,
            "agent_id": self.agent_id,
            "action": action,
            "reason": reason,
            "data": data,
            "confidence": confidence,
            "authority": self._authority.value,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self._decision_journal.append(entry)
        if len(self._decision_journal) > self.config.max_decisions_logged:
            self._decision_journal.pop(0)

        # Persist to SQLite Decision Journal
        try:
            from core.decision_journal import log_decision as dj_log

            dj_log(
                app_id=self.app_id,
                agent_id=self.agent_id,
                action=action,
                reason=reason,
                data_snapshot={"confidence": confidence, "authority": self._authority.value, "payload": data},
                confidence=confidence,
            )
        except Exception as exc:
            logger.warning("Failed to persist decision to journal: %s", exc)

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
