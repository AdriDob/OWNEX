"""Root Cause Analyzer — Diagnoses problems using MERLIN/OAR reasoning."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from cores.ai.runtime import get_oar
from cores.events.event_bus import get_event_bus
from cores.self_healer.models import (
    Diagnosis,
    DiagnosisConfidence,
    FixStrategy,
    Problem,
    ProblemSeverity,
)

logger = logging.getLogger("ownex.self_healer.reasoner")


KNOWN_PATTERNS = {
    "health_score_drop": {
        "indicators": ["health score dropped", "health score decreased"],
        "root_cause": "Component health checks failing or dependency degradation",
        "factors": ["downstream service failure", "resource exhaustion", "config drift"],
        "strategy": FixStrategy.CONFIG_CHANGE,
        "confidence": DiagnosisConfidence.HIGH,
    },
    "scheduler_job_failing": {
        "indicators": ["scheduler job", "failing repeatedly", "job failed"],
        "root_cause": "Job dependency unavailable or job logic error",
        "factors": ["external API down", "database locked", "timeout misconfiguration"],
        "strategy": FixStrategy.CODE_PATCH,
        "confidence": DiagnosisConfidence.HIGH,
    },
    "high_memory_usage": {
        "indicators": ["memory usage", "high memory", "memory at"],
        "root_cause": "Memory leak or insufficient resources",
        "factors": ["unclosed connections", "cache not evicting", "large dataset loaded"],
        "strategy": FixStrategy.CODE_PATCH,
        "confidence": DiagnosisConfidence.MEDIUM,
    },
    "high_cpu_usage": {
        "indicators": ["cpu usage", "high cpu", "cpu at"],
        "root_cause": "Infinite loop or inefficient computation",
        "factors": ["runaway process", "unoptimized query", "polling too frequent"],
        "strategy": FixStrategy.CODE_PATCH,
        "confidence": DiagnosisConfidence.MEDIUM,
    },
    "disk_space_critical": {
        "indicators": ["disk space", "disk usage", "disk at"],
        "root_cause": "Logs not rotating or temp files accumulating",
        "factors": ["log rotation disabled", "cleanup job failed", "large artifacts"],
        "strategy": FixStrategy.CONFIG_CHANGE,
        "confidence": DiagnosisConfidence.HIGH,
    },
    "component_unhealthy": {
        "indicators": ["component unhealthy", "health check failed", "unhealthy"],
        "root_cause": "Dependency unreachable or misconfigured",
        "factors": ["network issue", "auth expired", "service down"],
        "strategy": FixStrategy.CONFIG_CHANGE,
        "confidence": DiagnosisConfidence.HIGH,
    },
    "test_failure": {
        "indicators": ["test failed", "test failure", "pytest"],
        "root_cause": "Code regression or flaky test",
        "factors": ["recent change broke test", "environment difference", "timing issue"],
        "strategy": FixStrategy.CODE_PATCH,
        "confidence": DiagnosisConfidence.MEDIUM,
    },
}


class RootCauseAnalyzer:
    """Analyzes problems and generates diagnoses using AI reasoning."""

    def __init__(self):
        self.event_bus = get_event_bus()
        self.oar = None
        self._pattern_cache = KNOWN_PATTERNS.copy()
        self._diagnosis_count = 0

    async def initialize(self) -> None:
        """Initialize OAR runtime for AI reasoning."""
        try:
            self.oar = get_oar()
            if not self.oar._initialized:
                await self.oar.initialize()
        except Exception as e:
            logger.warning(f"OAR not available for reasoning: {e}")

    def _match_known_pattern(self, problem: Problem) -> dict[str, Any] | None:
        """Match problem against known patterns for quick diagnosis."""
        text = f"{problem.title} {problem.description}".lower()

        for pattern_name, pattern in self._pattern_cache.items():
            for indicator in pattern["indicators"]:
                if indicator.lower() in text:
                    return pattern
        return None

    async def analyze(self, problem: Problem) -> Diagnosis:
        """Analyze a problem and generate a diagnosis."""
        self._diagnosis_count += 1
        diagnosis_id = f"diag_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{self._diagnosis_count}"

        # Try quick pattern match first
        pattern = self._match_known_pattern(problem)

        if pattern and problem.severity != ProblemSeverity.CRITICAL:
            # Use known pattern for quick diagnosis
            pattern_name = next((k for k, v in self._pattern_cache.items() if v == pattern), "unknown")
            return Diagnosis(
                id=f"diag_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                problem_id=problem.id,
                root_cause=pattern["root_cause"],
                contributing_factors=pattern["factors"],
                confidence=pattern["confidence"],
                evidence=[f"Matched pattern: {pattern_name}"],
                reasoning=f"Problem matches known pattern '{pattern_name}'. Indicators found in problem description.",
                suggested_strategy=pattern["strategy"],
                estimated_effort_hours=self._estimate_effort(pattern["strategy"]),
                risk_level=self._estimate_risk(problem, pattern["strategy"]),
            )

        # Use AI reasoning for complex/unknown problems
        if self.oar:
            return await self._analyze_with_ai(problem)

        # Fallback: heuristic analysis
        return await self._analyze_heuristic(problem)

    async def _analyze_with_ai(self, problem: Problem) -> Diagnosis:
        """Use OAR/LLM for deep root cause analysis."""
        try:
            system_prompt = """You are a senior Site Reliability Engineer analyzing system problems.
