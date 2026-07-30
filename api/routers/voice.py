"""Voice Command API Router.

Processes voice commands and integrates with workflow engine.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.voice_interface import VoiceCommand, VoiceCommandParser
from cores.workflow import WorkflowOrchestrator

logger = logging.getLogger("ownex.api.voice")

router = APIRouter(prefix="/voice", tags=["voice"])

# Global instances
_command_parser = VoiceCommandParser()
_workflow_orchestrator = WorkflowOrchestrator()


class VoiceCommandRequest(BaseModel):
    """Voice command request."""

    text: str
    session_id: str | None = None


class VoiceCommandResponse(BaseModel):
    """Voice command response."""

    command: str
    intent: str
    entities: dict[str, Any]
    confidence: float
    success: bool
    message: str
    action_taken: str | None = None


@router.post("/command", response_model=VoiceCommandResponse)
async def process_voice_command(request: VoiceCommandRequest) -> VoiceCommandResponse:
    """Process a voice command."""
    try:
        # Parse voice command
        session_id = request.session_id or "default"
        command = _command_parser.parse(request.text, session_id)

        logger.info(f"[VOICE] Command parsed: {command.intent} (confidence: {command.confidence:.2f})")

        # Execute command based on intent
        result = await execute_command(command)

        return VoiceCommandResponse(
            command=request.text,
            intent=command.intent,
            entities=command.entities,
            confidence=command.confidence,
            success=result["success"],
            message=result["message"],
            action_taken=result.get("action_taken"),
        )

    except Exception as e:
        logger.error(f"[VOICE] Error processing command: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def execute_command(command: VoiceCommand) -> dict[str, Any]:
    """Execute a voice command based on intent."""
    intent = command.intent
    entities = command.entities

    # OWNEX OMEGA specific commands
    if intent == "navigate":
        return await handle_navigate(entities)
    elif intent == "start_workflow":
        return await handle_start_workflow(entities)
    elif intent == "pause_workflow":
        return await handle_pause_workflow(entities)
    elif intent == "resume_workflow":
        return await handle_resume_workflow(entities)
    elif intent == "cancel_workflow":
        return await handle_cancel_workflow(entities)
    elif intent == "activate_agent":
        return await handle_activate_agent(entities)
    elif intent == "pause_agent":
        return await handle_pause_agent(entities)
    elif intent == "get_status":
        return await handle_get_status(entities)
    elif intent == "search":
        return await handle_search(entities)
    elif intent == "set_theme":
        return await handle_set_theme(entities)
    elif intent == "unknown":
        return {
            "success": False,
            "message": f"No entendí el comando: {command.raw_text}",
        }
    else:
        return {
            "success": False,
            "message": f"Comando no implementado: {intent}",
        }


async def handle_navigate(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle navigation commands."""
    # entities may contain 'destination'
    destination = entities.get("destination", "dashboard")
    return {
        "success": True,
        "message": f"Navegando a {destination}",
        "action_taken": f"navigate:{destination}",
    }


async def handle_start_workflow(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle workflow start commands."""
    workflow_type = entities.get("workflow_type", "feature_development")
    feature_name = entities.get("feature_name", "Feature")

    from cores.workflow import create_feature_development_workflow

    workflow_id = create_feature_development_workflow(_workflow_orchestrator, feature_name)
    _workflow_orchestrator.start_workflow(workflow_id)

    return {
        "success": True,
        "message": f"Iniciando workflow de {workflow_type}",
        "action_taken": f"start_workflow:{workflow_id}",
    }


async def handle_pause_workflow(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle workflow pause commands."""
    workflow_id = entities.get("workflow_id")

    if workflow_id:
        _workflow_orchestrator.pause_workflow(workflow_id)
        return {
            "success": True,
            "message": f"Pausando workflow {workflow_id}",
            "action_taken": f"pause_workflow:{workflow_id}",
        }

    return {
        "success": False,
        "message": "Workflow ID no especificado",
    }


async def handle_resume_workflow(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle workflow resume commands."""
    workflow_id = entities.get("workflow_id")

    if workflow_id:
        _workflow_orchestrator.resume_workflow(workflow_id)
        return {
            "success": True,
            "message": f"Reanudando workflow {workflow_id}",
            "action_taken": f"resume_workflow:{workflow_id}",
        }

    return {
        "success": False,
        "message": "Workflow ID no especificado",
    }


async def handle_cancel_workflow(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle workflow cancel commands."""
    workflow_id = entities.get("workflow_id")

    if workflow_id:
        _workflow_orchestrator.cancel_workflow(workflow_id)
        return {
            "success": True,
            "message": f"Cancelando workflow {workflow_id}",
            "action_taken": f"cancel_workflow:{workflow_id}",
        }

    return {
        "success": False,
        "message": "Workflow ID no especificado",
    }


async def handle_activate_agent(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle agent activation commands."""
    agent_id = entities.get("agent_id", "coding")

    return {
        "success": True,
        "message": f"Activando agente {agent_id}",
        "action_taken": f"activate_agent:{agent_id}",
    }


async def handle_pause_agent(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle agent pause commands."""
    agent_id = entities.get("agent_id", "coding")

    return {
        "success": True,
        "message": f"Pausando agente {agent_id}",
        "action_taken": f"pause_agent:{agent_id}",
    }


async def handle_get_status(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle status commands."""
    workflow = _workflow_orchestrator.get_active_workflow()

    if workflow:
        return {
            "success": True,
            "message": f"Workflow activos: {workflow.name} ({workflow.status.value})",
            "action_taken": "status:active",
        }

    return {
        "success": True,
        "message": "No hay workflows activos",
        "action_taken": "status:idle",
    }


async def handle_search(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle search commands."""
    query = entities.get("query", "")

    return {
        "success": True,
        "message": f"Buscando: {query}",
        "action_taken": f"search:{query}",
    }


async def handle_set_theme(entities: dict[str, Any]) -> dict[str, Any]:
    """Handle theme commands."""
    theme = entities.get("theme", "cyber")

    return {
        "success": True,
        "message": f"Cambiando tema a {theme}",
        "action_taken": f"set_theme:{theme}",
    }


@router.get("/status")
async def get_voice_status() -> dict[str, Any]:
    """Get voice interface status."""
    return {
        "enabled": True,
        "stt_provider": "local_whisper",
        "tts_provider": "local_piper",
        "language": "es-ES",
        "wake_word": "ownex",
    }
