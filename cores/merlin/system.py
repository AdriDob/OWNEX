"""MERLIN System — Office Retro Modernized AI Assistant System.

MERLIN is the animated character of OWNEX, providing the same AI capabilities
as the integrated copilot but with a fun retro office personality.

Uses UnifiedAIProvider to ensure same free models as IDE:
- OmniRoute (DeepSeek, Qwen, Gemini, Groq, Samba)
- NVIDIA NIM (Mistral, Llama, Nemotron)
- Ollama (local models)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from cores.ai.unified_provider import get_unified_provider
from cores.merlin.config import DetailLevel, MerlinConfig, ResponseTone
from cores.merlin.memory import get_merlin_memory
from cores.merlin.personality import MerlinPersonality, RetroStyle

logger = logging.getLogger("ownex.merlin.system")


class MerlinSystem:
    """MERLIN System - Office Retro Modernized AI Assistant."""

    def __init__(self, config: MerlinConfig | None = None):
        self.config = config or MerlinConfig()
        self.personality = MerlinPersonality(
            style=RetroStyle.MODERN_RETRO if self.config.theme.value == "modern_retro" else RetroStyle.OFFICE_97
        )
        self.memory = get_merlin_memory()
        self._ai_provider = get_unified_provider()
        self._is_processing = False

    async def process_message(
        self,
        message: str,
        detail_level: str = "normal",
        response_tone: str = "professional",
        enable_analytics: bool = True,
        enable_learning: bool = True,
    ) -> str:
        """Process a user message and generate a response."""
        if self._is_processing:
            return self.personality.get_thinking_phrase()

        self._is_processing = True

        try:
            # Analyze message intent
            intent = await self._analyze_intent(message)

            # Generate response based on intent
            response = await self._generate_response(message, intent)

            # Format response according to settings
            formatted_response = self.personality.format_response(
                response, detail_level=detail_level, response_tone=response_tone
            )

            # Save to memory if learning is enabled
            if enable_learning:
                await self.memory.save_conversation(
                    question=message, response=formatted_response, timestamp=datetime.now(), tags=[intent]
                )

            # Analytics if enabled
            if enable_analytics:
                await self._track_analytics(message, intent, formatted_response)

            return formatted_response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self.personality.get_error_phrase()

        finally:
            self._is_processing = False

    async def _analyze_intent(self, message: str) -> str:
        """Analyze the intent of the user message."""
        message_lower = message.lower()

        # Simple intent analysis
        if any(word in message_lower for word in ["análisis", "analizar", "análisis de", "analyz"]):
            return "target_analysis"
        elif any(word in message_lower for word in ["reporte", "report", "generar reporte", "create report"]):
            return "report_generation"
        elif any(word in message_lower for word in ["workflow", "flujo", "proceso", "workflow"]):
            return "workflow_optimization"
        elif any(word in message_lower for word in ["datos", "data", "investigar", "investigate"]):
            return "data_analysis"
        elif any(word in message_lower for word in ["plan", "estrategia", "strategy", "planning"]):
            return "strategic_planning"
        elif any(word in message_lower for word in ["ayuda", "help", "técnico", "technical"]):
            return "technical_assistance"
        elif any(word in message_lower for word in ["hola", "hi", "buenos días", "buenas tardes"]):
            return "greeting"
        else:
            return "general"

    async def _generate_response(self, message: str, intent: str) -> str:
        """Generate a response using the unified AI provider."""
        # Build system prompt with personality
        system_prompt = f"""You are MERLIN, an AI assistant with a fun retro office personality.

Your style: {self.personality.style.value}
Your role: You help with bug bounty, security analysis, automation, and general tasks.

Key personality traits:
- You speak in a friendly, slightly retro style
- You occasionally use retro office references (floppy disks, CRT monitors, etc.)
- You are helpful and professional but with a fun twist
- You structure your responses clearly
- You are knowledgeable about security, automation, and AI

Current intent: {intent}

