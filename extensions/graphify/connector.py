from __future__ import annotations

import logging

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.graphify.connector")

try:
    import graphify

    _GRAPHIFY_AVAILABLE = True
except ImportError:
    _GRAPHIFY_AVAILABLE = False
    logger.warning("graphify not installed — Graphify code intelligence extension disabled")


class GraphifyConnector(IConnector):
    """Connector to Graphify code intelligence.

    Transforms codebases into knowledge graphs using deterministic
    AST parsing. No hallucinations, no vector store — every
    relationship is backed by code structure.
    """

    connector_id = "graphify_code"
    app_id = "ownex"
    display_name = "Graphify Code KG"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        if not _GRAPHIFY_AVAILABLE:
            logger.warning("graphify not installed")
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return []

    async def analyze(self, repo_path: str, output_dir: str | None = None) -> dict:
        """Analyze a codebase and build its knowledge graph."""
        if not _GRAPHIFY_AVAILABLE:
            return {"error": "graphify not installed"}
        try:
            result = graphify.analyze(
                repo_path=repo_path,
                output_dir=output_dir or f"{repo_path}/.graphify",
            )
            return {"status": "ok", "graph_path": str(result) if result else ""}
        except Exception as exc:
            logger.error("Graphify analyze failed: %s", exc)
            return {"error": str(exc)}

    async def search(self, query: str, graph_dir: str) -> list[dict]:
        """Search the code knowledge graph."""
        if not _GRAPHIFY_AVAILABLE:
            return []
        try:
            results = graphify.search(graph_dir=graph_dir, query=query)
            return results if isinstance(results, list) else []
        except Exception as exc:
            logger.error("Graphify search failed: %s", exc)
            return []

    async def get_context(self, file_path: str, graph_dir: str) -> dict:
        """Get context for a specific file from the knowledge graph."""
        if not _GRAPHIFY_AVAILABLE:
            return {"error": "graphify not installed"}
        try:
            result = graphify.get_context(file_path=file_path, graph_dir=graph_dir)
            return result if isinstance(result, dict) else {"error": "invalid result format"}
        except Exception as exc:
            logger.error("Graphify get_context failed: %s", exc)
            return {"error": str(exc)}

    async def export(self, graph_dir: str, format: str = "json") -> dict:
        """Export the knowledge graph in the specified format."""
        if not _GRAPHIFY_AVAILABLE:
            return {"error": "graphify not installed"}
        try:
            result = graphify.export(graph_dir=graph_dir, format=format)
            return {"status": "ok", "file_path": str(result) if result else ""}
        except Exception as exc:
            logger.error("Graphify export failed: %s", exc)
            return {"error": str(exc)}
