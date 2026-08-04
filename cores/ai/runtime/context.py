"""OAR Context Manager — Cross-provider context handling."""

from __future__ import annotations

import logging
from typing import Any

from .interfaces import AIRequest, OARConfig, get_config

logger = logging.getLogger("oar.context")


class ContextManager:
    """Manages conversation context across providers with intelligent truncation."""

    def __init__(self, config: OARConfig | None = None):
        self._config = config or get_config()
        self._contexts: dict[str, list[dict[str, str]]] = {}  # session_id -> messages
        self._summaries: dict[str, str] = {}  # session_id -> summary

    def get_context(self, session_id: str, max_tokens: int = 4096) -> list[dict[str, str]]:
        """Get context for a session, truncated to fit max_tokens."""
        messages = self._contexts.get(session_id, [])
        if not messages:
            return []

        # Estimate tokens (rough: 4 chars = 1 token)
        total_chars = sum(len(m.get("content", "")) for m in messages)
        estimated_tokens = total_chars // 4

        if estimated_tokens <= max_tokens:
            return messages

        # Truncate: keep system message, summary, and recent messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        user_assistant_msgs = [m for m in messages if m.get("role") != "system"]

        # Keep summary if exists
        summary_msg = []
        if session_id in self._summaries:
            summary_msg = [
                {"role": "system", "content": f"Previous conversation summary: {self._summaries[session_id]}"}
            ]

        # Calculate remaining budget for recent messages
        reserved = sum(len(m.get("content", "")) for m in system_msgs + summary_msg) // 4
        available = max_tokens - reserved

        # Take most recent messages that fit
        result = system_msgs + summary_msg
        current_tokens = reserved

        for msg in reversed(user_assistant_msgs):
            msg_tokens = len(msg.get("content", "")) // 4
            if current_tokens + msg_tokens > available:
                break
            result.insert(-len(summary_msg) if summary_msg else len(result), msg)
            current_tokens += msg_tokens

        return result

    def add_message(self, session_id: str, message: dict[str, str]) -> None:
        """Add a message to the session context."""
        if session_id not in self._contexts:
            self._contexts[session_id] = []
        self._contexts[session_id].append(message)

    def add_messages(self, session_id: str, messages: list[dict[str, str]]) -> None:
        """Add multiple messages to the session context."""
        if session_id not in self._contexts:
            self._contexts[session_id] = []
        self._contexts[session_id].extend(messages)

    def clear_context(self, session_id: str) -> None:
        """Clear context for a session."""
        self._contexts.pop(session_id, None)
        self._summaries.pop(session_id, None)

    def set_summary(self, session_id: str, summary: str) -> None:
        """Set conversation summary for a session."""
        self._summaries[session_id] = summary

    def get_summary(self, session_id: str) -> str | None:
        """Get conversation summary for a session."""
        return self._summaries.get(session_id)

    def prepare_request(self, request: AIRequest, session_id: str | None = None) -> AIRequest:
        """Prepare request with context from session."""
        if not session_id:
            return request

        context_messages = self.get_context(session_id, request.max_tokens // 2)

        # Merge context with request messages (avoid duplicates)
        existing_content = {m.get("content", "") for m in request.messages}
        merged = []
        for msg in context_messages:
            if msg.get("content", "") not in existing_content:
                merged.append(msg)
        merged.extend(request.messages)

        return AIRequest(
            messages=merged,
            task_type=request.task_type,
            model=request.model,
            provider=request.provider,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            tools=request.tools,
            tool_choice=request.tool_choice,
            response_format=request.response_format,
            images=request.images,
            metadata={**request.metadata, "session_id": session_id},
        )

    def update_from_response(self, session_id: str, request: AIRequest, response: Any) -> None:
        """Update context with request/response pair."""
        # Add user messages from request
        for msg in request.messages:
            if msg.get("role") == "user":
                self.add_message(session_id, msg)

        # Add assistant response
        if hasattr(response, "content") and response.content:
            self.add_message(session_id, {"role": "assistant", "content": response.content})


# Global context manager instance
_context_manager: ContextManager | None = None


def get_context_manager(config: OARConfig | None = None) -> ContextManager:
    """Get global context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager(config)
    return _context_manager