Given a problem description, provide:
1. Root cause (specific, actionable)
2. Contributing factors (list)
3. Confidence level (low/medium/high/very_high)
4. Evidence from the problem data
5. Reasoning for your conclusion
6. Suggested fix strategy (config_change/code_patch/dependency_update/restart_service/rollback/workaround/manual_intervention)
7. Estimated effort in hours
8. Risk level (low/medium/high/critical)

Be precise and technical. Avoid generic answers."""

            user_prompt = f"""Problem:
- ID: {problem.id}
- Category: {problem.category.value}
- Severity: {problem.severity.value}
- Title: {problem.title}
- Description: {problem.description}
- Affected Components: {problem.affected_components}
- Metrics: {problem.metrics}
- First Seen: {problem.first_seen.isoformat()}
- Occurrences: {problem.occurrence_count}

Provide your analysis as JSON with keys: root_cause, contributing_factors, confidence, evidence, reasoning, suggested_strategy, estimated_effort_hours, risk_level"""

            result = await self.oar.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                task_type="analysis",
                max_tokens=1500,
                temperature=0.3,
            )

            analysis = json.loads(result.get("content", "{}"))

            return Diagnosis(
                id=f"diag_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                problem_id=problem.id,
                root_cause=analysis.get("root_cause", "Unknown"),
                contributing_factors=analysis.get("contributing_factors", []),
                confidence=DiagnosisConfidence(analysis.get("confidence", "medium")),
                evidence=analysis.get("evidence", []),
                reasoning=analysis.get("reasoning", ""),
                suggested_strategy=FixStrategy(analysis.get("suggested_strategy", "manual_intervention")),
                estimated_effort_hours=float(analysis.get("estimated_effort_hours", 2.0)),
                risk_level=ProblemSeverity(analysis.get("risk_level", "medium")),
            )

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return await self._analyze_heuristic(problem)

    async def _analyze_heuristic(self, problem: Problem) -> Diagnosis:
        """Heuristic fallback analysis."""
        strategy_map = {
            "health_degradation": FixStrategy.CONFIG_CHANGE,
            "error_spike": FixStrategy.CODE_PATCH,
            "performance_regression": FixStrategy.CODE_PATCH,
            "test_failure": FixStrategy.CODE_PATCH,
            "sla_violation": FixStrategy.CONFIG_CHANGE,
            "resource_exhaustion": FixStrategy.CONFIG_CHANGE,
            "config_drift": FixStrategy.CONFIG_CHANGE,
            "dependency_failure": FixStrategy.DEPENDENCY_UPDATE,
            "security_anomaly": FixStrategy.MANUAL_INTERVENTION,
        }

        strategy = strategy_map.get(problem.category.value, FixStrategy.MANUAL_INTERVENTION)

        return Diagnosis(
            id=f"diag_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            problem_id=problem.id,
            root_cause=f"Heuristic analysis: {problem.category.value} likely caused by recent changes or dependency issues",
            contributing_factors=["Recent deployment", "Configuration change", "External dependency"],
            confidence=DiagnosisConfidence.LOW,
            evidence=[f"Category: {problem.category.value}", f"Severity: {problem.severity.value}"],
            reasoning="No AI available, using heuristic mapping from problem category to likely causes.",
            suggested_strategy=strategy,
            estimated_effort_hours=2.0,
            risk_level=problem.severity,
        )

    def _estimate_effort(self, strategy: FixStrategy) -> float:
        effort_map = {
            FixStrategy.CONFIG_CHANGE: 0.5,
            FixStrategy.CODE_PATCH: 2.0,
            FixStrategy.DEPENDENCY_UPDATE: 1.0,
            FixStrategy.RESTART_SERVICE: 0.25,
            FixStrategy.ROLLBACK: 0.5,
            FixStrategy.WORKAROUND: 1.0,
            FixStrategy.MANUAL_INTERVENTION: 4.0,
        }
        return effort_map.get(strategy, 2.0)

    def _estimate_risk(self, problem: Problem, strategy: FixStrategy) -> ProblemSeverity:
        risk_map = {
            FixStrategy.CONFIG_CHANGE: ProblemSeverity.LOW,
            FixStrategy.CODE_PATCH: ProblemSeverity.MEDIUM,
            FixStrategy.DEPENDENCY_UPDATE: ProblemSeverity.MEDIUM,
            FixStrategy.RESTART_SERVICE: ProblemSeverity.LOW,
            FixStrategy.ROLLBACK: ProblemSeverity.LOW,
            FixStrategy.WORKAROUND: ProblemSeverity.LOW,
            FixStrategy.MANUAL_INTERVENTION: ProblemSeverity.HIGH,
        }
        base_risk = risk_map.get(strategy, ProblemSeverity.MEDIUM)
        if problem.severity == ProblemSeverity.CRITICAL:
            return ProblemSeverity.HIGH
        return base_risk

    def add_pattern(self, name: str, pattern: dict[str, Any]) -> None:
        """Add a new known pattern."""
        self._pattern_cache[name] = pattern
        logger.info(f"Added known pattern: {name}")

    def get_status(self) -> dict[str, Any]:
        return {
            "diagnosis_count": self._diagnosis_count,
            "known_patterns": len(self._pattern_cache),
            "oar_available": self.oar is not None,
            "patterns": list(self._pattern_cache.keys()),
        }


# Singleton
_root_cause_analyzer: RootCauseAnalyzer | None = None


def get_root_cause_analyzer() -> RootCauseAnalyzer:
    global _root_cause_analyzer
    if _root_cause_analyzer is None:
        _root_cause_analyzer = RootCauseAnalyzer()
    return _root_cause_analyzer
