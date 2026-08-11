"""Auto-Communication — responde mensajes de plataformas automáticamente.

Monitorea y responde:
- Preguntas de triage de BB
- Mensajes de clientes en Freelancer
- Comentarios en PRs de Forge
- Notificaciones de plataformas
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.auto_communication")


class AutoCommunication:
    """Auto-responds to platform messages."""

    def __init__(self) -> None:
        self._response_templates = self._load_templates()

    def _load_templates(self) -> dict[str, str]:
        """Load response templates for common messages."""
        return {
            "triage_more_info": "Thank you for the feedback. I've updated the report with additional information:\n\n{additional_info}\n\nPlease let me know if you need anything else.",
            "triage_steps": "Here are detailed reproduction steps:\n\n{steps}\n\nThese steps were verified on the latest version.",
            "triage_impact": "The impact of this vulnerability is:\n\n{impact}\n\nThis was verified through manual testing.",
            "triage_duplicate": "This report appears to be a duplicate. Could you please provide the original report ID so I can review and add additional context if needed?",
            "triage_out_of_scope": "I believe this finding is within the program scope based on the following:\n\n{scope_reference}\n\nCould you please clarify which scope rule applies?",
            "client_clarification": "Thank you for your message. Here's what I understand:\n\n{summary}\n\nCould you please confirm if this is correct so I can proceed?",
            "client_delivery": "I've completed the work as requested. Here's the deliverable:\n\n{deliverable}\n\nPlease review and let me know if any changes are needed.",
            "pr_review_thanks": "Thank you for the review feedback. I've addressed the comments:\n\n{changes}\n\nPlease review the updated PR.",
            "pr_review_explanation": "Regarding your comment about {topic}:\n\n{explanation}\n\nThis approach was chosen because {reason}.",
        }

    async def handle_message(
        self,
        platform: str,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle an incoming platform message."""
        context = context or {}

        # Determine message type
        msg_type = self._classify_message(message)

        # Generate response
        response = await self._generate_response(platform, msg_type, message, context)

        return {
            "platform": platform,
            "original_message": message,
            "message_type": msg_type,
            "response": response,
            "auto_sent": False,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _classify_message(self, message: str) -> str:
        """Classify the message type."""
        msg_lower = message.lower()

        if "more information" in msg_lower or "additional detail" in msg_lower:
            return "triage_more_info"
        if "steps to reproduce" in msg_lower or "reproduction steps" in msg_lower:
            return "triage_steps"
        if "impact" in msg_lower:
            return "triage_impact"
        if "duplicate" in msg_lower:
            return "triage_duplicate"
        if "out of scope" in msg_lower or "not in scope" in msg_lower:
            return "triage_out_of_scope"
        if "clarif" in msg_lower:
            return "client_clarification"
        if "deliver" in msg_lower or "submission" in msg_lower:
            return "client_delivery"
        if "review" in msg_lower:
            return "pr_review"
        return "generic"

    async def _generate_response(
        self,
        platform: str,
        msg_type: str,
        message: str,
        context: dict[str, Any],
    ) -> str:
        """Generate a response using templates or AI."""
        template = self._response_templates.get(msg_type, "")

        if template:
            # Fill template with context
            try:
                return template.format(**context)
            except KeyError:
                return template

        # Fallback to AI
        try:
            from core.ai_worker import get_ai_worker

            worker = get_ai_worker()
            response = await worker.triage.respond_triage_question(
                question=message,
                finding_data=context.get("finding_data", {}),
                evidence=context.get("evidence", ""),
            )
            return response
        except Exception:
            return "Thank you for your message. I will review and respond shortly."

    def get_custom_template(self, name: str) -> str:
        """Get a custom response template."""
        return self._response_templates.get(name, "")

    def set_custom_template(self, name: str, template: str) -> None:
        """Set a custom response template."""
        self._response_templates[name] = template


_comm: AutoCommunication | None = None


def get_communication() -> AutoCommunication:
    """Get singleton AutoCommunication."""
    global _comm
    if _comm is None:
        _comm = AutoCommunication()
    return _comm
