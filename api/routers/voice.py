"""Voice Command API Router.

Processes voice commands, evaluates whether a request is worth the user's time
(income/learning/opportunity reasoning), and bridges real-time audio between
OMEGA (mobile STT) and ALPHA (desktop TTS). All speech APIs are open-source
browser Web Speech (SpeechRecognition / speechSynthesis).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from cores.voice.opportunity_evaluator import OpportunityEvaluator
from cores.voice.voice_engine import VoiceProfile, get_tts_manager, personality
from cores.voice_interface import VoiceCommand, VoiceCommandParser
from cores.workflow import WorkflowOrchestrator

logger = logging.getLogger("ownex.api.voice")

router = APIRouter(prefix="/voice", tags=["voice"])

# Global instances
_command_parser = VoiceCommandParser()
_workflow_orchestrator = WorkflowOrchestrator()
_evaluator = OpportunityEvaluator()

# In-memory reply queue: OMEGA posts, ALPHA polls and speaks.
_reply_lock = threading.Lock()
_reply_seq = 0
_replies: list[dict[str, Any]] = []


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


class AssistantRequest(BaseModel):
    """Request to the intelligent voice assistant (text from OMEGA STT)."""

    text: str
    session_id: str | None = None


class AssistantReply(BaseModel):
    """A reply the ALPHA desktop should speak/display."""

    id: int
    request_text: str
    domain: str
    worth_it: bool
    worth_score: float
    response: str
    reasoning: list[str]
    suggested_action: str
    created_at: str
    voice: str | None = None


class TTSRequest(BaseModel):
    """Request backend TTS synthesis (OWNEX voice, local-first)."""

    text: str


class VoiceConfigUpdate(BaseModel):
    """Partial update of the persisted voice profile."""

    provider: str | None = None
    language: str | None = None
    locale: str | None = None
    speed: float | None = None
    pitch: int | None = None
    volume: float | None = None
    personality: str | None = None
    fallback: str | None = None


@router.post("/assistant")
async def process_assistant(request: AssistantRequest) -> AssistantReply:
    """Evaluate a voice request and queue a reply for the ALPHA desktop."""
    from datetime import UTC, datetime

    evaluation = _evaluator.evaluate(request.text)

    response = _own_voice(_compose_response(evaluation))

    global _reply_seq
    with _reply_lock:
        _reply_seq += 1
        reply = AssistantReply(
            id=_reply_seq,
            request_text=evaluation.request_text,
            domain=evaluation.domain,
            worth_it=evaluation.worth_it,
            worth_score=evaluation.worth_score,
            response=response,
            reasoning=evaluation.reasoning,
            suggested_action=evaluation.suggested_action,
            created_at=datetime.now(UTC).isoformat(),
        )
        _replies.append(reply.model_dump())
        if len(_replies) > 100:
            del _replies[:-100]

    logger.info(
        "[VOICE-ASSISTANT] domain=%s worth=%s score=%.2f request=%r",
        evaluation.domain,
        evaluation.worth_it,
        evaluation.worth_score,
        request.text,
    )
    return reply


@router.get("/assistant/replies")
async def get_assistant_replies(since: int = 0) -> dict[str, Any]:
    """Return replies newer than ``since`` so ALPHA can speak them in real time."""
    with _reply_lock:
        new_replies = [r for r in _replies if r["id"] > since]
    return {"replies": new_replies}


def _compose_response(evaluation) -> str:
    """Compose a natural, speakable response from the evaluation."""
    parts = []
    if evaluation.worth_it:
        parts.append(f"Sí, vale la pena. {evaluation.reasoning[0] if evaluation.reasoning else ''}")
    else:
        parts.append(f"No es una prioridad. {evaluation.reasoning[0] if evaluation.reasoning else ''}")
    parts.append(f"Sugerencia: {evaluation.suggested_action}")
    return " ".join(parts)


def _own_voice(reply_text: str, worth_it: bool | None = None) -> str:
    """Apply the persisted OWNEX voice personality to a reply."""
    return personality().apply(reply_text, worth_it=worth_it)


@router.post("/tts")
async def synthesize_tts(request: TTSRequest) -> Response:
    """Synthesise text with the OWNEX voice (piper local). 415 when unavailable."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="empty text")
    engine = get_tts_manager()
    wav = engine.synthesize(text)
    if wav is None:
        return Response(
            status_code=415,
            media_type="application/json",
            content=b'{"detail": "piper unavailable; use system_tts"}',
        )
    return Response(content=wav, media_type="audio/wav")


@router.get("/config")
async def get_voice_config() -> dict[str, Any]:
    """Return the persisted voice profile."""
    return get_tts_manager().store.get().to_dict()


@router.put("/config")
async def update_voice_config(update: VoiceConfigUpdate) -> dict[str, Any]:
    """Persist a partial voice profile update."""
    store = get_tts_manager().store
    current = store.get()
    changes = {k: v for k, v in update.model_dump().items() if v is not None}
    profile = VoiceProfile.from_dict({**current.to_dict(), **changes})
    store.save(profile)
    return profile.to_dict()


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
    """Get voice interface status (honest provider report)."""
    profile = get_tts_manager().store.get()
    tts = get_tts_manager().provider_status()
    return {
        "enabled": profile.enabled,
        "stt_provider": "capacitor_native" if _capacitor_stt_hint() else "browser_webspeech",
        "tts_provider": tts["active"],
        "piper_available": tts["piper_available"],
        "assistant_endpoint": "/voice/assistant",
        "language": f"{profile.language}-{profile.locale}",
        "locale": profile.locale,
        "speed": profile.speed,
        "personality": profile.personality,
        "wake_word": "ownex",
    }


def _capacitor_stt_hint() -> bool:
    """True when the frontend reports Capacitor native STT (Android APK)."""
    return False
