"""Cross-Workflow Memory — Transfer learning across workflows.

Enables learning from one workflow to be applied to others:
- Pattern extraction from completed workflows
- Skill transfer across domains
- Cross-domain pattern matching
- Workflow similarity detection
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cores.learning.memory import get_memory_builder
from cores.opportunity_genome.models import OpportunityGenome

logger = logging.getLogger("cross_workflow_memory")


@dataclass(slots=True)
class WorkflowPattern:
    """Extracted pattern from a completed workflow."""

    pattern_id: str
    workflow_type: str  # e.g., "bug_bounty", "dev_bounty", "code_generation"
    pattern_type: str  # e.g., "success_factor", "failure_mode", "optimization"
    description: str
    confidence: float  # 0-1
    evidence: list[str] = field(default_factory=list)
    applicable_domains: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    usage_count: int = 0
    success_rate: float = 0.0


@dataclass(slots=True)
class WorkflowMemory:
    """Aggregated memory for a workflow type."""

    workflow_type: str
    patterns: list[WorkflowPattern] = field(default_factory=list)
    successful_strategies: dict[str, float] = field(default_factory=dict)  # strategy -> success_rate
    failure_modes: dict[str, float] = field(default_factory=dict)  # failure_mode -> frequency
    best_practices: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class CrossWorkflowMemory:
    """Cross-workflow memory for transfer learning across workflows.

    Analyzes completed workflows to extract patterns, then applies them
    to new workflows in the same or different domains.
    """

    def __init__(self):
        self._workflow_memories: dict[str, WorkflowMemory] = {}
        self._global_patterns: list[WorkflowPattern] = []
        self._similarity_cache: dict[tuple[str, str], float | int] = {}

    def record_workflow_completion(
        self,
        workflow_type: str,
        outcome: str,  # "success", "partial", "failure"
        key_factors: list[str],  # What contributed to outcome
        metrics: dict[str, float],  # Quantifiable metrics
        artifacts: list[str],  # Artifact IDs produced
        domain: str = "general",
    ) -> None:
        """Record a completed workflow for future learning."""
        memory = self._get_or_create_memory(workflow_type)

        # Extract patterns from outcome
        if outcome in ("success", "partial"):
            for factor in key_factors:
                if factor not in memory.successful_strategies:
                    memory.successful_strategies[factor] = 0.0
                memory.successful_strategies[factor] = min(1.0, memory.successful_strategies[factor] + 0.1)
        else:
            for factor in key_factors:
                if factor not in memory.failure_modes:
                    memory.failure_modes[factor] = 0.0
                memory.failure_modes[factor] = min(1.0, memory.failure_modes[factor] + 0.1)

        # Update best practices
        if outcome == "success":
            for factor in key_factors:
                if factor not in memory.best_practices:
                    memory.best_practices.append(factor)

        # Track anti-patterns
        if outcome == "failure":
            for factor in key_factors:
                if factor not in memory.anti_patterns:
                    memory.anti_patterns.append(factor)

        memory.updated_at = datetime.now(UTC).isoformat()

        # Extract cross-domain patterns
        self._extract_cross_domain_patterns(workflow_type, domain, outcome, key_factors, metrics)

    def _get_or_create_memory(self, workflow_type: str) -> WorkflowMemory:
        if workflow_type not in self._workflow_memories:
            self._workflow_memories[workflow_type] = WorkflowMemory(workflow_type=workflow_type)
        return self._workflow_memories[workflow_type]

    def _extract_cross_domain_patterns(
        self,
        workflow_type: str,
        domain: str,
        outcome: str,
        key_factors: list[str],
        metrics: dict[str, float],
    ) -> None:
        """Extract patterns applicable across domains."""
        if outcome not in ("success", "partial"):
            return

        # Create pattern for each successful factor
        for factor in key_factors:
            # Check if similar pattern exists
            existing = self._find_similar_pattern(factor, domain)
            if existing:
                existing.usage_count += 1
                existing.applicable_domains.append(domain)
                existing.applicable_domains = list(set(existing.applicable_domains))
            else:
                pattern = WorkflowPattern(
                    pattern_id=f"pattern_{len(self._global_patterns)}",
                    workflow_type=workflow_type,
                    pattern_type="success_factor",
                    description=factor,
                    confidence=min(1.0, metrics.get("success_probability", 0.5)),
                    evidence=[f"Derived from {workflow_type} workflow in {domain}"],
                    applicable_domains=[domain],
                )
                self._global_patterns.append(pattern)

    def _find_similar_pattern(self, factor: str, domain: str) -> WorkflowPattern | None:
        """Find existing similar pattern."""
        key = (factor.lower(), domain.lower())
        if key in self._similarity_cache:
            idx = self._similarity_cache[key]
            if isinstance(idx, int) and idx < len(self._global_patterns):
                return self._global_patterns[idx]

        for i, pattern in enumerate(self._global_patterns):
            if pattern.description.lower() == factor.lower() and domain in pattern.applicable_domains:
                self._similarity_cache[key] = i
                return pattern
        return None

    def get_recommendations_for_workflow(
        self,
        workflow_type: str,
        domain: str,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Get recommendations for a workflow based on cross-domain learning."""
        recommendations = {
            "apply_strategies": [],
            "avoid_patterns": [],
            "confidence": 0.0,
            "reasoning": [],
        }

        memory = self._workflow_memories.get(workflow_type)
        if not memory:
            return recommendations

        # Apply successful strategies
        for strategy, rate in memory.successful_strategies.items():
            if rate > 0.6:
                recommendations["apply_strategies"].append(
                    {
                        "strategy": strategy,
                        "success_rate": rate,
                        "source": "same_workflow",
                    }
                )

        # Avoid failure modes
        for failure, freq in memory.failure_modes.items():
            if freq > 0.4:
                recommendations["avoid_patterns"].append(
                    {
                        "pattern": failure,
                        "frequency": freq,
                        "source": "same_workflow",
                    }
                )

        # Cross-domain patterns
        for pattern in self._global_patterns:
            if domain in pattern.applicable_domains:
                if pattern.confidence > 0.7:
                    recommendations["apply_strategies"].append(
                        {
                            "strategy": pattern.description,
                            "confidence": pattern.confidence,
                            "source": f"cross_domain ({pattern.workflow_type})",
                            "evidence": pattern.evidence,
                        }
                    )

        # Calculate overall confidence
        if recommendations["apply_strategies"]:
            recommendations["confidence"] = sum(
                s.get("success_rate", s.get("confidence", 0)) for s in recommendations["apply_strategies"]
            ) / len(recommendations["apply_strategies"])

        recommendations["reasoning"].extend(
            [
                f"Based on {len(memory.successful_strategies)} successful strategies in {workflow_type}",
                f"Cross-domain patterns from {len([p for p in self._global_patterns if domain in p.applicable_domains])} patterns",
            ]
        )

        return recommendations

    def get_workflow_similarity(self, wf_type1: str, wf_type2: str) -> float:
        """Calculate similarity between two workflow types."""
        key: tuple[str, str] = tuple(sorted([wf_type1, wf_type2]))  # type: ignore[assignment]
        if key in self._similarity_cache:
            return self._similarity_cache[key]

        mem1 = self._workflow_memories.get(wf_type1)
        mem2 = self._workflow_memories.get(wf_type2)

        if not mem1 or not mem2:
            return 0.0

        # Compare strategies
        strategies1 = set(mem1.successful_strategies.keys())
        strategies2 = set(mem2.successful_strategies.keys())

        if not strategies1 or not strategies2:
            return 0.0

        intersection = strategies1 & strategies2
        union = strategies1 | strategies2

        similarity = len(intersection) / len(union) if union else 0.0
        self._similarity_cache[key] = similarity
        return similarity


# Global instance
_cross_workflow_memory: CrossWorkflowMemory | None = None


def get_cross_workflow_memory() -> CrossWorkflowMemory:
    """Get or create the global cross-workflow memory."""
    global _cross_workflow_memory
    if _cross_workflow_memory is None:
        _cross_workflow_memory = CrossWorkflowMemory()
    return _cross_workflow_memory


# Convenience function for WorkerCore integration
async def get_cross_workflow_recommendations(
    workflow_type: str,
    domain: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Get cross-workflow recommendations for a workflow."""
    memory = get_cross_workflow_memory()
    return memory.get_recommendations_for_workflow(workflow_type, domain, {})
