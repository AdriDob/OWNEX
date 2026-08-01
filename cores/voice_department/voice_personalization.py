"""Voice Personalization - Sistema de personalización de voz.

Gestiona preferencias de tono, velocidad, detalle, idioma y modos de usuario.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cores.voice_department.models import (
    ConversationMode,
    VoicePersonality,
    VoicePreference,
)

logger = logging.getLogger("ownex.voice_department.personalization")

VOICE_PREF_PATH = Path.home() / ".ownex" / "voice_department" / "preferences"
PREF_FILE = VOICE_PREF_PATH / "voice_preferences.json"


class VoicePersonalizationSystem:
    """Sistema de personalización de voz."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or VOICE_PREF_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.preferences: dict[str, VoicePreference] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Cargar preferencias de voz."""
        try:
            if PREF_FILE.exists():
                with open(PREF_FILE) as f:
                    data = json.load(f)
                    for user_id, pref_data in data.items():
                        # Convertir enums
                        if pref_data.get("preferred_mode"):
                            pref_data["preferred_mode"] = ConversationMode(pref_data["preferred_mode"])
                        if pref_data.get("preferred_personality"):
                            pref_data["preferred_personality"] = VoicePersonality(pref_data["preferred_personality"])

                        self.preferences[user_id] = VoicePreference(**pref_data)
        except Exception as exc:
            logger.error("Error loading voice preferences: %s", exc)

    def _save_data(self) -> None:
        """Guardar preferencias de voz."""
        try:
            data = {}
            for user_id, pref in self.preferences.items():
                data[user_id] = asdict(pref)

            with open(PREF_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.error("Error saving voice preferences: %s", exc)

    def get_preferences(self, user_id: str) -> VoicePreference:
        """Obtener preferencias de un usuario."""
        if user_id not in self.preferences:
            self.preferences[user_id] = VoicePreference(user_id=user_id)
            self._save_data()

        return self.preferences[user_id]

    def update_preferences(self, user_id: str, **kwargs) -> VoicePreference:
        """Actualizar preferencias de un usuario."""
        pref = self.get_preferences(user_id)

        for key, value in kwargs.items():
            if hasattr(pref, key):
                setattr(pref, key, value)

        self._save_data()
        return pref

    def set_tone(self, user_id: str, tone: str) -> VoicePreference:
        """Establecer tono."""
        return self.update_preferences(user_id, tone=tone)

    def set_speed(self, user_id: str, speed: float) -> VoicePreference:
        """Establecer velocidad."""
        return self.update_preferences(user_id, speed=max(0.5, min(2.0, speed)))

    def set_pitch(self, user_id: str, pitch: float) -> VoicePreference:
        """Establecer pitch."""
        return self.update_preferences(user_id, pitch=max(0.5, min(2.0, pitch)))

    def set_volume(self, user_id: str, volume: float) -> VoicePreference:
        """Establecer volumen."""
        return self.update_preferences(user_id, volume=max(0.0, min(1.0, volume)))

    def set_language(self, user_id: str, language: str) -> VoicePreference:
        """Establecer idioma."""
        return self.update_preferences(user_id, language=language)

    def set_auto_explain(self, user_id: str, auto_explain: bool) -> VoicePreference:
        """Establecer si explicar automáticamente."""
        return self.update_preferences(user_id, auto_explain=auto_explain)

    def set_auto_narrate(self, user_id: str, auto_narrate: bool) -> VoicePreference:
        """Establecer si narrar automáticamente."""
        return self.update_preferences(user_id, auto_narrate=auto_narrate)

    def set_interrupt_threshold(self, user_id: str, threshold: str) -> VoicePreference:
        """Establecer umbral de interrupción."""
        valid_thresholds = ["risk_only", "important", "always", "never"]
        if threshold in valid_thresholds:
            return self.update_preferences(user_id, interrupt_threshold=threshold)
        return self.get_preferences(user_id)

    def set_detail_level(self, user_id: str, detail_level: str) -> VoicePreference:
        """Establecer nivel de detalle."""
        valid_levels = ["minimal", "low", "medium", "high", "maximum"]
        if detail_level in valid_levels:
            return self.update_preferences(user_id, detail_level=detail_level)
        return self.get_preferences(user_id)

    def set_conversation_mode(self, user_id: str, mode: ConversationMode) -> None:
        """Establecer modo de conversación."""
        self.update_preferences(user_id, preferred_mode=mode)

    def set_personality(self, user_id: str, personality: VoicePersonality) -> None:
        """Establecer personalidad."""
        self.update_preferences(user_id, preferred_personality=personality)

    def get_audio_config(self, user_id: str) -> dict[str, Any]:
        """Obtener configuración de audio para el sistema de voz."""
        pref = self.get_preferences(user_id)
        return {
            "speed": pref.speed,
            "pitch": pref.pitch,
            "volume": pref.volume,
            "language": pref.language,
            "tone": pref.tone,
        }

    def get_interaction_config(self, user_id: str) -> dict[str, Any]:
        """Obtener configuración de interacción."""
        pref = self.get_preferences(user_id)
        return {
            "auto_explain": pref.auto_explain,
            "auto_narrate": pref.auto_narrate,
            "interrupt_threshold": pref.interrupt_threshold,
            "detail_level": pref.detail_level,
            "mode": pref.preferred_mode.value,
            "personality": pref.preferred_personality.value,
        }

    def should_explain(self, user_id: str) -> bool:
        """Determinar si debe explicar según preferencias."""
        pref = self.get_preferences(user_id)
        return pref.auto_explain

    def should_narrate(self, user_id: str) -> bool:
        """Determinar si debe narrar según preferencias."""
        pref = self.get_preferences(user_id)
        return pref.auto_narrate

    def should_interrupt(self, user_id: str, risk_level: str) -> bool:
        """Determinar si debe interrumpir según preferencias y riesgo."""
        pref = self.get_preferences(user_id)

        if pref.interrupt_threshold == "never":
            return False
        if pref.interrupt_threshold == "always":
            return True
        if pref.interrupt_threshold == "risk_only":
            return risk_level in ["high", "critical"]
        if pref.interrupt_threshold == "important":
            return risk_level in ["medium", "high", "critical"]

        return False

    def get_detail_level_value(self, user_id: str) -> int:
        """Obtener valor numérico de nivel de detalle (0-4)."""
        pref = self.get_preferences(user_id)
        levels = {"minimal": 0, "low": 1, "medium": 2, "high": 3, "maximum": 4}
        return levels.get(pref.detail_level, 2)


# Singleton instance
_voice_personalization_system: VoicePersonalizationSystem | None = None


def get_voice_personalization() -> VoicePersonalizationSystem:
    """Obtener instancia singleton del Voice Personalization System."""
    global _voice_personalization_system
    if _voice_personalization_system is None:
        _voice_personalization_system = VoicePersonalizationSystem()
    return _voice_personalization_system


def reset_voice_personalization() -> None:
    """Resetear instancia singleton."""
    global _voice_personalization_system
    _voice_personalization_system = None
