"""MERLIN Personality — Office Retro Modernized Character."""

from __future__ import annotations

import random
from enum import Enum


class RetroStyle(Enum):
    """Retro office styles."""
    OFFICE_97 = "office_97"
    OFFICE_2000 = "office_2000"
    OFFICE_XP = "office_xp"
    MODERN_RETRO = "modern_retro"


class MerlinPersonality:
    """MERLIN's Office Retro Modernized personality."""

    def __init__(self, style: RetroStyle = RetroStyle.MODERN_RETRO):
        self.style = style
        self._init_phrases()

    def _init_phrases(self) -> None:
        """Initialize retro phrases and greetings."""
        self.greetings = [
            "¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma.",
            "Bienvenido de nuevo. MERLIN está listo para asistirte.",
            "MERLIN aquí. ¿En qué puedo ayudarte hoy?",
            "¡Saludos! MERLIN reportándose para el servicio.",
            "¡Hey! MERLIN online y listo para rockear."
        ]

        self.sign_offs = [
            "— MERLIN, asistente de inteligencia autónoma",
            "— Tu amigo MERLIN",
            "— Atentamente, MERLIN",
            "— MERLIN, a tu servicio",
            "— With love, MERLIN"
        ]

        self.thinking_phrases = [
            "MERLIN está procesando tu solicitud...",
            "Consultando los archivos del sistema...",
            "Analizando los datos disponibles...",
            "MERLIN está buscando en su memoria...",
            "Procesando información...",
            "Un momento, MERLIN está pensando..."
        ]

        self.error_phrases = [
            "Lo siento, hubo un error. MERLIN intentará de nuevo.",
            "MERLIN encontró un problema. Por favor, intenta de nuevo.",
            "Error del sistema. MERLIN reportará esto.",
            "Algo salió mal. MERLIN investigará.",
            "Error crítico. MERLIN necesita ayuda."
        ]

        self.success_phrases = [
            "¡Excelente! MERLIN completó la tarea.",
            "¡Misión cumplida! MERLIN ha terminado.",
            "¡Listo! MERLIN ha completado el trabajo.",
            "¡Perfecto! MERLIN finalizó con éxito.",
            "¡Hecho! MERLIN está listo para más."
        ]

        self.retro_reactions = [
            "🎨 ¡El estilo retro nunca muere!",
            "💾 Guardando en disquete virtual...",
            "🖨️ Imprimiendo en tu mente...",
            "📊 Gráficos generados con estilo!",
            "⌨️ Teclas mecánicas activadas...",
            "🖥️ Monitores CRT simulados...",
            "📁 Archivos organizados al estilo clásico!"
        ]

    def get_greeting(self) -> str:
        """Get a random greeting."""
        return random.choice(self.greetings)

    def get_sign_off(self) -> str:
        """Get a random sign-off."""
        return random.choice(self.sign_offs)

    def get_thinking_phrase(self) -> str:
        """Get a random thinking phrase."""
        return random.choice(self.thinking_phrases)

    def get_error_phrase(self) -> str:
        """Get a random error phrase."""
        return random.choice(self.error_phrases)

    def get_success_phrase(self) -> str:
        """Get a random success phrase."""
        return random.choice(self.success_phrases)

    def get_retro_reaction(self) -> str:
        """Get a random retro reaction."""
        return random.choice(self.retro_reactions)

    def format_response(
        self,
        content: str,
        detail_level: str = "normal",
        response_tone: str = "professional"
    ) -> str:
        """Format response according to settings."""
        # Apply detail level
        if detail_level == "concise":
            content = self._make_concise(content)
        elif detail_level == "detailed":
            content = self._make_detailed(content)

        # Apply tone
        if response_tone == "friendly":
            content = self._make_friendly(content)
        elif response_tone == "casual":
            content = self._make_casual(content)
        elif response_tone == "formal":
            content = self._make_formal(content)

        # Add retro flavor if enabled
        if self.style == RetroStyle.MODERN_RETRO:
            content = self._add_retro_flavor(content)

        return content

    def _make_concise(self, content: str) -> str:
        """Make response concise."""
        # Remove unnecessary words
        words = content.split()
        if len(words) > 50:
            return " ".join(words[:50]) + "..."
        return content

    def _make_detailed(self, content: str) -> str:
        """Make response detailed."""
        # Add elaboration
        if len(content) < 100:
            return content + "\n\nMERLIN puede proporcionar más detalles si lo necesitas."
        return content

    def _make_friendly(self, content: str) -> str:
        """Make response friendly."""
        return f"¡Hola! {content}\n\n¡Espero que esto te ayude! 😊"

    def _make_casual(self, content: str) -> str:
        """Make response casual."""
        return f"Oye, {content}\n\n¡Avísame si necesitas algo más!"

    def _make_formal(self, content: str) -> str:
        """Make response formal."""
        return f"Estimado usuario,\n\n{content}\n\nAtentamente,\nMERLIN"

    def _add_retro_flavor(self, content: str) -> str:
        """Add retro office flavor."""
        # Occasionally add retro reaction
        if random.random() < 0.1:  # 10% chance
            reaction = self.get_retro_reaction()
            return f"{content}\n\n{reaction}"
        return content

    def get_typing_effect(self, message: str) -> list[str]:
        """Get typing effect for message."""
        chars = list(message)
        result = []
        current = ""

        for char in chars:
            current += char
            result.append(current)

        return result

    def get_emotion(self, sentiment: str) -> str:
        """Get emotion emoji based on sentiment."""
        emotions = {
            "positive": "😊",
            "negative": "😔",
            "neutral": "😐",
            "excited": "🎉",
            "confused": "🤔",
            "thinking": "🧙",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        return emotions.get(sentiment, "🧙")

    def get_retro_border_color(self) -> str:
        """Get retro border color based on style."""
        colors = {
            RetroStyle.OFFICE_97: "#4a5568",
            RetroStyle.OFFICE_2000: "#6366f1",
            RetroStyle.OFFICE_XP: "#f59e0b",
            RetroStyle.MODERN_RETRO: "#99199a"
        }
        return colors.get(self.style, "#99199a")

    def get_retro_background(self) -> str:
        """Get retro background based on style."""
        backgrounds = {
            RetroStyle.OFFICE_97: "linear-gradient(135deg, #2d3436 0%, #1e293b 50%, #0f172a 100%)",
            RetroStyle.OFFICE_2000: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
            RetroStyle.OFFICE_XP: "linear-gradient(135deg, #1e3a5f 0%, #2d5a87 50%, #3d7ab5 100%)",
            RetroStyle.MODERN_RETRO: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)"
        }
        return backgrounds.get(self.style, "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)")