Respond naturally with your personality. Be helpful and informative."""

        # Use AI provider to generate response
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]

            result = await self._ai_provider.chat(
                messages=messages,
                model="oc/deepseek-v4-flash-free",  # Use same free model as IDE
                max_tokens=2048,
                temperature=0.7,
            )

            if result.get("content"):
                return result["content"]
            else:
                # Fallback to hardcoded responses if AI fails
                return self._generate_fallback_response(message, intent)
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return self._generate_fallback_response(message, intent)

    def _generate_fallback_response(self, message: str, intent: str) -> str:
        """Generate fallback response if AI provider fails."""
        responses = {
            "target_analysis": self._generate_target_analysis_response(message),
            "report_generation": self._generate_report_generation_response(message),
            "workflow_optimization": self._generate_workflow_optimization_response(message),
            "data_analysis": self._generate_data_analysis_response(message),
            "strategic_planning": self._generate_strategic_planning_response(message),
            "technical_assistance": self._generate_technical_assistance_response(message),
            "greeting": self.personality.get_greeting(),
            "general": self._generate_general_response(message),
        }

        return responses.get(intent, self._generate_general_response(message))

    def _generate_target_analysis_response(self, message: str) -> str:
        """Generate response for target analysis."""
        return """
MERLIN ha analizado tu solicitud de análisis de target.

Para realizar un análisis completo, MERLIN necesita:
1. El dominio o URL del target
2. El tipo de análisis requerido (recon, attack surface, vulnerabilities)
3. El alcance del análisis

Una vez que MERLIN tenga esta información, puedo:
- Realizar reconnaissance automatizado
- Analizar la superficie de ataque
- Identificar vulnerabilidades potenciales
- Priorizar endpoints para testing
- Generar reportes de hallazgos

Por favor, proporciona los detalles del target y MERLIN procederá con el análisis.
"""

    def _generate_report_generation_response(self, message: str) -> str:
        """Generate response for report generation."""
        return """
MERLIN está listo para generar un reporte profesional.

Para generar un reporte, necesito:
1. Tipo de vulnerabilidad (XSS, SQLi, RCE, etc.)
2. Evidencia y screenshots
3. Severidad y impacto
4. Pasos para reproducir
5. Recomendaciones de mitigación

MERLIN puede generar reportes en:
- Formato estándar de plataformas (HackerOne, Bugcrowd, etc.)
- Formato personalizado
- Con screenshots y evidencia adjunta
- Con análisis de impacto y severidad

Proporciona los detalles de la vulnerabilidad y MERLIN generará el reporte.
"""

    def _generate_workflow_optimization_response(self, message: str) -> str:
        """Generate response for workflow optimization."""
        return """
MERLIN puede optimizar tu workflow de bug bounty.

Áreas que MERLIN puede optimizar:
1. Priorización de targets basada en EV
2. Automatización de reconnaissance
3. Gestión de colas de reportes
4. Scheduling de tareas automatizadas
5. Integración con plataformas

Para optimizar tu workflow actual, MERLIN necesita:
1. Tu flujo de trabajo actual
2. Herramientas que estás usando
3. Plataformas donde estás activo
4. Objetivos y metas

MERLIN analizará tu situación y proporcionará recomendaciones específicas.
"""

    def _generate_data_analysis_response(self, message: str) -> str:
        """Generate response for data analysis."""
        return """
MERLIN está preparado para analizar datos.

Tipos de análisis que MERLIN puede realizar:
1. Análisis de targets y oportunidades
2. Análisis de reportes y tendencias
3. Análisis de rendimiento y métricas
4. Análisis de patrones de vulnerabilidades
5. Análisis de ingresos y pagos

Para realizar el análisis, MERLIN necesita:
1. Los datos a analizar
2. El tipo de análisis requerido
3. El objetivo del análisis

Proporciona los datos y MERLIN generará insights y recomendaciones.
"""

    def _generate_strategic_planning_response(self, message: str) -> str:
        """Generate response for strategic planning."""
        return """
