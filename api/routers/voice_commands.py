"""Voice Commands API Router — executes voice commands via executors.

Endpoints:
- POST /api/voice/command — execute a voice command from text
- POST /api/voice/commands/audio — transcribe an audio blob and execute the command
- POST /api/voice/command/confirm — confirm and execute a pending command
- GET /api/voice/commands/history — view command execution history
- GET /api/voice/commands/available — list available voice commands
- GET /api/voice/commands/health — STT/TTS/player health with honest fallbacks
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from cores.voice.command_executor import (
    CommandExecutionResult,
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


class VoiceAudioCommandResponse(VoiceCommandResponse):
    """Audio-in result: the text response plus what the local STT actually heard."""

    transcript: str
    language: str | None = None
    model_size: str
    audio_bytes: int


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
        result = await _run_command(request.text, confirmed=request.confirmed)
        return _to_response(result)

    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error executing command: %s", e)
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}") from e


@router.post("/audio", response_model=VoiceAudioCommandResponse)
async def execute_voice_audio(
    audio: UploadFile = File(..., description="Audio blob recorded by the dashboard (wav/webm/ogg/m4a)"),
    language: str | None = Form(None, description="ISO hint (es, en); auto-detected when omitted"),
    model_size: str | None = Form(None, description="faster-whisper size; the STT layer default when omitted"),
    confirmed: bool = Form(False, description="Whether the user already confirmed the action"),
) -> VoiceAudioCommandResponse:
    """Transcribe an uploaded audio blob locally, then execute the command it contains.

    One call performs the whole round-trip the dashboard needs:
    audio → local Whisper → command executor → same payload as ``/command``,
    plus the transcript so the UI can show what was heard.
    """
    payload = await audio.read()
    if not payload:
        raise HTTPException(status_code=422, detail="empty audio")

    resolved_model = model_size or _default_stt_model()
    suffix = Path(audio.filename or "command.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(prefix="ownex_stt_", suffix=suffix, delete=False) as handle:
        handle.write(payload)
        audio_path = Path(handle.name)
    try:
        transcript = _transcribe(audio_path, resolved_model, language)
    finally:
        audio_path.unlink(missing_ok=True)

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="could not transcribe the audio (local STT unavailable)",
        )

    try:
        result = await _run_command(transcript, confirmed=confirmed)
    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error executing transcribed command: %s", e)
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}") from e

    logger.info(
        "[VOICE-COMMANDS] audio=%dB language=%s transcript=%r -> %s",
        len(payload),
        language,
        transcript,
        result.command_type.value,
    )
    return VoiceAudioCommandResponse(
        **_to_response(result).model_dump(),
        transcript=transcript,
        language=language,
        model_size=resolved_model,
        audio_bytes=len(payload),
    )


async def _run_command(text: str, *, confirmed: bool = False) -> CommandExecutionResult:
    """Parse and execute one command — shared by the text and audio endpoints."""
    executor = _get_executor()
    parsed = executor.parse_command(text)
    logger.info(
        "[VOICE-COMMANDS] Parsed command: %s (confidence=%.2f, requires_confirmation=%s)",
        parsed.command_type,
        parsed.confidence,
        parsed.requires_confirmation,
    )
    return await executor.execute_command(parsed, confirmed=confirmed)


def _to_response(result: CommandExecutionResult) -> VoiceCommandResponse:
    """Map an executor result onto the API payload."""
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


def _default_stt_model() -> str:
    """STT layer default model size (single source of truth lives there)."""
    from cores.cycles.voice_commands import DEFAULT_MODEL_SIZE

    return DEFAULT_MODEL_SIZE


def _transcribe(path: Path, model_size: str, language: str | None) -> str | None:
    """Run local STT; imported lazily so the router never pulls Whisper at boot."""
    from cores.cycles.voice_commands import transcribe_audio

    return transcribe_audio(path, model_size=model_size, language=language)


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


@router.get("/health")
async def get_voice_health() -> dict[str, Any]:
    """Health of the local voice stack: STT, TTS and audio player.

    Each component reports whether it is usable, why, and what happens
    instead when it is not, so the dashboard never assumes a silent fallback.
    """
    try:
        from cores.cycles.voice_commands import voice_stack_health

        return voice_stack_health()

    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error checking voice health: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to check voice health: {str(e)}") from e


@router.get("/status")
async def get_executor_status() -> dict[str, Any]:
    """Get voice command executor status."""
    try:
        from cores.cycles.voice_commands import voice_stack_health

        executor = _get_executor()
        history = executor.get_command_history(limit=1)

        return {
            "initialized": True,
            "executors_available": list(executor.executors.keys()),
            "bounty_pipeline_available": executor.bounty_pipeline is not None,
            "total_commands_executed": len(executor._command_history),
            "last_command": history[0] if history else None,
            # STT / TTS / player availability with the honest fallback per component.
            "voice_stack": voice_stack_health(),
        }

    except Exception as e:
        logger.error("[VOICE-COMMANDS] Error getting status: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}") from e
