from __future__ import annotations

from collections import deque

from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType
from core.execution.validation import BaseValidator, ValidationResult


class GraphValidator(BaseValidator):
    """Structural validation of the workflow graph.

    Checks:
    - Exactly one START node
    - At least one END node
    - All nodes reachable from START
    - No orphan nodes (every node has at least one connection)
    - No cycles
    - No dead branches (conditions with no true/false targets)
    - No disconnected subgraphs
    """

    name = "graph"

    def validate(self, workflow: Workflow) -> ValidationResult:
        result = ValidationResult(validator_name=self.name)

        node_map = {n.id: n for n in workflow.nodes}
        node_ids = set(node_map.keys())

        if not node_ids:
            result.errors.append(self._error("GRAPH_EMPTY", "Workflow has no nodes"))
            result.passed = False
            return result

        # ── Build adjacency list ─────────────────────────────────
        adjacency: dict[str, list[str]] = {nid: [] for nid in node_ids}
        edge_map: dict[str, list[str]] = {nid: [] for nid in node_ids}  # reverse: incoming edges

        for edge in workflow.edges:
            if edge.source_id in adjacency:
                adjacency[edge.source_id].append(edge.target_id)
            if edge.target_id in edge_map:
                edge_map[edge.target_id].append(edge.source_id)

        # ── 1. Exactly one START ─────────────────────────────────
        start_nodes = [n for n in workflow.nodes if n.type == PrimitiveType.START.value]
        if len(start_nodes) == 0:
            result.errors.append(self._error("GRAPH_NO_START", "Workflow must have exactly one START node"))
            result.passed = False
        elif len(start_nodes) > 1:
            for sn in start_nodes[1:]:
                result.errors.append(self._error("GRAPH_MULTI_START", "Multiple START nodes found", node_id=sn.id))
            result.passed = False

        # ── 2. At least one END ──────────────────────────────────
        end_nodes = [n for n in workflow.nodes if n.type == PrimitiveType.END.value]
        if len(end_nodes) == 0:
            result.errors.append(self._error("GRAPH_NO_END", "Workflow must have at least one END node"))
            result.passed = False

        # ── 3. Reachability from START ───────────────────────────
        start_id = start_nodes[0].id if start_nodes else None
        if start_id:
            reachable = self._bfs(adjacency, start_id)
            unreachable = node_ids - reachable
            for nid in sorted(unreachable):
                node = node_map[nid]
                result.warnings.append(
                    self._warning(
                        "GRAPH_UNREACHABLE",
                        f"Node '{node.label or nid}' is not reachable from START",
                        node_id=nid,
                    )
                )

        # ── 4. Orphan nodes ──────────────────────────────────────
        connected: set[str] = set()
        for edge in workflow.edges:
            connected.add(edge.source_id)
            connected.add(edge.target_id)
        orphans = node_ids - connected
        for nid in sorted(orphans):
            node = node_map[nid]
            result.warnings.append(
                self._warning(
                    "GRAPH_ORPHAN",
                    f"Node '{node.label or nid}' has no edges (orphan)",
                    node_id=nid,
                )
            )

        # ── 5. Cycle detection ───────────────────────────────────
        cycle_nodes = self._find_cycles(adjacency)
        for nid in cycle_nodes:
            node = node_map[nid]
            result.errors.append(
                self._error(
                    "GRAPH_CYCLE",
                    f"Cycle detected involving node '{node.label or nid}'",
                    node_id=nid,
                )
            )
            result.passed = False

        # ── 6. Condition nodes with no true/false path ───────────
        for node in workflow.nodes:
            if node.type == PrimitiveType.CONDITION.value:
                out_edges = [e for e in workflow.edges if e.source_id == node.id]
                if not out_edges:
                    result.warnings.append(
                        self._warning(
                            "GRAPH_CONDITION_NO_EDGE",
                            f"Condition node '{node.label or node.id}' has no outgoing edges",
                            node_id=node.id,
                        )
                    )

        # ── 7. Disconnected subgraphs ────────────────────────────
        if start_id:
            all_reachable = self._bfs(adjacency, start_id)
            # Also find nodes reachable in reverse from END nodes
            end_reachable: set[str] = set()
            for end_node in end_nodes:
                end_reachable |= self._bfs(edge_map, end_node.id)
            combined = all_reachable | end_reachable
            disconnected = node_ids - combined - orphans
            for nid in sorted(disconnected):
                node = node_map[nid]
                result.warnings.append(
                    self._warning(
                        "GRAPH_DISCONNECTED",
                        f"Node '{node.label or nid}' is in a disconnected subgraph",
                        node_id=nid,
                    )
                )

        return result

    @staticmethod
    def _bfs(adjacency: dict[str, list[str]], start: str) -> set[str]:
        """BFS traversal returning all reachable nodes."""
        visited: set[str] = set()
        queue: deque[str] = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        return visited

    @staticmethod
    def _find_cycles(adjacency: dict[str, list[str]]) -> set[str]:
        """DFS-based cycle detection.

        Returns the set of node IDs that are part of at least one cycle.
        """
        white, gray, black = 0, 1, 2
        color: dict[str, int] = {n: white for n in adjacency}
        in_cycle: set[str] = set()

        def dfs(node: str) -> bool:
            color[node] = gray
            for neighbor in adjacency.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == gray:
                    in_cycle.add(node)
                    in_cycle.add(neighbor)
                    return True
                if color[neighbor] == white and dfs(neighbor):
                    in_cycle.add(node)
                    return True
            color[node] = black
            return False

        for node in adjacency:
            if color[node] == white:
                dfs(node)

        return in_cycle
