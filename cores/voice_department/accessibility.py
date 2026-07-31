"""Voice Accessibility - Modos de accesibilidad.

Implementa modos de accesibilidad para diferentes necesidades:
- Silent: Solo texto, sin voz
- Voice: Solo voz
- Hybrid: Voz + subtítulos
- Subtitles: Voz + subtítulos automáticos
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

from cores.voice_department.models import AccessibilityMode, VoiceVisualContext

logger = logging.getLogger("ownex.voice_department.accessibility")


class VoiceAccessibilitySystem:
    """Sistema de accesibilidad de voz."""

    def __init__(self):
        self.current_mode = AccessibilityMode.HYBRID
        self.subtitles_enabled = True
        self.subtitle_history: list[dict[str, Any]] = []

    def set_mode(self, mode: AccessibilityMode) -> None:
        """Establecer modo de accesibilidad."""
        self.current_mode = mode
        logger.info(f"Accessibility mode set to {mode.value}")

    def enable_subtitles(self, enabled: bool) -> None:
        """Habilitar/deshabilitar subtítulos."""
        self.subtitles_enabled = enabled
        logger.info(f"Subtitles {'enabled' if enabled else 'disabled'}")

    def should_speak(self) -> bool:
        """Determinar si debe hablar según modo."""
        if self.current_mode == AccessibilityMode.SILENT:
            return False
        if self.current_mode == AccessibilityMode.VOICE:
            return True
        if self.current_mode == AccessibilityMode.HYBRID:
            return True
        if self.current_mode == AccessibilityMode.SUBTITLES:
            return True

        return True

    def should_show_subtitles(self) -> bool:
        """Determinar si debe mostrar subtítulos."""
        if self.current_mode == AccessibilityMode.SILENT:
            return True  # Mostrar subtítulos en modo silencioso
        if self.current_mode == AccessibilityMode.VOICE:
            return False
        if self.current_mode == AccessibilityMode.HYBRID:
            return self.subtitles_enabled
        if self.current_mode == AccessibilityMode.SUBTITLES:
            return True

        return False

    def add_subtitle(self, text: str, timestamp: float, speaker: str = "OWNEX") -> None:
        """Agregar subtítulo."""
        if self.should_show_subtitles():
            self.subtitle_history.append({
                "text": text,
                "timestamp": timestamp,
                "speaker": speaker,
            })
            logger.debug(f"Subtitle added: {text}")

    def get_subtitle_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Obtener historial de subtítulos."""
        return self.subtitle_history[-limit:]

    def clear_subtitle_history(self) -> None:
        """Limpiar historial de subtítulos."""
        self.subtitle_history = []
        logger.info("Subtitle history cleared")

    def get_accessibility_config(self) -> dict[str, Any]:
        """Obtener configuración de accesibilidad."""
        return {
            "mode": self.current_mode.value,
            "subtitles_enabled": self.subtitles_enabled,
            "subtitle_count": len(self.subtitle_history),
        }

    def get_visual_context_for_mode(self, mode: AccessibilityMode) -> VoiceVisualContext:
        """Obtener contexto visual según modo."""
        visual_context = VoiceVisualContext()

        if mode == AccessibilityMode.SILENT:
            # En modo silencioso, mostrar más contexto visual
            visual_context.show_code = True
            visual_context.show_graphs = True
            visual_context.show_progress = True
        elif mode == AccessibilityMode.VOICE:
            # En modo voz, contexto visual mínimo
            visual_context.follow_narration = True
        elif mode == AccessibilityMode.HYBRID:
            # En modo híbrido, contexto visual balanceado
            visual_context.follow_narration = True
            visual_context.show_progress = True
        elif mode == AccessibilityMode.SUBTITLES:
            # En modo subtítulos, contexto visual con subtítulos
            visual_context.follow_narration = True
            visual_context.show_progress = True

        return visual_context


# Singleton instance
_voice_accessibility_system: VoiceAccessibilitySystem | None = None


def get_voice_accessibility() -> VoiceAccessibilitySystem:
    """Obtener instancia singleton del Voice Accessibility System."""
    global _voice_accessibility_system
    if _voice_accessibility_system is None:
        _voice_accessibility_system = VoiceAccessibilitySystem()
    return _voice_accessibility_system


def reset_voice_accessibility() -> None:
    """Resetear instancia singleton."""
    global _voice_accessibility_system
    _voice_accessibility_system = None