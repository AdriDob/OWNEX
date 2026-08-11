from __future__ import annotations

from core.copilot.permissions import AuthorityLevel
from core.execution.compiler import BaseOptimizer, OptimizationLog
from core.execution.models import Node, Workflow
from core.execution.primitives import PrimitiveType

# ── Authority level ordering ──────────────────────────────────────
AUTHORITY_ORDER = [lv.value for lv in AuthorityLevel]


class ApprovalOptimizer(BaseOptimizer):
    """Optimizes approval and rollback nodes in the workflow.

    Optimizations:
    - Merge consecutive APPROVAL nodes (keep the highest required_level)
    - Detect redundant approvals (same level within short range)
    - Suggest rollback consolidation
    """

    name = "approval"

    def optimize(self, workflow: Workflow, plan=None) -> tuple[Workflow, list[OptimizationLog]]:
        logs: list[OptimizationLog] = []
        node_map = {n.id: n for n in workflow.nodes}
        adjacency: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
        incoming: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}

        for edge in workflow.edges:
            if edge.source_id in adjacency:
                adjacency[edge.source_id].append(edge.target_id)
            if edge.target_id in incoming:
                incoming[edge.target_id].append(edge.source_id)

        # ── 1. Merge consecutive APPROVAL nodes ─────────────────
        merged_ids: set[str] = set()
        new_nodes: list[Node] = []

        for node in workflow.nodes:
            if node.id in merged_ids:
                continue

            if node.type != PrimitiveType.APPROVAL.value:
                new_nodes.append(node)
                continue

            # Walk the chain of consecutive approvals
            chain = [node]
            targets = list(adjacency.get(node.id, []))
            while targets:
                nid = targets.pop(0)
                if nid in merged_ids:
                    continue
                n = node_map.get(nid)
                if not n or n.type != PrimitiveType.APPROVAL.value:
                    continue
                chain.append(n)
                merged_ids.add(nid)
                targets.extend(adjacency.get(nid, []))

            if len(chain) > 1:
                # Merge: keep the highest authority level required
                levels = [self._level_index(n.config.get("required_level", "operator")) for n in chain]
                max_idx = max(levels)
                best = AUTHORITY_ORDER[max_idx]

                # Keep the first node, update its config
                lead = chain[0]
                original_levels = [n.config.get("required_level", "?") for n in chain]
                lead.config["required_level"] = best
                lead.config["reason"] = "; ".join(filter(None, [n.config.get("reason", "") for n in chain]))

                logs.append(
                    OptimizationLog(
                        optimizer=self.name,
                        description=f"Merged {len(chain)} consecutive approvals into one (required_level={best})",
                        node_ids_affected=[n.id for n in chain],
                        before=f"levels={original_levels}",
                        after=f"level={best} (merged)",
                    )
                )

            new_nodes.append(chain[0])

        # ── 2. Remove edges that pointed into merged approvals ──
        workflow.edges = [e for e in workflow.edges if e.target_id not in merged_ids or e.source_id not in merged_ids]

        # Rewire edges: any edge targeting a merged approval should
        # target the first node in its chain instead
        workflow.nodes = new_nodes

        # ── 3. Suggest rollback consolidation ────────────────────
        rollback_nodes = [n for n in workflow.nodes if n.type == PrimitiveType.ROLLBACK.value]
        if len(rollback_nodes) > 1:
            logs.append(
                OptimizationLog(
                    optimizer=self.name,
                    description=f"Found {len(rollback_nodes)} rollback nodes — "
                    f"consider consolidating into a single rollback with checkpoint restore",
                    node_ids_affected=[n.id for n in rollback_nodes],
                    before=f"{len(rollback_nodes)} separate rollbacks",
                    after="potential single rollback",
                )
            )

        return workflow, logs

    @staticmethod
    def _level_index(level: str) -> int:
        try:
            return AUTHORITY_ORDER.index(level)
        except ValueError:
            return AUTHORITY_ORDER.index("operator")
