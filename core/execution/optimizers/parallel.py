from __future__ import annotations

from collections import deque

from core.execution.compiler import BaseOptimizer, OptimizationLog
from core.execution.models import Edge, Node, Workflow
from core.execution.primitives import PrimitiveType


class ParallelOptimizer(BaseOptimizer):
    """Detects sequential branches that can execute in parallel.

    Strategy:
    1. Find a CAPABILITY node whose outgoing edges fan out to multiple
       CAPABILITY nodes with no data dependency between them.
    2. Group those branches into a PARALLEL node group.
    3. Insert a MERGE node after the parallel group.

    This is conservative: only applies when branches are truly independent
    (no shared variables, no sequential dependency chain).
    """

    name = "parallel"

    def optimize(self, workflow: Workflow, plan=None) -> tuple[Workflow, list[OptimizationLog]]:
        logs: list[OptimizationLog] = []
        node_map = {n.id: n for n in workflow.nodes}

        # ── Build adjacency ──────────────────────────────────────
        adjacency: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
        incoming: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
        for edge in workflow.edges:
            if edge.source_id in adjacency:
                adjacency[edge.source_id].append(edge.target_id)
            if edge.target_id in incoming:
                incoming[edge.target_id].append(edge.source_id)

        # ── Find fan-out points ─────────────────────────────────
        for node in workflow.nodes:
            targets = adjacency.get(node.id, [])
            if len(targets) < 2:
                continue

            # All targets must be CAPABILITY nodes
            cap_targets = [t for t in targets if t in node_map and node_map[t].type == PrimitiveType.CAPABILITY.value]
            if len(cap_targets) < 2:
                continue

            # Check independence: no target is an ancestor of another
            if self._has_interdependency(cap_targets, adjacency):
                continue

            # Check no shared output variable names (indicates data dependency)
            if self._has_shared_outputs(cap_targets, node_map):
                continue

            # ── Create parallel group ────────────────────────────
            merge_id = f"merge_{node.id[:8]}"
            branch_ids = list(cap_targets)

            # Insert a MERGE node after the parallel group
            merge_node = Node(
                id=merge_id,
                type="merge",
                label=f"Merge ({len(branch_ids)} branches)",
                config={"branches": branch_ids},
            )

            # Find the common successor (the node all branches lead to)
            common_succ = self._find_common_successor(branch_ids, adjacency)

            # Create edges: node → each branch → merge → common successor
            new_edges: list[Edge] = []
            for br_id in branch_ids:
                new_edges.append(Edge(source_id=node.id, target_id=br_id, label="parallel"))
                new_edges.append(Edge(source_id=br_id, target_id=merge_id))

            if common_succ:
                new_edges.append(Edge(source_id=merge_id, target_id=common_succ))

            # Remove old edges from node to each branch target and from targets to common_succ
            old_edge_ids: set[str] = set()
            for edge in workflow.edges:
                if edge.source_id == node.id and edge.target_id in branch_ids:
                    old_edge_ids.add(edge.id)
                if edge.target_id == common_succ and edge.source_id in branch_ids:
                    old_edge_ids.add(edge.id)

            workflow.edges = [e for e in workflow.edges if e.id not in old_edge_ids]
            workflow.edges.extend(new_edges)
            workflow.nodes.append(merge_node)

            logs.append(
                OptimizationLog(
                    optimizer=self.name,
                    description=f"Parallelized {len(branch_ids)} independent branches "
                    f"after node '{node.label or node.id}'",
                    node_ids_affected=[node.id] + branch_ids + [merge_id],
                    before=f"sequential chain of {len(branch_ids)} capability calls",
                    after=f"parallel execution of {len(branch_ids)} branches + merge",
                )
            )

        return workflow, logs

    @staticmethod
    def _has_interdependency(targets: list[str], adjacency: dict[str, list[str]]) -> bool:
        """Check if any target node can reach another via graph edges."""
        for src in targets:
            visited: set[str] = set()
            queue: deque[str] = deque([src])
            while queue:
                nid = queue.popleft()
                if nid in visited:
                    continue
                visited.add(nid)
                if nid != src and nid in targets:
                    return True
                for nxt in adjacency.get(nid, []):
                    if nxt not in visited:
                        queue.append(nxt)
        return False

    @staticmethod
    def _has_shared_outputs(branch_ids: list[str], node_map: dict[str, Node]) -> bool:
        """Check if branches write to the same output variable."""
        seen: set[str] = set()
        for nid in branch_ids:
            node = node_map.get(nid)
            if not node:
                continue
            for out_key in node.output_mapping.values():
                if out_key in seen:
                    return True
                seen.add(out_key)
        return False

    @staticmethod
    def _find_common_successor(branch_ids: list[str], adjacency: dict[str, list[str]]) -> str | None:
        """Find the single common successor node across all branches."""
        succ_sets: list[set[str]] = []
        for nid in branch_ids:
            succs = set(adjacency.get(nid, []))
            if succs:
                succ_sets.append(succs)

        if not succ_sets:
            return None

        common = succ_sets[0]
        for s in succ_sets[1:]:
            common &= s

        return next(iter(common)) if len(common) == 1 else None
