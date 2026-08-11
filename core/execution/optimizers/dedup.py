from __future__ import annotations

from core.execution.compiler import BaseOptimizer, OptimizationLog
from core.execution.models import Workflow
from core.execution.primitives import PrimitiveType


class DedupOptimizer(BaseOptimizer):
    """Deduplicates redundant nodes in the workflow.

    Optimizations:
    - Remove duplicate CAPABILITY nodes with identical config
    - Remove duplicate CHECKPOINT nodes
    - Remove duplicate PERSIST nodes
    """

    name = "dedup"

    def optimize(self, workflow: Workflow, plan=None) -> tuple[Workflow, list[OptimizationLog]]:
        logs: list[OptimizationLog] = []
        node_map = {n.id: n for n in workflow.nodes}

        # ── 1. Dedup identical CAPABILITY calls ──────────────────
        seen_caps: dict[tuple, str] = {}  # (capability, frozen_params) -> node_id
        dup_ids: set[str] = set()

        for node in workflow.nodes:
            if node.type == PrimitiveType.CAPABILITY.value:
                cap_name = node.config.get("capability", "")
                params = node.config.get("params", {})
                # Use a canonical representation
                key = (cap_name, str(sorted(params.items())))
                if key in seen_caps and seen_caps[key] != node.id:
                    dup_ids.add(node.id)
                else:
                    seen_caps[key] = node.id

        if dup_ids:
            for nid in dup_ids:
                n = node_map.get(nid)
                logs.append(
                    OptimizationLog(
                        optimizer=self.name,
                        description=f"Removed duplicate CAPABILITY '{n.label or nid}' "
                        f"(identical to another node with same config)",
                        node_ids_affected=[nid],
                        before=f"duplicate {n.label or nid}",
                        after="removed",
                    )
                )

        # ── 2. Dedup duplicate CHECKPOINT nodes ──────────────────
        checkpoint_ids: list[str] = []
        for node in workflow.nodes:
            if node.type == PrimitiveType.CHECKPOINT.value:
                label = node.config.get("label", "")
                if label and any(node_map[oid].config.get("label") == label for oid in checkpoint_ids):
                    dup_ids.add(node.id)
                else:
                    checkpoint_ids.append(node.id)

        # ── 3. Dedup duplicate PERSIST nodes ─────────────────────
        persist_count = sum(1 for n in workflow.nodes if n.type == PrimitiveType.PERSIST.value)
        if persist_count > 1:
            extra_persists = [n.id for n in workflow.nodes if n.type == PrimitiveType.PERSIST.value][1:]
            dup_ids.update(extra_persists)

        # ── Apply dedup ──────────────────────────────────────────
        if dup_ids:
            kept = [n for n in workflow.nodes if n.id not in dup_ids]
            workflow.edges = [e for e in workflow.edges if e.source_id not in dup_ids and e.target_id not in dup_ids]
            workflow.nodes = kept

        return workflow, logs
