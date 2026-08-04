"""Voice Engine - Motor de orquestación de voz.

Orquesta el pipeline completo de voz: micrófono → wake word → recognition →
intent → conversation planner → task planner → OWNEX brain → agents →
response builder → voice synthesizer → audio output.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from cores.voice_department.conversation_agent import get_conversation_agent
from cores.voice_department.models import (
    AutomaticSummary,
    ConversationContext,
    SystemNarration,
)
from cores.voice_department.voice_personalization import get_voice_personalization

logger = logging.getLogger("ownex.voice_department.engine")


class VoiceEngine:
    """Motor de orquestación de voz."""

    def __init__(self):
        self.conversation_agent = get_conversation_agent()
        self.personalization_system = get_voice_personalization()
        self.is_listening = False
        self.current_context: ConversationContext | None = None

    async def start_listening(self, user_id: str, session_id: str) -> ConversationContext:
        """Iniciar escucha continua."""
        self.current_context = self.conversation_agent.create_context(user_id, session_id)
        self.is_listening = True

        logger.info(f"Voice Engine started listening for user {user_id}")

        return self.current_context

    async def stop_listening(self) -> None:
        """Detener escucha continua."""
        self.is_listening = False
        logger.info("Voice Engine stopped listening")

    async def process_voice_input(self, audio_data: bytes, context: ConversationContext) -> dict[str, Any]:
        """Procesar entrada de voz (pipeline completo)."""
        # Paso 1: Speech Recognition (STT)
        transcribed_text = await self._speech_to_text(audio_data, context)

        # Paso 2: Intent Recognition
        intent = self.conversation_agent._analyze_intent(transcribed_text, context)

        # Paso 3: Conversation Planner
        await self._conversation_planner(intent, context)

        # Paso 4: Task Planner (delegar a OWNEX brain)
        task_result = await self._task_planner(intent, context)

        # Paso 5: Response Builder
        response = self.conversation_agent._generate_response(intent, context)

        # Paso 6: Visual Context
        visual_context = self.conversation_agent._get_visual_context(intent, context)

        # Paso 7: Voice Synthesis (TTS)
        audio_output = await self._text_to_speech(response, context)

        return {
            "transcribed_text": transcribed_text,
            "intent": intent,
            "response": response,
            "audio_output": audio_output,
            "visual_context": visual_context,
            "task_result": task_result,
        }

    async def process_text_input(self, text: str, context: ConversationContext) -> dict[str, Any]:
        """Procesar entrada de texto (bypass speech recognition)."""
        # Intent Recognition
        intent = self.conversation_agent._analyze_intent(text, context)

        # Conversation Planner
        await self._conversation_planner(intent, context)

        # Task Planner
        task_result = await self._task_planner(intent, context)

        # Response Builder
        response = self.conversation_agent._generate_response(intent, context)

        # Visual Context
        visual_context = self.conversation_agent._get_visual_context(intent, context)

        # Voice Synthesis (opcional según preferencias)
        should_speak = self.conversation_agent._should_speak(context)
        audio_output = None
        if should_speak:
            audio_output = await self._text_to_speech(response, context)

        return {
            "intent": intent,
            "response": response,
            "audio_output": audio_output,
            "visual_context": visual_context,
            "task_result": task_result,
            "should_speak": should_speak,
        }

    async def _speech_to_text(self, audio_data: bytes, context: ConversationContext) -> str:
        """Speech Recognition (STT)."""
        # Integrar con Whisper existente en cores/voice_interface.py
        # Por ahora, retornar placeholder
        logger.debug("Speech-to-text processing audio data")
        return "Texto transcripción placeholder"

    async def _text_to_speech(self, text: str, context: ConversationContext) -> bytes:
        """Voice Synthesis (TTS)."""
        # Integrar con Piper existente en cores/voice_interface.py
        # Por ahora, retornar placeholder
        logger.debug("Text-to-speech synthesizing text")
        return b"audio_placeholder"

    async def _conversation_planner(self, intent: str, context: ConversationContext) -> dict[str, Any]:
        """Conversation Planner - planifica la respuesta conversacional."""
        # Determinar si necesita explicación detallada
        needs_explanation = intent in ["explain", "question"]
        needs_narration = intent in ["execute", "status"]

        plan = {
            "needs_explanation": needs_explanation,
            "needs_narration": needs_narration,
            "detail_level": self.personalization_system.get_detail_level_value(context.user_id),
            "mode": context.mode.value,
            "personality": context.personality.value,
        }

        return plan

    async def _task_planner(self, intent: str, context: ConversationContext) -> dict[str, Any]:
        """Task Planner - delega a OWNEX brain y agents."""
        # Aquí se integra con:
        # - Mission Control
        # - Terminal
        # - Copilot
        # - CoderAgent
        # - Execution Layer
        # - Workflow Engine
        # - Documentation
        # - Knowledge Graph

        # Por ahora, retornar placeholder
        logger.debug(f"Task planner delegating intent {intent} to OWNEX brain")
        return {
            "intent": intent,
            "delegated_to": "OWNEX brain",
            "status": "pending",
        }

    async def narrate_action(self, action: str, status: str, files: list[str] | None = None) -> SystemNarration:
        """Narrar acción mientras trabaja el sistema."""
        narration = self.conversation_agent.generate_system_narration(action, status, files)

        # Si auto_narrate está activado, sintetizar y hablar
        if self.current_context:
            pref = self.personalization_system.get_preferences(self.current_context.user_id)
            if pref.auto_narrate:
                # Sintetizar y hablar la narración
                await self._text_to_speech(narration.action, self.current_context)
                # Reproducir audio (placeholder)
                logger.info(f"Narrating: {narration.action}")

        return narration

    async def ask_question(self, context: str, risk_level: str) -> dict[str, Any]:
        """Preguntar inteligentemente si existe riesgo."""
        if not self.current_context:
            return {"error": "No active context"}

        question = self.conversation_agent.ask_intelligent_question(context, risk_level)

        # Determinar si debe interrumpir según preferencias
        should_interrupt = self.personalization_system.should_interrupt(self.current_context.user_id, risk_level)

        if should_interrupt:
            # Sintetizar y hacer la pregunta
            await self._text_to_speech(question.question, self.current_context)
            # Reproducir audio (placeholder)
            logger.info(f"Asking: {question.question}")

        return {
            "question": question.question,
            "risk_level": question.risk_level,
            "action_required": question.action_required,
            "can_auto_resolve": question.can_auto_resolve,
            "should_interrupt": should_interrupt,
        }

    async def generate_startup_summary(self, user_id: str) -> dict[str, Any]:
        """Generar resumen automático al iniciar OWNEX."""
        summary = self.conversation_agent.generate_automatic_summary(user_id)

        # Sintetizar y narrar el resumen
        summary_text = self._format_summary_for_speech(summary)
        context = self.conversation_agent.create_context(user_id, f"startup_{datetime.now().timestamp()}")
        audio = await self._text_to_speech(summary_text, context)

        return {
            "summary": summary,
            "summary_text": summary_text,
            "audio": audio,
        }

    def _format_summary_for_speech(self, summary: AutomaticSummary) -> str:
        """Formatear resumen para voz."""
        return f"""
Buenos días.

Mientras no estabas:
{chr(10).join(f"• {activity}" for activity in summary.activities)}

El sistema continúa estable.

¿Deseás revisar los cambios?
        """.strip()

    async def set_mode(self, mode: str) -> None:
        """Cambiar modo de conversación."""
        if not self.current_context:
            return

        from cores.voice_department.models import ConversationMode

        new_mode = ConversationMode(mode)
        self.current_context = self.conversation_agent.switch_mode(self.current_context, new_mode)

        logger.info(f"Switched to {mode} mode")

    async def set_personality(self, personality: str) -> None:
        """Cambiar personalidad."""
        if not self.current_context:
            return

        from cores.voice_department.models import VoicePersonality

        new_personality = VoicePersonality(personality)
        self.current_context = self.conversation_agent.switch_personality(self.current_context, new_personality)

        logger.info(f"Switched to {personality} personality")


# Singleton instance
_voice_engine: VoiceEngine | None = None


def get_voice_engine() -> VoiceEngine:
    """Obtener instancia singleton del Voice Engine."""
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine()
    return _voice_engine


def reset_voice_engine() -> None:
    """Resetear instancia singleton."""
    global _voice_engine
    _voice_engine = None
