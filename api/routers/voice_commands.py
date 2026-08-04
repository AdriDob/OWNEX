"""Voice Commands API Router — executes voice commands via executors.

Endpoints:
- POST /api/voice/command — execute a voice command
- POST /api/voice/command/confirm — confirm and execute a pending command
- GET /api/voice/commands/history — view command execution history
- GET /api/voice/commands/available — list available voice commands
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.voice.command_executor import (
    ParsedCommand,
    VoiceCommandExecutor,
    get_voice_command_executor,
)

logger = logging.getLogger("ownex.api.voice_commands")

router = APIRouter(prefix="/api/voice/commands", tags=["voice-commands"])

# Global executor instance
_executor: VoiceCommandExecutor | None = None


def _get_executor() -> VoiceCommandExecutor:
    """Get or create executor instance."""
    global _executor
    if _executor is None:
        _executor = get_voice_command_executor()
    return _executor


class VoiceCommandRequest(BaseModel):
    """Request to execute a voice command."""

    text: str = Field(..., description="Voice command text")
    session_id: str | None = Field(None, description="Optional session ID")
    confirmed: bool = Field(False, description="Whether user confirmed the action")


class VoiceCommandResponse(BaseModel):
    """Response from voice command execution."""

    success: bool
    command_type: str
    raw_text: str
    message: str
    voice_feedback: str
    data: dict[str, Any] | None = None
    error: str | None = None
    requires_confirmation: bool = False
    executed_at: str


class ConfirmationRequest(BaseModel):
    """Request to confirm a pending command."""

    command_type: str = Field(..., description="Type of command to confirm")
    raw_text: str = Field(..., description="Original command text")
    entities: dict[str, Any] = Field(default_factory=dict, description="Extracted entities")


class HistoryResponse(BaseModel):
    """Response with command history."""

    commands: list[dict[str, Any]]
    total: int


class AvailableCommandsResponse(BaseModel):
    """Response with available commands."""

    commands: list[dict[str, Any]]
    total: int


@router.post("/command", response_model=VoiceCommandResponse)
async def execute_voice_command(request: VoiceCommandRequest) -> VoiceCommandResponse:
    """Execute a voice command.

    This endpoint:
    1. Parses the voice command text
    2. Checks if confirmation is required
    3. Executes the command (if confirmed or no confirmation needed)
    4. Returns the result with voice feedback
    """
    try:
        executor = _get_executor()

        # Parse the command
        parsed = executor.parse_command(request.text)

        logger.info(
            "[VOICE-COMMANDS] Parsed command: %s (confidence=%.2f, requires_confirmation=%s)",
            parsed.command_type,
            parsed.confidence,
            parsed.requires_confirmation,
        )

        # Execute the command
        result = await executor.execute_command(parsed, confirmed=request.confirmed)

        return VoiceCommandResponse(
            success=result.success,
            command_type=result.command_type.value,
            raw_text=result.raw_text,
            message=result.message,
            voice_feedback=result.voice_feedback,
            data=result.data,
            error=result.error,
            requires_confirmation=result.requires_confirmation,
            executed_at=result.executed_at,
        )

    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error executing command: %s", e)
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}") from e


@router.post("/command/confirm", response_model=VoiceCommandResponse)
async def confirm_voice_command(request: ConfirmationRequest) -> VoiceCommandResponse:
    """Confirm and execute a pending voice command.

    Use this when a command requires confirmation. The user should call
    this endpoint after being prompted for confirmation.
    """
    try:
        executor = _get_executor()

        # Reconstruct the parsed command
        from cores.voice.command_executor import VoiceCommandType

        command_type = VoiceCommandType(request.command_type)
        parsed = ParsedCommand(
            command_type=command_type,
            raw_text=request.raw_text,
            entities=request.entities,
            confidence=0.9,
            requires_confirmation=False,  # Already confirmed
        )

        # Execute with confirmed=True
        result = await executor.execute_command(parsed, confirmed=True)

        return VoiceCommandResponse(
            success=result.success,
            command_type=result.command_type.value,
            raw_text=result.raw_text,
            message=result.message,
            voice_feedback=result.voice_feedback,
            data=result.data,
            error=result.error,
            requires_confirmation=False,
            executed_at=result.executed_at,
        )

    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error confirming command: %s", e)
        raise HTTPException(status_code=500, detail=f"Command confirmation failed: {str(e)}") from e


@router.get("/history", response_model=HistoryResponse)
async def get_command_history(limit: int = 50) -> HistoryResponse:
    """Get voice command execution history.

    Returns the last N executed commands with their results.
    """
    try:
        executor = _get_executor()
        history = executor.get_command_history(limit=limit)

        return HistoryResponse(commands=history, total=len(history))

    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error getting history: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}") from e


@router.get("/available", response_model=AvailableCommandsResponse)
async def get_available_commands() -> AvailableCommandsResponse:
    """Get list of available voice commands.

    Returns all supported voice command patterns, descriptions,
    and whether they require confirmation.
    """
    try:
        executor = _get_executor()
        commands = executor.get_available_commands()

        return AvailableCommandsResponse(commands=commands, total=len(commands))

    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error getting available commands: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get available commands: {str(e)}") from e


@router.get("/status")
async def get_executor_status() -> dict[str, Any]:
    """Get voice command executor status."""
    try:
        executor = _get_executor()
        history = executor.get_command_history(limit=1)

        return {
            "initialized": True,
            "executors_available": list(executor.executors.keys()),
            "bounty_pipeline_available": executor.bounty_pipeline is not None,
            "total_commands_executed": len(executor._command_history),
            "last_command": history[0] if history else None,
        }

    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error getting status: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}") from e
