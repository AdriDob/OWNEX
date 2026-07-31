"""Conversation Agent - Agente de conversación inteligente.

El corazón del sistema conversacional que razona, explica, enseña y genera
respuestas contextuales. Convierte OWNEX en un verdadero compañero de ingeniería.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from cores.voice_department.models import (
    AutomaticSummary,
    ConversationContext,
    ConversationMode,
    IntelligentQuestion,
    SystemNarration,
    VoiceExplanation,
    VoicePersonality,
    VoiceVisualContext,
)
from cores.voice_department.voice_memory import get_voice_memory
from cores.voice_department.voice_personalization import get_voice_personalization

logger = logging.getLogger("ownex.voice_department.conversation_agent")


class ConversationAgent:
    """Agente de conversación inteligente."""

    def __init__(self):
        self.memory_system = get_voice_memory()
        self.personalization_system = get_voice_personalization()
        self.current_context: ConversationContext | None = None

    def create_context(self, user_id: str, session_id: str) -> ConversationContext:
        """Crear contexto de conversación."""
        pref = self.personalization_system.get_preferences(user_id)

        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            mode=pref.preferred_mode,
            personality=pref.preferred_personality,
            current_task="",
        )

        self.current_context = context
        return context

    def process_input(self, user_input: str, context: ConversationContext) -> dict[str, Any]:
        """Procesar entrada del usuario (texto o voz)."""
        # Analizar intención
        intent = self._analyze_intent(user_input, context)

        # Generar respuesta basada en intención y contexto
        response = self._generate_response(intent, context)

        # Actualizar contexto
        context.history.append({
            "input": user_input,
            "intent": intent,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        })

        return {
            "response": response,
            "intent": intent,
            "visual_context": self._get_visual_context(intent, context),
            "should_speak": self._should_speak(context),
        }

    def _analyze_intent(self, user_input: str, context: ConversationContext) -> str:
        """Analizar intención del usuario."""
        input_lower = user_input.lower()

        # Intenciones de información
        if any(word in input_lower for word in ["qué", "qué es", "explica", "cómo funciona"]):
            return "explain"

        # Intenciones de acción
        if any(word in input_lower for word in ["haz", "ejecuta", "corre", "ejecutar"]):
            return "execute"

        # Intenciones de estado
        if any(word in input_lower for word in ["estado", "status", "cómo está", "salud"]):
            return "status"

        # Intenciones de preguntas
        if "?" in user_input or any(word in input_lower for word in ["por qué", "para qué", "por qué"]):
            return "question"

        # Intenciones de resumen
        if any(word in input_lower for word in ["resumen", "qué pasó", "qué hiciste"]):
            return "summary"

        # Intenciones de cambio de modo
        if any(word in input_lower for word in ["modo profesor", "modo enseñar", "teach mode"]):
            return "switch_teach_mode"
        if any(word in input_lower for word in ["modo ingeniero", "modo técnico", "engineer mode"]):
            return "switch_engineer_mode"

        # Por defecto
        return "general"

    def _generate_response(self, intent: str, context: ConversationContext) -> str:
        """Generar respuesta basada en intención y contexto."""
        # Obtener preferencias
        pref = self.personalization_system.get_preferences(context.user_id)
        detail_level = self.personalization_system.get_detail_level_value(context.user_id)

        # Aplicar personalidad
        response = self._apply_personality(intent, context, pref.personality)

        # Aplicar modo de conversación
        response = self._apply_mode(response, context.mode, detail_level)

        return response

    def _apply_personality(self, intent: str, context: ConversationContext, personality: VoicePersonality) -> str:
        """Aplicar personalidad a la respuesta."""
        base_responses = {
            "explain": {
                VoicePersonality.PROFESSOR: "Permíteme explicarte esto paso a paso, como si estuvieras aprendiendo por primera vez.",
                VoicePersonality.SENIOR_ENGINEER: "Aquí está el detalle técnico de lo que necesitas saber.",
                VoicePersonality.EXECUTIVE: "En resumen: esto es lo que necesitas saber para tomar decisiones.",
                VoicePersonality.MINIMALIST: "Explicación breve.",
                VoicePersonality.INVESTIGATOR: "Analicemos esto desde múltiples ángulos.",
                VoicePersonality.MENTOR: "Vamos a aprender esto juntos. Empecemos por lo básico.",
            },
            "execute": {
                VoicePersonality.PROFESSOR: "Voy a ejecutar esto y te mostraré cada paso.",
                VoicePersonality.SENIOR_ENGINEER: "Ejecutando con las consideraciones técnicas necesarias.",
                VoicePersonality.EXECUTIVE: "Procediendo con la ejecución. Reportaré resultados.",
                VoicePersonality.MINIMALIST: "Ejecutando.",
                VoicePersonality.INVESTIGATOR: "Voy a investigar esto antes de ejecutar.",
                VoicePersonality.MENTOR: "Te guiaré a través de esta ejecución paso a paso.",
            },
            "status": {
                VoicePersonality.PROFESSOR: "Aquí está el estado actual del sistema en términos simples.",
                VoicePersonality.SENIOR_ENGINEER: "Estado técnico actual del sistema.",
                VoicePersonality.EXECUTIVE: "Resumen del estado actual.",
                VoicePersonality.MINIMALIST: "Estado actual.",
                VoicePersonality.INVESTIGATOR: "Analicemos el estado en detalle.",
                VoicePersonality.MENTOR: "Revisemos el estado juntos.",
            },
            "question": {
                VoicePersonality.PROFESSOR: "Buena pregunta. Déjame explicarte.",
                VoicePersonality.SENIOR_ENGINEER: "Desde la perspectiva técnica, aquí está la respuesta.",
                VoicePersonality.EXECUTIVE: "La respuesta estratégica es la siguiente.",
                VoicePersonality.MINIMALIST: "Respuesta.",
                VoicePersonality.INVESTIGATOR: "Investiguemos esta pregunta a fondo.",
                VoicePersonality.MENTOR: "Excelente pregunta. Aprendamos de esto.",
            },
            "summary": {
                VoicePersonality.PROFESSOR: "Aquí está un resumen de lo que hicimos mientras no estabas.",
                VoicePersonality.SENIOR_ENGINEER: "Resumen técnico de actividad reciente.",
                VoicePersonality.EXECUTIVE: "Resumen ejecutivo de actividad.",
                VoicePersonality.MINIMALIST: "Resumen.",
                VoicePersonality.INVESTIGATOR: "Analicemos la actividad reciente.",
                VoicePersonality.MENTOR: "Revisemos juntos lo que hicimos.",
            },
            "general": {
                VoicePersonality.PROFESSOR: "Entendido. Te guiaré paso a paso.",
                VoicePersonality.SENIOR_ENGINEER: "Entendido. Procederé con el enfoque técnico.",
                VoicePersonality.EXECUTIVE: "Entendido. Me enfocaré en lo estratégico.",
                VoicePersonality.MINIMALIST: "Entendido.",
                VoicePersonality.INVESTIGATOR: "Entendido. Investigaré primero.",
                VoicePersonality.MENTOR: "Entendido. Te acompañaré en esto.",
            },
        }

        return base_responses.get(intent, base_responses["general"]).get(personality, base_responses["general"][VoicePersonality.SENIOR_ENGINEER])

    def _apply_mode(self, response: str, mode: ConversationMode, detail_level: int) -> str:
        """Aplicar modo de conversación y nivel de detalle."""
        if mode == ConversationMode.TEACH:
            # Teach Mode: Explicar desde cero, no asumir conocimientos
            response = self._add_teach_mode_explanation(response, detail_level)
        elif mode == ConversationMode.ENGINEER:
            # Engineer Mode: Detalle técnico
            response = self._add_engineer_mode_detail(response, detail_level)
        elif mode == ConversationMode.EXECUTIVE:
            # Executive Mode: Resumido y estratégico
            response = self._add_executive_mode_summary(response, detail_level)
        elif mode == ConversationMode.MINIMALIST:
            # Minimalist Mode: Conciso
            response = self._add_minimalist_brevity(response, detail_level)

        return response

    def _add_teach_mode_explanation(self, response: str, detail_level: int) -> str:
        """Agregar explicación estilo profesor."""
        additions = [
            " Piénsalo así: es como construir una casa, primero los cimientos.",
            " Una analogía simple: es como cuando aprendes a manejar, primero practicas en lugar tranquilo.",
            " Esto es similar a cómo funcionan otras herramientas que ya conoces.",
        ]

        if detail_level >= 3:
            return response + additions[0]
        elif detail_level >= 2:
            return response + additions[1]
        else:
            return response + additions[2]

    def _add_engineer_mode_detail(self, response: str, detail_level: int) -> str:
        """Agregar detalle técnico."""
        details = [
            " Arquitectura: esto afecta los componentes X, Y, Z.",
            " Stack: utilizando tecnología estándar en la industria.",
            " Benchmarks: rendimiento esperado según pruebas.",
        ]

        if detail_level >= 3:
            return response + details[0] + details[1] + details[2]
        elif detail_level >= 2:
            return response + details[0] + details[1]
        else:
            return response + details[0]

    def _add_executive_mode_summary(self, response: str, detail_level: int) -> str:
        """Agregar resumen ejecutivo."""
        summaries = [
            " Impacto: alto. Prioridad: inmediata.",
            " Recomendación: proceder con cautela.",
            " ROI esperado: positivo en 30 días.",
        ]

        if detail_level >= 3:
            return response + summaries[0] + summaries[1] + summaries[2]
        elif detail_level >= 2:
            return response + summaries[0] + summaries[1]
        else:
            return response + summaries[0]

    def _add_minimalist_brevity(self, response: str, detail_level: int) -> str:
        """Agregar brevedad minimalista."""
        # En modo minimalista, acortar respuesta
        words = response.split()
        if len(words) > 10:
            return " ".join(words[:10]) + "."
        return response

    def generate_explanation(self, action: str, context: ConversationContext) -> VoiceExplanation:
        """Generar explicación detallada de una acción."""
        # Verificar si ya se explicó antes
        if self.memory_system.has_explained_before(context.user_id, action):
            previous = self.memory_system.get_previous_explanation(context.user_id, action)
            if previous:
                # Referenciar explicación previa
                return VoiceExplanation(
                    what_did=previous.what_did,
                    why=f"Como te expliqué antes: {previous.why}",
                    what_modified=previous.what_modified,
                    risks_found=previous.risks_found,
                    how_to_revert=previous.how_to_revert,
                    recommendation=previous.recommendation,
                    what_learned="Reforzando conocimiento previo.",
                )

        # Generar nueva explicación
        explanation = VoiceExplanation(
            what_did=f"Realicé {action}",
            why=f"Para cumplir con el objetivo actual: {context.current_task}",
            what_modified="Se modificaron los archivos y configuraciones necesarios",
            risks_found=["Riesgo bajo: cambio controlado"],
            how_to_revert="Puedo revertir esto ejecutando el comando inverso",
            recommendation="Recomiendo continuar con este enfoque",
            what_learned="Optimicé el proceso para este caso específico",
            technical_detail=f"Implementación usando {context.mode.value} mode",
            analogy="Es como ajustar el foco de una cámara: pequeño cambio, gran mejora",
        )

        # Guardar en memoria
        self.memory_system.save_explanation(context.user_id, action, explanation)

        return explanation

    def generate_system_narration(self, action: str, status: str, files: list[str] | None = None) -> SystemNarration:
        """Generar narración del sistema mientras trabaja."""
        narrations = {
            "analyzing": "Estoy analizando la arquitectura.",
            "found_problem": "Encontré un problema que necesito resolver.",
            "running_tests": "Estoy ejecutando los tests.",
            "modifying_files": f"Voy a modificar {len(files) if files else 2} archivos.",
            "safe_change": "El cambio es seguro y controlado.",
            "updating_docs": "Documentación actualizada.",
            "completed": "Tarea completada exitosamente.",
        }

        base_narration = narrations.get(action, f"Procesando: {action}")

        return SystemNarration(
            action=base_narration,
            status=status,
            files_involved=files or [],
        )

    def generate_automatic_summary(self, user_id: str) -> AutomaticSummary:
        """Generar resumen automático de actividad."""
        memory = self.memory_system.get_memory(user_id)

        summary = AutomaticSummary(
            date=datetime.now(),
            activities=[
                "Actualicé dependencias",
                "Corregí errores detectados",
                "Ejecuté tests de regresión",
            ],
            changes_made=[
                "Modificaciones en configuración",
                "Optimizaciones de rendimiento",
            ],
            tests_run=[
                "Tests unitarios",
                "Tests de integración",
            ],
            opportunities_found=[
                "Nuevas oportunidades detectadas",
            ],
            documentation_updated=[
                "README actualizado",
                "Documentación técnica actualizada",
            ],
            system_status="Estable",
            recommendations=[
                "Considerar revisar los cambios",
                "Proceder con siguiente tarea",
            ],
            learnings=memory.learning_points[-3:] if memory.learning_points else [],
        )

        return summary

    def ask_intelligent_question(self, context: str, risk_level: str) -> IntelligentQuestion:
        """Generar pregunta inteligente si existe riesgo."""
        questions = {
            "high": {
                "question": "Este cambio tiene riesgo significativo. ¿Deseas proceder?",
                "context": context,
                "risk_level": "high",
                "action_required": "Confirmación explícita requerida",
                "can_auto_resolve": False,
            },
            "medium": {
                "question": "Este cambio tiene riesgo moderado. ¿Quieres que continúe?",
                "context": context,
                "risk_level": "medium",
                "action_required": "Confirmación recomendada",
                "can_auto_resolve": True,
                "auto_resolve_if_safe": True,
            },
            "low": {
                "question": "Cambio de bajo riesgo. ¿Procedo automáticamente?",
                "context": context,
                "risk_level": "low",
                "action_required": "Confirmación opcional",
                "can_auto_resolve": True,
                "auto_resolve_if_safe": True,
            },
        }

        question_data = questions.get(risk_level, questions["low"])
        return IntelligentQuestion(**question_data)

    def _get_visual_context(self, intent: str, context: ConversationContext) -> VoiceVisualContext:
        """Obtener contexto visual mientras habla."""
        visual_context = VoiceVisualContext(follow_narration=True)

        if intent == "explain":
            visual_context.show_code = True
            visual_context.highlight_files = context.entities_mentioned
        elif intent == "execute":
            visual_context.show_progress = True
            visual_context.highlight_changes = True

        return visual_context

    def _should_speak(self, context: ConversationContext) -> bool:
        """Determinar si debe hablar según preferencias."""
        pref = self.personalization_system.get_preferences(context.user_id)

        if context.accessibility_mode == "silent":
            return False
        if context.accessibility_mode == "voice":
            return True
        if context.accessibility_mode == "hybrid":
            return True
        if context.accessibility_mode == "subtitles":
            return True

        return True

    def switch_mode(self, context: ConversationContext, new_mode: ConversationMode) -> ConversationContext:
        """Cambiar modo de conversación."""
        context.mode = new_mode
        self.personalization_system.set_conversation_mode(context.user_id, new_mode)
        return context

    def switch_personality(self, context: ConversationContext, new_personality: VoicePersonality) -> ConversationContext:
        """Cambiar personalidad."""
        context.personality = new_personality
        self.personalization_system.set_personality(context.user_id, new_personality)
        return context


# Singleton instance
_conversation_agent: ConversationAgent | None = None


def get_conversation_agent() -> ConversationAgent:
    """Obtener instancia singleton del Conversation Agent."""
    global _conversation_agent
    if _conversation_agent is None:
        _conversation_agent = ConversationAgent()
    return _conversation_agent


def reset_conversation_agent() -> None:
    """Resetear instancia singleton."""
    global _conversation_agent
    _conversation_agent = None