from __future__ import annotations

import logging
import os

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.langfuse.connector")

try:
    from langfuse import Langfuse as LangfuseClient

    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False
    LangfuseClient = None  # type: ignore[assignment]


class LangfuseConnector(IConnector):
    """Connector to Langfuse LLM observability platform.

    Traces every LLM call, agent action, and tool execution with
    full observability: latency, cost, prompts, responses, scores.
    Enables prompt versioning, A/B testing, and quality evaluation.
    """

    connector_id = "langfuse_observer"
    app_id = "ownex"
    display_name = "Langfuse LLM Observability"

    def __init__(self) -> None:
        self._connected = False
        self._client: LangfuseClient | None = None

    async def connect(self) -> bool:
        if not _LANGFUSE_AVAILABLE:
            logger.warning("langfuse package not installed")
            return False
        try:
            public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
            secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
            host = os.environ.get("LANGFUSE_HOST", "http://localhost:3000")

            if not public_key or not secret_key:
                logger.warning("LANGFUSE keys not fully set — tracing disabled")
                return False

            self._client = LangfuseClient(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
            self._connected = True
            logger.info("Langfuse connected at %s", host)
            return True
        except Exception as exc:
            logger.error("Langfuse connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._client = None
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connected=self._connected,
            error=None if self._connected else "not initialized",
        )

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "langfuse_public_key", "label": "Langfuse Public Key", "type": "text"},
            {"key": "langfuse_secret_key", "label": "Langfuse Secret Key", "type": "password"},
            {
                "key": "langfuse_host",
                "label": "Langfuse Host",
                "type": "text",
                "default": "http://localhost:3000",
            },
        ]

    def trace(self, name: str, metadata: dict | None = None) -> object | None:
        """Start a new trace for an agent operation."""
        if not self._client:
            return None
        try:
            return self._client.trace(name=name, metadata=metadata or {})
        except Exception as exc:
            logger.error("Langfuse trace failed: %s", exc)
            return None

    def score(self, trace_id: str, name: str, value: float) -> bool:
        """Score a trace (quality evaluation)."""
        if not self._client:
            return False
        try:
            self._client.score(trace_id=trace_id, name=name, value=value)
            return True
        except Exception as exc:
            logger.error("Langfuse score failed: %s", exc)
            return False


async def on_llm_call(event: object) -> None:
    if not _LANGFUSE_AVAILABLE:
        return
    connector = LangfuseConnector()
    if not await connector.connect():
        return
    trace_name = getattr(event, "trace_name", "llm_call")
    connector.trace(trace_name)


async def on_agent_action(event: object) -> None:
    if not _LANGFUSE_AVAILABLE:
        return
    connector = LangfuseConnector()
    if not await connector.connect():
        return
    trace_name = getattr(event, "action", "agent_action")
    connector.trace(trace_name)


async def on_evaluation_score(event: object) -> None:
    if not _LANGFUSE_AVAILABLE:
        return
    connector = LangfuseConnector()
    if not await connector.connect():
        return
    trace_id = getattr(event, "trace_id", "")
    score_name = getattr(event, "score_name", "quality")
    score_value = getattr(event, "score_value", 0.0)
    if trace_id:
        connector.score(trace_id, score_name, score_value)
