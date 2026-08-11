from __future__ import annotations

import logging
from typing import Any

from core.execution.runtime.integration import ExecutionEventBusBridge
from cores.events.types import Events

logger = logging.getLogger("ownex.execution.kg_bridge")


class ExecutionKGSubscriber:
    """Records every execution into the Knowledge Graph.

    Each execution produces:
    - A WORKFLOW node (if new)
    - Nodes for each capability called
    - Edges connecting workflow → capability
    - A decision node with the execution outcome
    - Learning edges for future optimization
    """

    def __init__(self, bridge: ExecutionEventBusBridge) -> None:
        self._bridge = bridge
        self._kg: Any = None

    def _get_kg(self) -> Any:
        if self._kg is None:
            from core.knowledge.graph import get_knowledge_graph

            self._kg = get_knowledge_graph()
        return self._kg

    def subscribe(self) -> None:
        self._bridge.subscribe_to_execution_events(self._handle_event)

    def _handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        kg = self._get_kg()

        if event_type == Events.EXECUTION_WORKFLOW_STARTED:
            self._record_workflow_start(kg, data)
        elif event_type == Events.EXECUTION_WORKFLOW_COMPLETED:
            self._record_workflow_completed(kg, data)
        elif event_type == Events.EXECUTION_WORKFLOW_FAILED:
            self._record_workflow_failed(kg, data)
        elif event_type == Events.EXECUTION_NODE_STARTED:
            self._record_node_start(kg, data)
        elif event_type == Events.EXECUTION_NODE_COMPLETED:
            self._record_node_completed(kg, data)
        elif event_type == Events.EXECUTION_NODE_FAILED:
            self._record_node_failed(kg, data)

    def _record_workflow_start(self, kg: Any, data: dict[str, Any]) -> None:
        workflow_id = data.get("workflow_id", "")
        execution_id = data.get("execution_id", "")
        if not workflow_id:
            return

        kg.add_node(
            node_type="workflow",
            name=workflow_id,
            properties={
                "execution_id": execution_id,
                "status": "running",
                "source": "execution_runtime",
            },
            source="execution",
        )
        logger.debug("[KG] Recorded workflow start: %s", workflow_id)

    def _record_workflow_completed(self, kg: Any, data: dict[str, Any]) -> None:
        workflow_id = data.get("workflow_id", "")
        execution_id = data.get("execution_id", "")
        if not workflow_id:
            return

        nodes = kg.find_nodes(node_type="workflow", name_pattern=workflow_id, limit=1)
        if nodes:
            kg.decision_node = kg.record_decision(
                {
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "decision": "completed",
                    "confidence": 1.0,
                    "source": "execution_runtime",
                }
            )
        logger.info("[KG] Recorded workflow completion: %s", workflow_id)

    def _record_workflow_failed(self, kg: Any, data: dict[str, Any]) -> None:
        workflow_id = data.get("workflow_id", "")
        error = data.get("error", "unknown")
        if not workflow_id:
            return

        kg.record_decision(
            {
                "workflow_id": workflow_id,
                "decision": "failed",
                "reason": error,
                "confidence": 1.0,
                "source": "execution_runtime",
            }
        )
        logger.info("[KG] Recorded workflow failure: %s (%s)", workflow_id, error)

    def _record_node_start(self, kg: Any, data: dict[str, Any]) -> None:
        node_id = data.get("node_id", "")
        node_type = data.get("node_type", "")
        if not node_id:
            return

        kg.add_node(
            node_type="event",
            name=f"node:{node_id}",
            properties={
                "node_id": node_id,
                "primitive_type": node_type,
                "status": "running",
            },
            source="execution",
        )

    def _record_node_completed(self, kg: Any, data: dict[str, Any]) -> None:
        node_id = data.get("node_id", "")
        if not node_id:
            return

        nodes = kg.find_nodes(node_type="event", name_pattern=f"node:{node_id}", limit=1)
        if nodes:
            kg.add_edge(
                source_id=nodes[0].node_id if hasattr(nodes[0], "node_id") else "",
                target_id=nodes[0].node_id if hasattr(nodes[0], "node_id") else "",
                edge_type="related_to",
                properties={"status": "completed"},
            )

    def _record_node_failed(self, kg: Any, data: dict[str, Any]) -> None:
        node_id = data.get("node_id", "")
        error = data.get("error", "unknown")
        if not node_id:
            return

        nodes = kg.find_nodes(node_type="event", name_pattern=f"node:{node_id}", limit=1)
        if nodes:
            kg.add_edge(
                source_id=nodes[0].node_id if hasattr(nodes[0], "node_id") else "",
                target_id=nodes[0].node_id if hasattr(nodes[0], "node_id") else "",
                edge_type="related_to",
                properties={"status": "failed", "error": error},
            )
