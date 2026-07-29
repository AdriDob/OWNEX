"""Offensive Intelligence Engine — orchestrator for all reasoners.

Pipeline:
  1. Endpoint Relationship Engine (graph context)
  2. Reasoners (hypothesis generation)
  3. Contradiction Engine (self-critique)
  4. Triager Simulator (evidence scoring + acceptance prediction)
  5. Knowledge Graph recording
  6. EventBus publishing
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from core.capabilities.registry import get_capability_registry
from core.knowledge.graph import get_knowledge_graph
from core.offensive.contradiction import ContradictionEngine
from core.offensive.curiosity import CuriosityEngine
from core.offensive.models import EndpointInfo, ReasonerResult
from core.offensive.planner import InvestigationPlanner
from core.offensive.publisher import publish_offensive_event
from core.offensive.reasoners.auth_bypass import AuthBypassReasoner
from core.offensive.reasoners.base import BaseReasoner
from core.offensive.reasoners.idor import IDORReasoner
from core.offensive.reasoners.sqli import SQLiReasoner
from core.offensive.reasoners.ssrf import SSRFReasoner
from core.offensive.reasoners.xss import XSSReasoner
from core.offensive.relationship import EndpointRelationshipEngine
from core.offensive.triager import TriagerSimulator

logger = logging.getLogger("orion.core.offensive.engine")

_BATCH_TIMEOUT = 30
_BATCH_MAX_WORKERS = 4


class OffensiveEngine:
    """Orchestrates the full offensive analysis pipeline.

    Usage::

        engine = OffensiveEngine()
        result = engine.analyze_endpoint({
            "path": "/api/users/123",
            "method": "GET",
            "params": {"id": "123"},
        })
        logger.info(result.prioritize().to_dict())
    """

    def __init__(self) -> None:
        self._kg = get_knowledge_graph()
        self._reasoners: list[BaseReasoner] = []
        self._relationship_engine = EndpointRelationshipEngine()
        self._contradiction_engine = ContradictionEngine()
        self._triager = TriagerSimulator()
        self._planner = InvestigationPlanner()
        self._curiosity = CuriosityEngine()
        self._cached_endpoints: list[EndpointInfo] = []
        self._register_capabilities()
        self._discover_reasoners()

    def _register_capabilities(self) -> None:
        reg = get_capability_registry()
        reg.register(
            capability="analyze_endpoint",
            module="offensive",
            metadata={"types": ["idor", "ssrf", "auth_bypass", "xss", "sqli"]},
            description="Analyze an API endpoint for vulnerabilities",
        )
        reg.register(
            capability="generate_hypothesis",
            module="offensive",
            metadata={"types": ["idor", "ssrf", "auth_bypass", "xss", "sqli"]},
            description="Generate offensive hypotheses for a target",
        )
        reg.register(
            capability="generate_investigation_plan",
            module="offensive",
            metadata={"types": ["idor", "ssrf", "auth_bypass", "xss", "sqli"]},
            description="Generate step-by-step investigation plan for a hypothesis",
        )
        reg.register(
            capability="curiosity_explore",
            module="offensive",
            description="Generate expert-level questions about an endpoint",
        )
        reg.register(
            capability="build_ownership_graph",
            module="offensive",
            description="Build transitive ownership graph from endpoint collection",
        )
        reg.register(
            capability="triager_simulate",
            module="offensive",
            description="Simulate human triage on a hypothesis",
        )
        reg.register(
            capability="batch_analyze",
            module="offensive",
            description="Analyze multiple endpoints in parallel",
        )

    def _discover_reasoners(self) -> None:
        self._reasoners = [
            IDORReasoner(),
            SSRFReasoner(),
            AuthBypassReasoner(),
            XSSReasoner(),
            SQLiReasoner(),
        ]

    # ── Feedback ───────────────────────────────────────────────────

    def get_reasoner(self, vuln_type: str) -> BaseReasoner | None:
        """Get a reasoner by vulnerability type."""
        for r in self._reasoners:
            if r.vulnerability_type == vuln_type:
                return r
        return None

    def record_outcome(self, vuln_type: str, hypothesis_id: str, was_confirmed: bool) -> None:
        """Record an outcome for a specific reasoner (learn from results)."""
        reasoner = self.get_reasoner(vuln_type)
        if reasoner:
            reasoner.record_outcome(hypothesis_id, was_confirmed)

    def get_reasoner_stats(self) -> dict[str, Any]:
        """Get outcome statistics for all reasoners."""
        return {r.vulnerability_type: r.get_outcome_stats() for r in self._reasoners}

    def set_context(self, all_endpoints: list[dict[str, Any]]) -> None:
        """Pre-load all known endpoints for relationship analysis.

        Call this once before analyzing individual endpoints so the
        relationship engine can provide multi-endpoint context.
        """
        self._cached_endpoints = EndpointRelationshipEngine.normalize_endpoints(all_endpoints)

    def analyze_endpoint(self, endpoint_data: dict[str, Any]) -> ReasonerResult:
        """Analyze a single endpoint through the full pipeline.

        Pipeline:
          1. Build EndpointInfo
          2. Infer relationships (if batch context available)
          3. Run reasoners → hypotheses
          4. Attack hypotheses with contradictions
          5. Score evidence completeness
          6. Predict acceptance
          7. Prioritize results
          8. Record to KG
          9. Publish events
        """
        endpoint = EndpointInfo(
            path=endpoint_data.get("path", ""),
            method=endpoint_data.get("method", "GET"),
            params=endpoint_data.get("params", {}),
            headers=endpoint_data.get("headers", {}),
            body=endpoint_data.get("body"),
            response_sample=endpoint_data.get("response_sample"),
            target_id=endpoint_data.get("target_id", ""),
            host=endpoint_data.get("host", ""),
        )

        result = ReasonerResult(endpoint=endpoint)

        # ── Step 1: Relationship context ──────────────────────────
        if self._cached_endpoints:
            ctx = self._relationship_engine.analyze(endpoint, self._cached_endpoints)
            result.relationships = self._relationship_engine.build_relationships(self._cached_endpoints)
            result.ownership_edges = self._relationship_engine.build_ownership_graph(self._cached_endpoints)
        else:
            ctx = self._relationship_engine.analyze(endpoint, [endpoint])

        # ── Step 2: Generate hypotheses ───────────────────────────
        for reasoner in self._reasoners:
            if endpoint.method.upper() not in reasoner.supported_methods():
                continue
            try:
                hypotheses = reasoner.analyze(endpoint)
                for hyp in hypotheses:
                    hyp.relationship_context = ctx
                result.hypotheses.extend(hypotheses)
            except Exception as exc:
                logger.exception("[%s] Analysis failed: %s", reasoner.vulnerability_type, exc)

        # ── Step 3: Attack with contradictions ────────────────────
        for hyp in result.hypotheses:
            hyp.contradictions = self._contradiction_engine.attack(hyp)

        # ── Step 4: Score evidence + predict acceptance ───────────
        for hyp in result.hypotheses:
            triage = self._triager.evaluate(hyp)
            hyp.evidence_completeness.score = triage["evidence_completeness"]["score"]
            hyp.evidence_completeness.gaps = triage["evidence_completeness"]["gaps"]
            hyp.evidence_completeness.strong_points = triage["evidence_completeness"]["strong_points"]
            hyp.evidence_completeness.items = []  # items set internally
            hyp.acceptance_prediction.probability = triage["acceptance_prediction"]["probability"]
            hyp.acceptance_prediction.positive_signals = triage["acceptance_prediction"]["positive_signals"]
            hyp.acceptance_prediction.risk_factors = triage["acceptance_prediction"]["risk_factors"]
            hyp.acceptance_prediction.questions_triager_will_ask = triage["acceptance_prediction"][
                "questions_triager_will_ask"
            ]

        # ── Step 5: Generate investigation plans ──────────────────
        for hyp in result.hypotheses:
            try:
                result.investigation_plan = self._planner.plan(hyp)
            except Exception as exc:
                logger.exception("[PLANNER] Failed to generate plan: %s", exc)

        # ── Step 6: Generate curiosity questions ──────────────────
        for hyp in result.hypotheses:
            try:
                result.curiosity = self._curiosity.explore(hyp)
            except Exception as exc:
                logger.exception("[CURIOSITY] Failed to generate questions: %s", exc)

        # ── Step 7: Transitive ownership ──────────────────────────
        try:
            ownership_context = self._relationship_engine.build_transitive_ownership_graph(result.ownership_edges)
            result.transitive_ownership = ownership_context
        except Exception as exc:
            logger.exception("[OWNERSHIP] Failed to build transitive graph: %s", exc)

        # ── Step 8: Prioritize ────────────────────────────────────
        result.prioritize()

        # ── Step 6: Record to KG ──────────────────────────────────
        self._record_to_kg(endpoint, result)

        # ── Step 7: Publish events ────────────────────────────────
        self._publish_events(result)

        logger.info(
            "Analyzed %s %s → %d hypotheses | max confidence %.2f | evidence: %.1f%% | acceptance: %.0f%%",
            endpoint.method,
            endpoint.path,
            len(result.hypotheses),
            result.max_confidence,
            result.hypotheses[0].evidence_completeness.score if result.hypotheses else 0,
            result.hypotheses[0].acceptance_prediction.probability * 100 if result.hypotheses else 0,
        )
        return result

    def analyze_batch(self, endpoints: list[dict[str, Any]]) -> list[ReasonerResult]:
        """Analyze multiple endpoints with full relationship context (parallel)."""
        self.set_context(endpoints)
        results: list[ReasonerResult] = []

        with ThreadPoolExecutor(max_workers=_BATCH_MAX_WORKERS) as pool:
            futures = {pool.submit(self.analyze_endpoint, ep): ep for ep in endpoints}
            for future in as_completed(futures, timeout=_BATCH_TIMEOUT):
                try:
                    results.append(future.result())
                except Exception as exc:
                    ep = futures[future]
                    logger.exception(
                        "[BATCH] Failed to analyze %s %s: %s", ep.get("method", "GET"), ep.get("path", ""), exc
                    )
                    # Return empty result instead of failing entirely
                    results.append(
                        ReasonerResult(
                            endpoint=EndpointInfo(
                                path=ep.get("path", ""),
                                method=ep.get("method", "GET"),
                                params=ep.get("params", {}),
                            )
                        )
                    )

        results.sort(key=lambda r: r.max_confidence, reverse=True)
        return results

    def analyze_collection(self, endpoints: list[dict[str, Any]]) -> dict[str, Any]:
        """Full collection analysis: relationships + ownership graph + individual analyses."""
        self.set_context(endpoints)
        ep_objects = EndpointRelationshipEngine.normalize_endpoints(endpoints)

        relationships = self._relationship_engine.build_relationships(ep_objects)
        ownership_edges = self._relationship_engine.build_ownership_graph(ep_objects)

        results = [self.analyze_endpoint(ep) for ep in endpoints]
        results.sort(key=lambda r: r.max_confidence, reverse=True)

        return {
            "total_endpoints": len(endpoints),
            "total_relationships": len(relationships),
            "total_ownership_edges": len(ownership_edges),
            "total_hypotheses": sum(len(r.hypotheses) for r in results),
            "relationships": [
                {
                    "source": r.source_path,
                    "target": r.target_path,
                    "type": r.relationship_type,
                    "confidence": r.confidence,
                }
                for r in relationships[:50]
            ],
            "ownership_graph": [
                {
                    "parent": e.parent_resource,
                    "child": e.child_resource,
                    "confidence": e.confidence,
                    "via_param": e.via_param,
                }
                for e in ownership_edges[:50]
            ],
            "results": [r.to_dict() for r in results],
            "top_hypotheses": [
                {
                    "endpoint": r.endpoint.path,
                    "method": r.endpoint.method,
                    "confidence": r.max_confidence,
                    "recommended_action": r.recommended_action,
                    "evidence_score": r.hypotheses[0].evidence_completeness.score if r.hypotheses else 0,
                    "acceptance": r.hypotheses[0].acceptance_prediction.probability if r.hypotheses else 0,
                    "summary": r.hypotheses[0].summary if r.hypotheses else "",
                }
                for r in results[:10]
                if r.hypotheses
            ],
        }

    def _record_to_kg(self, endpoint: EndpointInfo, result: ReasonerResult) -> None:
        kind = f"endpoint:{endpoint.method}:{endpoint.path}"
        node = self._kg.add_node(
            "endpoint",
            name=endpoint.path,
            node_id=kind,
            properties={
                "method": endpoint.method,
                "params": endpoint.params,
                "host": endpoint.host,
                "hypotheses": len(result.hypotheses),
                "max_confidence": result.max_confidence,
                "recommended_action": result.recommended_action,
                "evidence_score": result.hypotheses[0].evidence_completeness.score if result.hypotheses else 0,
                "acceptance": result.hypotheses[0].acceptance_prediction.probability if result.hypotheses else 0,
            },
            source="offensive",
        )
        for hyp in result.hypotheses:
            finding_node = self._kg.add_node(
                "finding",
                name=hyp.summary,
                properties=hyp.to_dict(),
                source="offensive",
            )
            self._kg.add_edge(node.id, finding_node.id, "has_finding")
            if endpoint.target_id:
                self._kg.add_edge(endpoint.target_id, node.id, "has_endpoint")

    def _publish_events(self, result: ReasonerResult) -> None:
        for hyp in result.hypotheses:
            publish_offensive_event(
                "hypothesis:generated",
                {
                    "endpoint": hyp.endpoint,
                    "method": hyp.method,
                    "vulnerability_type": hyp.vulnerability_type,
                    "confidence": hyp.confidence,
                    "summary": hyp.summary,
                    "hypothesis_id": hyp.id,
                    "evidence_score": hyp.evidence_completeness.score,
                    "acceptance": hyp.acceptance_prediction.probability,
                },
            )
