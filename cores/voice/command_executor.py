"""Voice Command Executor — bridges voice commands to executors.

Interprets voice commands and routes them to appropriate executors:
- "claim bounty X" → AlgoraExecutor.claim_issue
- "submit PR for bounty X" → AlgoraExecutor.submit_pr
- "check status of bounty X" → AlgoraExecutor.get_bounty
- "start bounty pipeline for X" → BountyPipeline.execute_bounty

Features:
- Command parsing with regex patterns
- Confirmation for critical actions
- Feedback loop integration
- Configurable command mappings
- Comprehensive logging
- Clear voice feedback for errors
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from core.autonomy.bounty_pipeline import BountyPipeline, get_bounty_pipeline
from core.opportunity.executors import get_executors
from cores.opportunity.feedback import FeedbackOutcome, get_feedback_loop

logger = logging.getLogger("ownex.voice.command_executor")


class VoiceCommandType(StrEnum):
    """Types of voice commands."""

    CLAIM_BOUNTY = "claim_bounty"
    SUBMIT_PR = "submit_pr"
    GET_BOUNTY = "get_bounty"
    START_PIPELINE = "start_pipeline"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Result of parsing a voice command."""

    command_type: VoiceCommandType
    raw_text: str
    entities: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    requires_confirmation: bool = False


