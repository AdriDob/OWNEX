"""Knowledge Graph API Router — Visual exploration of the knowledge graph.

Backed by the canonical ``core.knowledge.graph`` singleton (SQLAlchemy).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.knowledge.graph import get_knowledge_graph

logger = logging.getLogger("ownex.api.knowledge_graph")

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])


def _kg():
    return get_knowledge_graph()


@router.get("/stats")
async def graph_stats() -> dict[str, Any]:
    """Get graph statistics."""
    return _kg().get_stats()


@router.get("/nodes")
async def list_nodes(
    type: str | None = Query(None, alias="node_type"),
    name: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """List nodes, optionally filtered by type or name pattern."""
    nodes = _kg().find_nodes(node_type=type, name_pattern=name, limit=limit, offset=offset)
    return {"count": len(nodes), "nodes": [_kg()._node_to_dict(n) for n in nodes]}


@router.get("/nodes/search")
async def search_nodes(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Search nodes by name (ILIKE)."""
    nodes = _kg().find_nodes(name_pattern=q, limit=limit)
    return {"count": len(nodes), "nodes": [_kg()._node_to_dict(n) for n in nodes]}


@router.get("/nodes/{node_id}")
async def get_node(node_id: str) -> dict[str, Any]:
    """Get a single node by ID."""
    node = _kg().get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return _kg()._node_to_dict(node)


@router.post("/nodes")
async def upsert_node(
    name: str,
    node_type: str,
    properties: dict[str, Any] | None = None,
    node_id: str | None = None,
    source: str = "",
) -> dict[str, Any]:
    """Create or update a node."""
    node = _kg().add_node(
        node_type=node_type,
        name=name,
        properties=properties or {},
        node_id=node_id,
        source=source,
    )
    return _kg()._node_to_dict(node)


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str) -> dict[str, Any]:
    """Delete a node and all its edges."""
    deleted = _kg().delete_node(node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"success": True, "node_id": node_id}


@router.get("/edges")
async def list_edges(
    source_id: str | None = Query(None),
    target_id: str | None = Query(None),
    edge_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    """List edges, optionally filtered."""
    edges = _kg().get_edges(source_id=source_id, target_id=target_id, edge_type=edge_type, limit=limit)
    return {
        "count": len(edges),
        "edges": [
            {
                "id": e.id,
                "source": e.source_id,
                "target": e.target_id,
                "relationship": e.edge_type,
                "weight": e.weight,
                "properties": _try_json(e.properties),
            }
            for e in edges
        ],
    }


@router.post("/edges")
async def create_edge(
    source_id: str,
    target_id: str,
    relationship: str,
    weight: float = Query(1.0),
) -> dict[str, Any]:
    """Create an edge between two nodes."""
    edge = _kg().add_edge(source_id, target_id, relationship, weight=weight)
    if edge is None:
        raise HTTPException(status_code=400, detail="Source or target node not found")
    return {
        "id": edge.id,
        "source": edge.source_id,
        "target": edge.target_id,
        "relationship": edge.edge_type,
        "weight": edge.weight,
    }


@router.get("/subgraph/{node_id}")
async def get_subgraph(
    node_id: str,
    depth: int = Query(2, ge=1, le=4),
    limit: int = Query(200, ge=10, le=1000),
) -> dict[str, Any]:
    """Get a subgraph centered on a node (Cytoscape/vis.js format)."""
    sub = _kg().get_subgraph(center_id=node_id, depth=depth, limit=limit)
    node_ids = {n["id"] for n in sub.get("nodes", [])}
    # Rebuild edges with real source/target from the subgraph node set.
    edges: list[dict[str, Any]] = []
    for nid in node_ids:
        for e in _kg().get_edges(source_id=nid, limit=limit):
            if e.target_id in node_ids:
                edges.append(
                    {
                        "source": e.source_id,
                        "target": e.target_id,
                        "relationship": e.edge_type,
                        "weight": e.weight,
                    }
                )
        for e in _kg().get_edges(target_id=nid, limit=limit):
            if e.source_id in node_ids:
                edges.append(
                    {
                        "source": e.source_id,
                        "target": e.target_id,
                        "relationship": e.edge_type,
                        "weight": e.weight,
                    }
                )
    # Deduplicate edges
    seen: set[tuple[str, str, str]] = set()
    unique_edges = []
    for e in edges:
        key = (e["source"], e["target"], e["relationship"])
        if key in seen:
            continue
        seen.add(key)
        unique_edges.append(e)
    return {
        "center_id": node_id,
        "nodes": sub.get("nodes", []),
        "edges": unique_edges,
        "total_nodes": sub.get("total_nodes", 0),
        "total_edges": len(unique_edges),
    }


def _try_json(raw: str | None) -> dict[str, Any]:
    import json

    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
