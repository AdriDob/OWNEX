"""Offensive Intelligence API — analyze endpoints and retrieve hypotheses."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from core.offensive.engine import OffensiveEngine

router = APIRouter(prefix="/api/offensive", tags=["offensive"])

_engine: OffensiveEngine | None = None


class AnalyzeRequest(BaseModel):
    """Request body for endpoint analysis."""

    path: str
    method: str = "GET"
    params: dict = {}
    headers: dict = {}
    body: dict | None = None
    response_sample: dict | None = None
    target_id: str = ""
    host: str = ""


def _get_engine() -> OffensiveEngine:
    global _engine
    if _engine is None:
        _engine = OffensiveEngine()
    return _engine


@router.post("/analyze")
def analyze_endpoint(req: AnalyzeRequest):
    """Analyze a single endpoint through all reasoners."""
    engine = _get_engine()
    result = engine.analyze_endpoint(req.model_dump())
    return result.prioritize().to_dict()


@router.post("/analyze/batch")
def analyze_batch(endpoints: list[AnalyzeRequest]):
    """Analyze multiple endpoints at once (parallel)."""
    engine = _get_engine()
    results = engine.analyze_batch([req.model_dump() for req in endpoints])
    return {
        "total": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.post("/analyze/collection")
def analyze_collection(endpoints: list[AnalyzeRequest]):
    """Analyze an entire collection of endpoints with full relationship graph (parallel)."""
    engine = _get_engine()
    return engine.analyze_collection([req.model_dump() for req in endpoints])


@router.post("/reasoners/{vuln_type}/outcome")
def record_reasoner_outcome(vuln_type: str, hypothesis_id: str, confirmed: bool):
    """Record whether a hypothesis was confirmed or rejected (feedback loop)."""
    engine = _get_engine()
    engine.record_outcome(vuln_type, hypothesis_id, confirmed)
    return {"status": "recorded", "vulnerability_type": vuln_type, "hypothesis_id": hypothesis_id}


@router.get("/reasoners/stats")
def get_reasoner_stats():
    """Get outcome statistics for all reasoners."""
    engine = _get_engine()
    return engine.get_reasoner_stats()


@router.get("/hypotheses")
def list_hypotheses(
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    max_results: int = Query(50, ge=1, le=200),
):
    """List recent hypotheses from the Knowledge Graph."""
    from core.knowledge.graph import get_knowledge_graph

    kg = get_knowledge_graph()
    nodes = kg.find_nodes(node_type="finding", limit=max_results)
    hypotheses = []
    for node in nodes:
        props = node.properties or {}
        if props.get("vulnerability_type") and props.get("confidence", 0) >= min_confidence:
            hypotheses.append(props)
    return {
        "total": len(hypotheses),
        "hypotheses": sorted(hypotheses, key=lambda h: h.get("confidence", 0), reverse=True),
    }


@router.post("/plan")
def generate_investigation_plan(
    path: str = Query(..., description="Endpoint path"),
    method: str = Query("GET", description="HTTP method"),
    vulnerability_type: str = Query("idor", description="Vulnerability type"),
    summary: str = Query("", description="Hypothesis summary"),
):
    """Generate a step-by-step investigation plan for a hypothesis."""
    from core.offensive.models import Hypothesis
    from core.offensive.planner import InvestigationPlanner

    hyp = Hypothesis(
        vulnerability_type=vulnerability_type,
        endpoint=path,
        method=method,
        confidence=0.0,
        summary=summary or f"Potential {vulnerability_type} in {method} {path}",
    )
    planner = InvestigationPlanner()
    plan = planner.plan(hyp)
    return plan.to_dict()


@router.post("/curiosity")
def explore_endpoint(
    path: str = Query(..., description="Endpoint path"),
    method: str = Query("GET", description="HTTP method"),
    vulnerability_type: str = Query("idor", description="Vulnerability type"),
):
    """Generate expert-level questions and identify blind spots for an endpoint."""
    from core.offensive.curiosity import CuriosityEngine

    engine = CuriosityEngine()
    result = engine.explore_endpoint(path, method, vulnerability_type)
    return result.to_dict()


@router.get("/ownership-graph")
def get_ownership_graph(
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
):
    """Get the current ownership graph with transitive relationships."""
    from core.knowledge.graph import get_knowledge_graph

    kg = get_knowledge_graph()
    nodes = kg.find_nodes(node_type="endpoint", limit=200)
    from core.offensive.relationship import EndpointRelationshipEngine

    engine = EndpointRelationshipEngine()
    endpoints = [{"path": n.properties.get("name", n.name), "method": n.properties.get("method", "GET")} for n in nodes]
    if not endpoints:
        return {"direct_edges": [], "transitive_edges": [], "total": 0}
    ep_objects = EndpointRelationshipEngine.normalize_endpoints(endpoints)
    direct = engine.build_ownership_graph(ep_objects)
    transitive = engine.build_transitive_ownership_graph(direct)
    return {
        "direct_edges": [
            {"parent": e.parent_resource, "child": e.child_resource, "confidence": e.confidence}
            for e in direct
            if e.confidence >= min_confidence
        ],
        "transitive_edges": [
            {
                "parent": e.parent_resource,
                "child": e.child_resource,
                "confidence": e.confidence,
                "via_param": e.via_param,
            }
            for e in transitive
            if e.confidence >= min_confidence
        ],
        "total": len(direct) + len(transitive),
    }