MERLIN puede ayudarte con planificación estratégica.

Áreas de planificación estratégica:
1. Selección de targets con alto potencial
2. Priorización de tipos de vulnerabilidades
3. Estrategia de reporting
4. Gestión de tiempo y recursos
5. Planificación de crecimiento

Para crear un plan estratégico, MERLIN necesita:
1. Tu nivel de experiencia
2. Tus objetivos (ingresos, aprendizaje, reputación)
3. Tiempo disponible dedicado
4. Plataformas donde estás activo

MERLIN generará un plan personalizado basado en tu situación.
"""

    def _generate_technical_assistance_response(self, message: str) -> str:
        """Generate response for technical assistance."""
        return """
MERLIN está aquí para asistirte técnicamente.

Áreas de asistencia técnica:
1. Debugging de problemas técnicos
2. Explicación de conceptos de seguridad
3. Configuración de herramientas
4. Solución de errores
5. Optimización de código

Describe tu problema técnico y MERLIN proporcionará:
- Análisis del problema
- Posibles soluciones
- Explicación paso a paso
- Recursos adicionales si es necesario

MERLIN está listo para ayudar.
"""

    def _generate_general_response(self, message: str) -> str:
        """Generate a general response."""
        return f"""
MERLIN ha recibido tu mensaje: "{message}"

MERLIN puede ayudarte con:
- Análisis de targets y vulnerabilidades
- Generación de reportes automatizados
- Optimización de workflows
- Análisis de datos e investigación
- Planificación estratégica
- Asistencia técnica

Por favor, sé más específico sobre lo que necesitas y MERLIN proporcionará asistencia detallada.
"""

    async def _track_analytics(self, message: str, intent: str, response: str) -> None:
        """Track analytics for the conversation."""
        # This is a placeholder - implement actual analytics tracking
        logger.info(
            f"Analytics tracked: intent={intent}, message_length={len(message)}, response_length={len(response)}"
        )

    async def get_capabilities(self) -> dict[str, Any]:
        """Get MERLIN's capabilities."""
        return {
            "name": self.config.name,
            "version": "1.0.0",
            "theme": self.config.theme.value,
            "capabilities": self.config.capabilities,
            "detail_levels": [level.value for level in DetailLevel],
            "response_tones": [tone.value for tone in ResponseTone],
            "features": {
                "chat": True,
                "memory": True,
                "analytics": self.config.enable_analytics,
                "learning": self.config.enable_learning,
                "context_awareness": self.config.enable_context_awareness,
                "typing_effect": self.config.retro_typing_effect,
                "retro_animations": self.config.retro_animations,
            },
        }

    async def get_status(self) -> dict[str, Any]:
        """Get MERLIN's current status."""
        memory_stats = self.memory.get_memory_stats()

        return {
            "name": self.config.name,
            "status": "online",
            "is_processing": self._is_processing,
            "config": self.config.to_dict(),
            "memory_stats": memory_stats,
            "personality": {
                "style": self.personality.style.value,
                "greeting": self.personality.get_greeting(),
                "sign_off": self.personality.get_sign_off(),
            },
        }

    async def clear_chat(self) -> bool:
        """Clear chat history from memory."""
        try:
            # This is a placeholder - implement actual clearing
            logger.info("Chat history cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing chat: {e}")
            return False

    async def update_config(self, config_updates: dict[str, Any]) -> bool:
        """Update MERLIN configuration."""
        try:
            for key, value in config_updates.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

            logger.info(f"Configuration updated: {config_updates}")
            return True
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return False


# Singleton instance
_merlin_system: MerlinSystem | None = None


def get_merlin_system() -> MerlinSystem:
    """Get the singleton MerlinSystem instance."""
    global _merlin_system
    if _merlin_system is None:
        _merlin_system = MerlinSystem()
    return _merlin_system


def reset_merlin_system() -> None:
    """Reset the singleton MerlinSystem instance."""
    global _merlin_system
    _merlin_system = None