@dataclass
class CommandExecutionResult:
    """Result of executing a voice command."""

    success: bool
    command_type: VoiceCommandType
    raw_text: str
    message: str
    voice_feedback: str
    data: dict[str, Any] | None = None
    error: str | None = None
    requires_confirmation: bool = False
    executed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class VoiceCommandExecutor:
    """Executes voice commands by routing to appropriate executors."""

    # Command patterns (regex)
    _PATTERNS: dict[VoiceCommandType, list[re.Pattern[str]]] = {
        VoiceCommandType.CLAIM_BOUNTY: [
            re.compile(r"claim\s+(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"reclamar\s+(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"claim\s+issue\s+([a-zA-Z0-9_-]+)", re.IGNORECASE),
        ],
        VoiceCommandType.SUBMIT_PR: [
            re.compile(r"submit\s+(?:pr\s+)?(?:for\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"enviar\s+(?:pr\s+)?(?:para\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"submit\s+pull\s+request\s+(?:for\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
        ],
        VoiceCommandType.GET_BOUNTY: [
            re.compile(r"check\s+(?:status\s+)?(?:of\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"ver\s+(?:estado\s+)?(?:del\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"status\s+(?:of\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
        ],
        VoiceCommandType.START_PIPELINE: [
            re.compile(r"start\s+(?:bounty\s+)?pipeline\s+(?:for\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"iniciar\s+(?:pipeline\s+)?(?:de\s+)?(?:bounty\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
            re.compile(r"execute\s+(?:bounty\s+)?pipeline\s+(?:for\s+)?([a-zA-Z0-9_-]+)", re.IGNORECASE),
        ],
    }

    # Commands that require confirmation
    _CONFIRMATION_REQUIRED: set[VoiceCommandType] = {
        VoiceCommandType.CLAIM_BOUNTY,
        VoiceCommandType.SUBMIT_PR,
        VoiceCommandType.START_PIPELINE,
    }

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the voice command executor."""
        self.config = config or {}
        self.executors = get_executors(self.config)
        self.feedback_loop = get_feedback_loop()
        self.bounty_pipeline: BountyPipeline | None = None
        self._command_history: list[CommandExecutionResult] = []
        self._max_history = 100

    def parse_command(self, text: str) -> ParsedCommand:
        """Parse a voice command into a structured format."""
        text = text.strip()
        if not text:
            return ParsedCommand(
                command_type=VoiceCommandType.UNKNOWN,
                raw_text=text,
                confidence=0.0,
            )

        for cmd_type, patterns in self._PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    entities = {"bounty_id": match.group(1)}
                    # Try to extract additional entities
                    entities.update(self._extract_additional_entities(text))

                    return ParsedCommand(
                        command_type=cmd_type,
                        raw_text=text,
                        entities=entities,
                        confidence=0.9,
                        requires_confirmation=cmd_type in self._CONFIRMATION_REQUIRED,
                    )

        return ParsedCommand(
            command_type=VoiceCommandType.UNKNOWN,
            raw_text=text,
            confidence=0.0,
        )

    def _extract_additional_entities(self, text: str) -> dict[str, Any]:
        """Extract additional entities from command text."""
        entities = {}

        # Extract repo (owner/repo format)
        repo_match = re.search(r"([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)", text)
        if repo_match:
            entities["repo"] = repo_match.group(1)

        # Extract issue number
        issue_match = re.search(r"#(\d+)", text)
        if issue_match:
            entities["issue_number"] = int(issue_match.group(1))

        return entities

    async def execute_command(
        self,
        parsed: ParsedCommand,
        confirmed: bool = False,
    ) -> CommandExecutionResult:
        """Execute a parsed voice command."""
        logger.info(
            "[VOICE-EXECUTOR] Executing command: %s (confirmed=%s)",
            parsed.command_type,
            confirmed,
        )

        # Check confirmation for critical actions
        if parsed.requires_confirmation and not confirmed:
            return CommandExecutionResult(
                success=False,
                command_type=parsed.command_type,
                raw_text=parsed.raw_text,
                message="Confirmación requerida",
                voice_feedback=self._get_confirmation_prompt(parsed),
                requires_confirmation=True,
            )

        # Route to appropriate handler
        try:
            if parsed.command_type == VoiceCommandType.CLAIM_BOUNTY:
                return await self._handle_claim_bounty(parsed)
            elif parsed.command_type == VoiceCommandType.SUBMIT_PR:
                return await self._handle_submit_pr(parsed)
            elif parsed.command_type == VoiceCommandType.GET_BOUNTY:
                return await self._handle_get_bounty(parsed)
            elif parsed.command_type == VoiceCommandType.START_PIPELINE:
                return await self._handle_start_pipeline(parsed)
            else:
                return CommandExecutionResult(
                    success=False,
                    command_type=parsed.command_type,
                    raw_text=parsed.raw_text,
                    message="Comando no reconocido",
                    voice_feedback="No entendí el comando. Por favor reformula.",
                    error="Unknown command type",
                )
        except Exception as e:
            logger.error("[VOICE-EXECUTOR] Error executing command: %s", e)
            return CommandExecutionResult(
                success=False,
                command_type=parsed.command_type,
                raw_text=parsed.raw_text,
                message="Error al ejecutar comando",
                voice_feedback=self._get_error_voice_feedback(str(e)),
                error=str(e),
            )

    async def _handle_claim_bounty(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Handle claim bounty command."""
        bounty_id = parsed.entities.get("bounty_id")
        repo = parsed.entities.get("repo")
        issue_number = parsed.entities.get("issue_number")

        if not bounty_id:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.CLAIM_BOUNTY,
                raw_text=parsed.raw_text,
                message="ID de bounty requerido",
                voice_feedback="Necesito el ID del bounty para reclamarlo.",
                error="Missing bounty_id",
            )

        executor = self.executors.get("algora")
        if not executor:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.CLAIM_BOUNTY,
                raw_text=parsed.raw_text,
                message="Executor Algora no disponible",
                voice_feedback="El executor de Algora no está configurado.",
                error="Algora executor not available",
            )

        # Use defaults if not provided
        repo = repo or "unknown/repo"
        issue_number = issue_number or 1

        result = await executor.execute(
            "claim_issue",
            bounty_id=bounty_id,
            repo=repo,
            issue_number=issue_number,
        )

        # Record feedback
        if result.success:
            self.feedback_loop.record_feedback(
                opportunity_id=bounty_id,
                outcome=FeedbackOutcome.ACCEPTED,
                category="oss",
                platform="algora",
                technology_tags=[],
                reasoning=f"Voice command claim: {parsed.raw_text}",
            )

        execution_result = CommandExecutionResult(
            success=result.success,
            command_type=VoiceCommandType.CLAIM_BOUNTY,
            raw_text=parsed.raw_text,
            message=result.message or ("Bounty reclamado" if result.success else "Falló al reclamar"),
            voice_feedback="Bounty reclamado exitosamente." if result.success else f"Error: {result.error}",
            data=result.data,
            error=result.error,
        )

        self._add_to_history(execution_result)
        return execution_result

    async def _handle_submit_pr(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Handle submit PR command."""
        bounty_id = parsed.entities.get("bounty_id")
        pr_url = parsed.entities.get("pr_url")

        if not bounty_id:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.SUBMIT_PR,
                raw_text=parsed.raw_text,
                message="ID de bounty requerido",
                voice_feedback="Necesito el ID del bounty y la URL del PR.",
                error="Missing bounty_id",
            )

        executor = self.executors.get("algora")
        if not executor:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.SUBMIT_PR,
                raw_text=parsed.raw_text,
                message="Executor Algora no disponible",
                voice_feedback="El executor de Algora no está configurado.",
                error="Algora executor not available",
            )

        # Try to extract PR URL from text if not in entities
        if not pr_url:
            url_match = re.search(r"https?://[^\s]+", parsed.raw_text)
            if url_match:
                pr_url = url_match.group(0)

        if not pr_url:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.SUBMIT_PR,
                raw_text=parsed.raw_text,
                message="URL del PR requerida",
                voice_feedback="Necesito la URL del pull request para enviarlo.",
                error="Missing pr_url",
            )

        result = await executor.execute("submit_pr", bounty_id=bounty_id, pr_url=pr_url)

        # Record feedback
        if result.success:
            self.feedback_loop.record_feedback(
                opportunity_id=bounty_id,
                outcome=FeedbackOutcome.ACCEPTED,
                category="oss",
                platform="algora",
                technology_tags=[],
                reasoning=f"Voice command submit PR: {parsed.raw_text}",
            )

        execution_result = CommandExecutionResult(
            success=result.success,
            command_type=VoiceCommandType.SUBMIT_PR,
            raw_text=parsed.raw_text,
            message=result.message or ("PR enviado" if result.success else "Falló al enviar PR"),
            voice_feedback="Pull request enviado exitosamente." if result.success else f"Error: {result.error}",
            data=result.data,
            error=result.error,
        )

        self._add_to_history(execution_result)
        return execution_result

    async def _handle_get_bounty(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Handle get bounty status command."""
        bounty_id = parsed.entities.get("bounty_id")

        if not bounty_id:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.GET_BOUNTY,
                raw_text=parsed.raw_text,
                message="ID de bounty requerido",
                voice_feedback="Necesito el ID del bounty para consultar su estado.",
                error="Missing bounty_id",
            )

        executor = self.executors.get("algora")
        if not executor:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.GET_BOUNTY,
                raw_text=parsed.raw_text,
                message="Executor Algora no disponible",
                voice_feedback="El executor de Algora no está configurado.",
                error="Algora executor not available",
            )

        result = await executor.execute("get_bounty", bounty_id=bounty_id)

        bounty_data = result.data if result.data else {}
        status = bounty_data.get("status", "unknown")
        reward = bounty_data.get("reward", "0")

        execution_result = CommandExecutionResult(
            success=result.success,
            command_type=VoiceCommandType.GET_BOUNTY,
            raw_text=parsed.raw_text,
            message=f"Estado del bounty {bounty_id}: {status}",
            voice_feedback=f"El bounty {bounty_id} está en estado {status} con recompensa de {reward}.",
            data=bounty_data,
            error=result.error,
        )

        self._add_to_history(execution_result)
        return execution_result

    async def _handle_start_pipeline(self, parsed: ParsedCommand) -> CommandExecutionResult:
        """Handle start bounty pipeline command."""
        bounty_id = parsed.entities.get("bounty_id")
        repo = parsed.entities.get("repo")
        issue_number = parsed.entities.get("issue_number")

        if not bounty_id:
            return CommandExecutionResult(
                success=False,
                command_type=VoiceCommandType.START_PIPELINE,
                raw_text=parsed.raw_text,
                message="ID de bounty requerido",
                voice_feedback="Necesito el ID del bounty para iniciar el pipeline.",
                error="Missing bounty_id",
            )

        # Get or create bounty pipeline
        if not self.bounty_pipeline:
            self.bounty_pipeline = get_bounty_pipeline()

        # Use defaults if not provided
        repo = repo or "unknown/repo"
        issue_number = issue_number or 1
        issue_url = f"https://github.com/{repo}/issues/{issue_number}"
        title = f"Issue #{issue_number}"
        description = ""

        result = await self.bounty_pipeline.execute_bounty(
            bounty_id=bounty_id,
            repo=repo,
            issue_number=issue_number,
            issue_url=issue_url,
            title=title,
            description=description,
        )

        # Record feedback
        if result.success:
            self.feedback_loop.record_feedback(
                opportunity_id=bounty_id,
                outcome=FeedbackOutcome.ACCEPTED,
                category="oss",
                platform="algora",
                technology_tags=[],
                reasoning=f"Voice command pipeline: {parsed.raw_text}",
                estimated_payout=result.issue_analysis.estimated_reward if result.issue_analysis else 0,
            )

        execution_result = CommandExecutionResult(
            success=result.success,
            command_type=VoiceCommandType.START_PIPELINE,
            raw_text=parsed.raw_text,
            message=result.feedback or ("Pipeline ejecutado" if result.success else "Falló el pipeline"),
            voice_feedback=(
                f"Pipeline completado exitosamente en {result.total_duration_seconds:.1f} segundos."
                if result.success
                else f"Error en el pipeline: {result.error}"
            ),
            data={
                "verdict": result.verdict,
                "total_duration_seconds": result.total_duration_seconds,
                "phases": result.phases,
            },
            error=result.error,
        )

        self._add_to_history(execution_result)
        return execution_result

    def _get_confirmation_prompt(self, parsed: ParsedCommand) -> str:
        """Get voice confirmation prompt for a command."""
        prompts = {
            VoiceCommandType.CLAIM_BOUNTY: f"¿Confirmar que quieres reclamar el bounty {parsed.entities.get('bounty_id', '?')}?",
            VoiceCommandType.SUBMIT_PR: f"¿Confirmar que quieres enviar el PR para el bounty {parsed.entities.get('bounty_id', '?')}?",
            VoiceCommandType.START_PIPELINE: f"¿Confirmar que quieres iniciar el pipeline para el bounty {parsed.entities.get('bounty_id', '?')}?",
        }
        return prompts.get(parsed.command_type, "¿Confirmar esta acción?")

    def _get_error_voice_feedback(self, error: str) -> str:
        """Get user-friendly voice feedback for errors."""
        error_lower = error.lower()

        if "token" in error_lower or "auth" in error_lower:
            return "Error de autenticación. Verifica tus credenciales."
        elif "not found" in error_lower or "404" in error_lower:
            return "No encontré el recurso solicitado."
        elif "timeout" in error_lower:
            return "La operación tardó demasiado. Intenta nuevamente."
        elif "permission" in error_lower or "403" in error_lower:
            return "No tienes permiso para realizar esta acción."
        else:
            return "Ocurrió un error. Por favor intenta nuevamente."

    def _add_to_history(self, result: CommandExecutionResult) -> None:
        """Add command execution result to history."""
        self._command_history.append(result)
        if len(self._command_history) > self._max_history:
            self._command_history.pop(0)

        logger.info(
            "[VOICE-EXECUTOR] Command executed: %s, success=%s",
            result.command_type,
            result.success,
        )

    def get_command_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get command execution history."""
        return [r.model_dump() for r in self._command_history[-limit:]]

    def get_available_commands(self) -> list[dict[str, Any]]:
        """Get list of available voice commands."""
        return [
            {
                "command_type": cmd_type.value,
                "patterns": [p.pattern for p in patterns],
                "requires_confirmation": cmd_type in self._CONFIRMATION_REQUIRED,
                "description": self._get_command_description(cmd_type),
            }
            for cmd_type, patterns in self._PATTERNS.items()
        ]

    def _get_command_description(self, cmd_type: VoiceCommandType) -> str:
        """Get description for a command type."""
        descriptions = {
            VoiceCommandType.CLAIM_BOUNTY: "Reclamar un bounty de Algora",
            VoiceCommandType.SUBMIT_PR: "Enviar un pull request para un bounty",
            VoiceCommandType.GET_BOUNTY: "Consultar el estado de un bounty",
            VoiceCommandType.START_PIPELINE: "Iniciar el pipeline completo de bounty",
        }
        return descriptions.get(cmd_type, "Comando desconocido")


# Singleton instance
_global_executor: VoiceCommandExecutor | None = None


def get_voice_command_executor(config: dict[str, Any] | None = None) -> VoiceCommandExecutor:
    """Get singleton instance of voice command executor."""
    global _global_executor
    if _global_executor is None:
        _global_executor = VoiceCommandExecutor(config)
        logger.info("VoiceCommandExecutor initialized")
    return _global_executor


def reset_voice_command_executor() -> None:
    """Reset singleton instance."""
    global _global_executor
    _global_executor = None
