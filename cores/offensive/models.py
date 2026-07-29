"""Offensive Intelligence — data models for hypotheses, endpoints, and reasoning."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EndpointInfo:
    """Normalized representation of an API endpoint for analysis."""

    path: str
    method: str
    params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    response_sample: dict[str, Any] | None = None
    target_id: str = ""
    host: str = ""

    @property
    def path_params(self) -> list[str]:
        return [k for k, v in self.params.items() if v.startswith("{") and v.endswith("}")]

    @property
    def query_params(self) -> list[str]:
        return [k for k, v in self.params.items() if not (v.startswith("{") and v.endswith("}"))]

    def path_depth(self) -> int:
        return len([p for p in self.path.split("/") if p])

    def resource_name(self) -> str:
        parts = [p for p in self.path.split("/") if p and not p.startswith("{") and not p.startswith(":")]
        return parts[-1] if parts else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "params": self.params,
            "headers": self.headers,
            "body": self.body,
            "target_id": self.target_id,
            "host": self.host,
        }


@dataclass
class EndpointRelationship:
    """A relationship inferred between two endpoints."""

    source_path: str
    target_path: str
    relationship_type: str  # "parent_child", "collection", "sibling", "nested_resource"
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class OwnershipEdge:
    """An inferred ownership relationship in the object graph."""

    parent_resource: str
    child_resource: str
    confidence: float
    via_param: str = ""  # e.g. "organization_id" links org→project
    evidence: list[str] = field(default_factory=list)


@dataclass
class RelationshipContext:
    """Contextual relationships for a single endpoint's analysis."""

    siblings: list[str] = field(default_factory=list)
    parent_endpoint: str = ""
    child_endpoints: list[str] = field(default_factory=list)
    collection_endpoint: str = ""
    ownership_chain: list[OwnershipEdge] = field(default_factory=list)
    similar_pattern_endpoints: list[str] = field(default_factory=list)


@dataclass
class Contradiction:
    """A counterargument that weakens a hypothesis."""

    label: str
    description: str
    confidence_reduction: float  # 0.0-1.0, how much this contradicts
    how_to_rule_out: str | None = None


@dataclass
class EvidenceItem:
    """An item in the evidence completeness scoring."""

    name: str
    present: bool = False
    weight: float = 1.0
    notes: str = ""


@dataclass
class EvidenceCompleteness:
    """Score and breakdown of how complete a hypothesis's evidence is."""

    score: float = 0.0  # 0-100
    items: list[EvidenceItem] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    strong_points: list[str] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for i in self.items if i.present)

    @property
    def total(self) -> int:
        return len(self.items)


@dataclass
class AcceptancePrediction:
    """Predicted acceptance probability with reasoning."""

    probability: float = 0.0
    positive_signals: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    questions_triager_will_ask: list[str] = field(default_factory=list)
    expected_verdict: str = "needs_review"


@dataclass
class Hypothesis:
    """A reasoner's output: this endpoint might be vulnerable to this type."""

    id: str = field(default_factory=lambda: f"hyp-{uuid.uuid4().hex[:12]}")
    vulnerability_type: str = ""
    endpoint: str = ""
    method: str = ""
    confidence: float = 0.0
    severity: str = "medium"
    summary: str = ""
    description: str = ""
    why_human_would_investigate: str = ""
    why_triager_might_reject: str = ""
    parameters_of_interest: list[str] = field(default_factory=list)
    test_instructions: list[str] = field(default_factory=list)
    alternative_explanations: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    scope_check: str = ""
    reproducibility_notes: str = ""
    relationship_context: RelationshipContext = field(default_factory=RelationshipContext)
    evidence_completeness: EvidenceCompleteness = field(default_factory=EvidenceCompleteness)
    acceptance_prediction: AcceptancePrediction = field(default_factory=AcceptancePrediction)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "vulnerability_type": self.vulnerability_type,
            "endpoint": self.endpoint,
            "method": self.method,
            "confidence": round(self.confidence, 2),
            "severity": self.severity,
            "summary": self.summary,
            "description": self.description,
            "why_human_would_investigate": self.why_human_would_investigate,
            "why_triager_might_reject": self.why_triager_might_reject,
            "parameters_of_interest": self.parameters_of_interest,
            "test_instructions": self.test_instructions,
            "alternative_explanations": self.alternative_explanations,
            "contradictions": [
                {
                    "label": c.label,
                    "description": c.description,
                    "confidence_reduction": c.confidence_reduction,
                    "how_to_rule_out": c.how_to_rule_out,
                }
                for c in self.contradictions
            ],
            "signals": self.signals,
            "scope_check": self.scope_check,
            "reproducibility_notes": self.reproducibility_notes,
            "relationship_context": {
                "siblings": self.relationship_context.siblings,
                "parent_endpoint": self.relationship_context.parent_endpoint,
                "child_endpoints": self.relationship_context.child_endpoints,
                "collection_endpoint": self.relationship_context.collection_endpoint,
            },
            "evidence_completeness": {
                "score": round(self.evidence_completeness.score, 1),
                "passed": self.evidence_completeness.passed,
                "total": self.evidence_completeness.total,
                "gaps": self.evidence_completeness.gaps,
                "strong_points": self.evidence_completeness.strong_points,
            },
            "acceptance_prediction": {
                "probability": round(self.acceptance_prediction.probability, 2),
                "positive_signals": self.acceptance_prediction.positive_signals,
                "risk_factors": self.acceptance_prediction.risk_factors,
                "questions_triager_will_ask": self.acceptance_prediction.questions_triager_will_ask,
                "expected_verdict": self.acceptance_prediction.expected_verdict,
            },
            "created_at": self.created_at,
        }


