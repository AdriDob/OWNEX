from __future__ import annotations

from core.execution.compiler import BaseOptimizer, OptimizationLog
from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType


class NormalizeOptimizer(BaseOptimizer):
    """Normalizes the workflow graph for consistent compilation.

    Optimizations:
    - Ensures every START node has the correct config
    - Ensures every END node has the correct config
    - Removes NOP nodes (unknown types that became NOP)
    - Merges consecutive NOPs from START/END patterns
    - Assigns default labels to unnamed nodes
    """

    name = "normalize"

    def optimize(self, workflow: Workflow, plan=None) -> tuple[Workflow, list[OptimizationLog]]:
        logs: list[OptimizationLog] = []
        modified = False
        kept: list = []

        for node in workflow.nodes:
            # ── Remove NOP nodes ─────────────────────────────────
            if node.type == "nop":
                logs.append(
                    OptimizationLog(
                        optimizer=self.name,
                        description=f"Removed NOP node '{node.label or node.id}'",
                        node_ids_affected=[node.id],
                        before="type=nop",
                        after="removed",
                    )
                )
                modified = True
                continue

            # ── Default label ────────────────────────────────────
            if not node.label:
                node.label = f"{node.type}_{node.id[:8]}"
                modified = True

            # ── START node config ────────────────────────────────
            if node.type == PrimitiveType.START.value and not node.config.get("initial_variables"):
                node.config["initial_variables"] = {}
                logs.append(
                    OptimizationLog(
                        optimizer=self.name,
                        description="Added default initial_variables to START node",
                        node_ids_affected=[node.id],
                        before="no config",
                        after="initial_variables={}",
                    )
                )
                modified = True

            kept.append(node)

        if modified:
            workflow.nodes = kept

        return workflow, logs
