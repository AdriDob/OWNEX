"""Endpoint Relationship Engine — infers relationships between endpoints.

Takes a collection of endpoints and builds:
  - Parent/child hierarchies  (/users ← /users/{id})
  - Collection patterns  (/users → collection of user resources)
  - Ownership chains  (user → org → project → invoice)
  - Sibling detection  (/users/{id}/profile and /users/{id}/settings)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from core.offensive.models import EndpointInfo, EndpointRelationship, OwnershipEdge, RelationshipContext

logger = logging.getLogger("orion.core.offensive.relationship")

PATH_PARAM_PATTERN = re.compile(r"\{[^}]+\}|:[a-zA-Z_]+")


class EndpointRelationshipEngine:
    """Infers relationships between endpoints to build an attack surface graph.

    Usage::

        engine = EndpointRelationshipEngine()
        ctx = engine.analyze(endpoint, all_endpoints)
        # ctx.parent_endpoint → "/api/users" if endpoint is "/api/users/{id}"
    """

    def analyze(self, endpoint: EndpointInfo, all_endpoints: list[EndpointInfo]) -> RelationshipContext:
        """Given an endpoint and all known endpoints, infer its relationships."""
        ctx = RelationshipContext()
        template = self._path_template(endpoint.path)

        for other in all_endpoints:
            if other.path == endpoint.path:
                continue

            other_template = self._path_template(other.path)
            ep_parent_of_other = self._is_parent(endpoint.path, other.path)
            other_parent_of_ep = self._is_parent(other.path, endpoint.path)

            # Parent: other is a parent/collection of endpoint
            if other_parent_of_ep:
                ctx.parent_endpoint = other.path
                if template != other_template:
                    ctx.collection_endpoint = other.path

            # Child: other is a child of endpoint
            if ep_parent_of_other:
                ctx.child_endpoints.append(other.path)

            # Sibling: same parent path prefix, same depth, different resource
            if self._is_sibling(endpoint.path, other.path):
                ctx.siblings.append(other.path)

            # Similar pattern: same abstract structure (param positions match)
            if self._abstract_pattern(endpoint.path) == self._abstract_pattern(other.path):
                ctx.similar_pattern_endpoints.append(other.path)

        ctx.siblings = list(set(ctx.siblings))
        ctx.child_endpoints = list(set(ctx.child_endpoints))
        ctx.similar_pattern_endpoints = list(set(ctx.similar_pattern_endpoints))

        # Collection inference: if this endpoint has children and its own path has no params, it's a collection
        if ctx.child_endpoints and not PATH_PARAM_PATTERN.search(endpoint.path):
            ctx.collection_endpoint = endpoint.path

        return ctx

    def build_relationships(self, endpoints: list[EndpointInfo]) -> list[EndpointRelationship]:
        """Build all pairwise relationships across a collection of endpoints."""
        relationships: list[EndpointRelationship] = []

        for ep in endpoints:
            template = self._path_template(ep.path)
            for other in endpoints:
                if other.path == ep.path:
                    continue
                rel = self._infer_relationship(ep, template, other)
                if rel is not None:
                    relationships.append(rel)

        return relationships

    def build_ownership_graph(self, endpoints: list[EndpointInfo]) -> list[OwnershipEdge]:
        """Infer ownership chains from endpoint structure.

        Looks for patterns like:
          /users/{userId}/organizations/{orgId}
          → user owns organization

          /organizations/{orgId}/projects/{projectId}
          → organization owns project
        """
        edges: list[OwnershipEdge] = []
        seen: set[str] = set()

        for ep in endpoints:
            parts = [p for p in ep.path.split("/") if p]
            param_positions = [
                (i, parts[i]) for i in range(len(parts)) if parts[i].startswith("{") or parts[i].startswith(":")
            ]

            for pi, param in param_positions:
                if pi + 1 >= len(parts):
                    continue
                sub_resource = parts[pi + 1]
                if sub_resource.startswith("{"):
                    continue
                resource_type = parts[pi - 1] if pi >= 1 and not parts[pi - 1].startswith("{") else ""
                if not resource_type:
                    continue

                child = sub_resource.rstrip("s")
                key = f"{resource_type}->{child}"
                if key in seen:
                    continue
                seen.add(key)

                param_name = param.strip("{}:")
                edges.append(
                    OwnershipEdge(
                        parent_resource=resource_type,
                        child_resource=child,
                        confidence=0.55,
                        via_param=param_name,
                        evidence=[
                            f"Path pattern: .../{resource_type}/{{{param_name}}}/{sub_resource}/...",
                            f"Nested resource suggests {resource_type} owns {child}",
                        ],
                    )
                )

        return edges

    def build_transitive_ownership_graph(
        self, direct_edges: list[OwnershipEdge], confidence_decay: float = 0.65
    ) -> list[OwnershipEdge]:
        """Extend ownership edges with transitive relationships.

        If user→organization and organization→project, infers user→project
        with confidence = min(parent.confidence, child.confidence) * decay.
        """
        adj: dict[str, list[tuple[str, float, str]]] = {}
        parent_map: dict[str, str] = {}

        for e in direct_edges:
            adj.setdefault(e.parent_resource, []).append((e.child_resource, e.confidence, e.via_param))
            parent_map[e.child_resource] = e.parent_resource

        transitive: list[OwnershipEdge] = []
        seen: set[str] = set()

        def dfs(start: str, current: str, chain_confidence: float, chain_via: list[str]) -> None:
            for child, conf, via in adj.get(current, []):
                new_conf = chain_confidence * (conf * confidence_decay)
                via_chain = chain_via + [via]
                key = f"{start}->{child}"
                if key not in seen and child != start:
                    seen.add(key)
                    transitive.append(
                        OwnershipEdge(
                            parent_resource=start,
                            child_resource=child,
                            confidence=round(new_conf, 4),
                            via_param=" → ".join(via_chain),
                            evidence=[
                                f"Transitive ownership via {chain_via[-1] if chain_via else '?'} → {via}",
                                f"Found {len(chain_via) + 1}-hop relationship",
                            ],
                        )
                    )
                    if child in adj:
                        dfs(start, child, new_conf, via_chain)

        for root in adj:
            dfs(root, root, 1.0, [])

        transitive.sort(key=lambda e: e.confidence, reverse=True)
        return transitive

    # ── Internal ──────────────────────────────────────────────────

    @staticmethod
    def _path_template(path: str) -> str:
        return PATH_PARAM_PATTERN.sub("{param}", path)

    def _infer_relationship(
        self, endpoint: EndpointInfo, template: str, other: EndpointInfo
    ) -> EndpointRelationship | None:
        other_template = self._path_template(other.path)

        # Parent/child: endpoint is parent of other (other starts with endpoint/)
        if self._is_parent(endpoint.path, other.path) and template != other_template:
            return EndpointRelationship(
                source_path=endpoint.path,
                target_path=other.path,
                relationship_type="parent_child",
                confidence=0.9,
                evidence=[f"{endpoint.path} is a parent resource of {other.path}"],
            )

        # Parent/child: endpoint is child of other (other is the parent)
        if self._is_parent(other.path, endpoint.path) and template != other_template:
            return EndpointRelationship(
                source_path=endpoint.path,
                target_path=other.path,
                relationship_type="parent_child",
                confidence=0.9,
                evidence=[f"{other.path} is the parent resource of {endpoint.path}"],
            )

        # Sibling: same parent prefix, same depth
        if self._is_sibling(endpoint.path, other.path):
            return EndpointRelationship(
                source_path=endpoint.path,
                target_path=other.path,
                relationship_type="sibling",
                confidence=0.5,
                evidence=[f"Same parent path and depth: {endpoint.path} ↔ {other.path}"],
            )

        # Nested resource: different templates but one is nested under the other
        if template != other_template and (
            self._is_parent(endpoint.path, other.path) or self._is_parent(other.path, endpoint.path)
        ):
            return EndpointRelationship(
                source_path=endpoint.path,
                target_path=other.path,
                relationship_type="nested_resource",
                confidence=0.7,
                evidence=[f"Nested path relationship between {endpoint.path} and {other.path}"],
            )

        return None

    @staticmethod
    def _is_parent(potential_parent: str, potential_child: str) -> bool:
        return potential_child.startswith(potential_parent + "/")

    @staticmethod
    def _is_sibling(path_a: str, path_b: str) -> bool:
        if path_a == path_b:
            return False
        parent_a = path_a.rsplit("/", 1)[0] if "/" in path_a else ""
        parent_b = path_b.rsplit("/", 1)[0] if "/" in path_b else ""
        if parent_a != parent_b:
            return False
        depth_a = len([p for p in path_a.split("/") if p])
        depth_b = len([p for p in path_b.split("/") if p])
        return depth_a == depth_b

    @staticmethod
    def _abstract_pattern(path: str) -> str:
        """Normalize path to its abstract structure: replace all literal segments with a marker.

        /api/users/{id} → /_/_/{param}
        /api/orders/{id} → /_/_/{param}
        """
        segments = path.strip("/").split("/")
        abstract = []
        for s in segments:
            if PATH_PARAM_PATTERN.match(s):
                abstract.append("{param}")
            else:
                abstract.append("_")
        return "/" + "/".join(abstract)

    @staticmethod
    def normalize_endpoints(raw_endpoints: list[dict[str, Any]]) -> list[EndpointInfo]:
        return [
            EndpointInfo(
                path=e.get("path", ""),
                method=e.get("method", "GET"),
                params=e.get("params", {}),
                host=e.get("host", ""),
            )
            for e in raw_endpoints
        ]