@dataclass
class InvestigationStep:
    """A single step in an investigation plan — what to do and why."""

    phase: str  # "recon", "probe", "attack", "document"
    action: str
    condition: str  # when this step applies
    expected_outcome: str  # what to look for
    follow_up: str  # what to try if outcome differs
    priority: int = 99


@dataclass
class InvestigationPlan:
    """Complete step-by-step research plan for a hypothesis."""

    hypothesis_id: str
    vulnerability_type: str
    endpoint: str
    method: str
    summary: str
    steps: list[InvestigationStep] = field(default_factory=list)
    estimated_effort: str = "medium"  # "low" / "medium" / "high"
    priority: str = "medium"
    prerequisites: list[str] = field(default_factory=list)
    alternative_approaches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "vulnerability_type": self.vulnerability_type,
            "endpoint": self.endpoint,
            "method": self.method,
            "summary": self.summary,
            "estimated_effort": self.estimated_effort,
            "priority": self.priority,
            "prerequisites": self.prerequisites,
            "alternative_approaches": self.alternative_approaches,
            "steps": [
                {
                    "phase": s.phase,
                    "action": s.action,
                    "condition": s.condition,
                    "expected_outcome": s.expected_outcome,
                    "follow_up": s.follow_up,
                    "priority": s.priority,
                }
                for s in sorted(self.steps, key=lambda x: x.priority)
            ],
        }


@dataclass
class CuriosityQuestion:
    """A question a human expert would ask about an endpoint."""

    question: str
    category: str  # "auth", "logic", "business", "technical", "edge_case"
    rationale: str
    test_suggestion: str


@dataclass
class CuriosityResult:
    """Output of the curiosity engine — questions + blind spots for an endpoint."""

    endpoint: str
    method: str
    vulnerability_type: str
    questions: list[CuriosityQuestion] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)
    recommended_focus: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "vulnerability_type": self.vulnerability_type,
            "questions": [
                {
                    "question": q.question,
                    "category": q.category,
                    "rationale": q.rationale,
                    "test_suggestion": q.test_suggestion,
                }
                for q in self.questions
            ],
            "blind_spots": self.blind_spots,
            "recommended_focus": self.recommended_focus,
        }


@dataclass
class ReasonerResult:
    """Result of running one or more reasoners on an endpoint."""

    endpoint: EndpointInfo
    hypotheses: list[Hypothesis] = field(default_factory=list)
    relationships: list[EndpointRelationship] = field(default_factory=list)
    ownership_edges: list[OwnershipEdge] = field(default_factory=list)
    transitive_ownership: list[OwnershipEdge] = field(default_factory=list)
    investigation_plan: InvestigationPlan | None = None
    curiosity: CuriosityResult | None = None
    max_confidence: float = 0.0
    recommended_action: str = "none"

    def prioritize(self) -> ReasonerResult:
        self.hypotheses.sort(key=lambda h: (h.confidence, h.severity), reverse=True)
        self.max_confidence = self.hypotheses[0].confidence if self.hypotheses else 0.0
        if self.max_confidence >= 0.6:
            self.recommended_action = "investigate"
        elif self.max_confidence >= 0.3:
            self.recommended_action = "review"
        else:
            self.recommended_action = "monitor"
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint.to_dict(),
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "relationships": [
                {
                    "source": r.source_path,
                    "target": r.target_path,
                    "type": r.relationship_type,
                    "confidence": r.confidence,
                }
                for r in self.relationships
            ],
            "ownership_edges": [
                {
                    "parent": e.parent_resource,
                    "child": e.child_resource,
                    "confidence": e.confidence,
                    "via_param": e.via_param,
                }
                for e in self.ownership_edges
            ],
            "transitive_ownership": [
                {
                    "parent": e.parent_resource,
                    "child": e.child_resource,
                    "confidence": round(e.confidence, 3),
                    "via_param": e.via_param,
                }
                for e in self.transitive_ownership
            ],
            "investigation_plan": self.investigation_plan.to_dict() if self.investigation_plan else None,
            "curiosity": self.curiosity.to_dict() if self.curiosity else None,
            "max_confidence": round(self.max_confidence, 2),
            "recommended_action": self.recommended_action,
        }
