"""Voice Memory - Sistema de memoria de voz.

Recuerda preferencias, tono, velocidad, detalle, horarios, formas de trabajo,
errores frecuentes y explicaciones anteriores para evitar repeticiones innecesarias.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cores.voice_department.models import VoiceExplanation, VoiceMemory

logger = logging.getLogger("ownex.voice_department.memory")

VOICE_MEMORY_PATH = Path.home() / ".ownex" / "voice_department" / "memory"
MEMORY_FILE = VOICE_MEMORY_PATH / "voice_memory.json"


class VoiceMemorySystem:
    """Sistema de memoria de voz."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or VOICE_MEMORY_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.memories: dict[str, VoiceMemory] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Cargar memorias de voz."""
        try:
            if MEMORY_FILE.exists():
                with open(MEMORY_FILE) as f:
                    data = json.load(f)
                    for user_id, mem_data in data.items():
                        # Convertir VoiceExplanation objects
                        explanations = {}
                        for key, exp_data in mem_data.get("previous_explanations", {}).items():
                            explanations[key] = VoiceExplanation(**exp_data)

                        # Convertir datetime
                        last_interaction = None
                        if mem_data.get("last_interaction"):
                            last_interaction = datetime.fromisoformat(mem_data["last_interaction"])

                        self.memories[user_id] = VoiceMemory(
                            user_id=user_id,
                            previous_explanations=explanations,
                            common_questions=mem_data.get("common_questions", {}),
                            error_patterns=mem_data.get("error_patterns", []),
                            learning_points=mem_data.get("learning_points", []),
                            preferred_responses=mem_data.get("preferred_responses", {}),
                            last_interaction=last_interaction,
                            interaction_count=mem_data.get("interaction_count", 0),
                        )
        except Exception as exc:
            logger.error("Error loading voice memory: %s", exc)

    def _save_data(self) -> None:
        """Guardar memorias de voz."""
        try:
            data = {}
            for user_id, memory in self.memories.items():
                data[user_id] = {
                    "user_id": memory.user_id,
                    "previous_explanations": {
                        k: asdict(v) for k, v in memory.previous_explanations.items()
                    },
                    "common_questions": memory.common_questions,
                    "error_patterns": memory.error_patterns,
                    "learning_points": memory.learning_points,
                    "preferred_responses": memory.preferred_responses,
                    "last_interaction": memory.last_interaction.isoformat() if memory.last_interaction else None,
                    "interaction_count": memory.interaction_count,
                }

            with open(MEMORY_FILE, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as exc:
            logger.error("Error saving voice memory: %s", exc)

    def get_memory(self, user_id: str) -> VoiceMemory:
        """Obtener memoria de un usuario."""
        if user_id not in self.memories:
            self.memories[user_id] = VoiceMemory(user_id=user_id)
            self._save_data()

        memory = self.memories[user_id]
        memory.last_interaction = datetime.now()
        memory.interaction_count += 1
        self._save_data()

        return memory

    def save_explanation(self, user_id: str, topic: str, explanation: VoiceExplanation) -> None:
        """Guardar una explicación."""
        memory = self.get_memory(user_id)
        memory.previous_explanations[topic] = explanation
        self._save_data()

    def get_previous_explanation(self, user_id: str, topic: str) -> VoiceExplanation | None:
        """Obtener explicación previa sobre un tema."""
        memory = self.get_memory(user_id)
        return memory.previous_explanations.get(topic)

    def has_explained_before(self, user_id: str, topic: str) -> bool:
        """Verificar si ya se explicó un tema."""
        memory = self.get_memory(user_id)
        return topic in memory.previous_explanations

    def save_common_question(self, user_id: str, question: str, answer: str) -> None:
        """Guardar pregunta común y su respuesta."""
        memory = self.get_memory(user_id)
        memory.common_questions[question] = answer
        self._save_data()

    def get_common_question_answer(self, user_id: str, question: str) -> str | None:
        """Obtener respuesta a pregunta común."""
        memory = self.get_memory(user_id)
        return memory.common_questions.get(question)

    def record_error_pattern(self, user_id: str, error_pattern: str) -> None:
        """Registrar patrón de error frecuente."""
        memory = self.get_memory(user_id)
        if error_pattern not in memory.error_patterns:
            memory.error_patterns.append(error_pattern)
            self._save_data()

    def add_learning_point(self, user_id: str, learning: str) -> None:
        """Agregar punto de aprendizaje."""
        memory = self.get_memory(user_id)
        memory.learning_points.append(learning)
        self._save_data()

    def save_preferred_response(self, user_id: str, situation: str, response: str) -> None:
        """Guardar respuesta preferida para una situación."""
        memory = self.get_memory(user_id)
        memory.preferred_responses[situation] = response
        self._save_data()

    def get_preferred_response(self, user_id: str, situation: str) -> str | None:
        """Obtener respuesta preferida para una situación."""
        memory = self.get_memory(user_id)
        return memory.preferred_responses.get(situation)

    def get_learning_summary(self, user_id: str) -> dict[str, Any]:
        """Obtener resumen de aprendizaje."""
        memory = self.get_memory(user_id)
        return {
            "user_id": user_id,
            "interaction_count": memory.interaction_count,
            "explanations_given": len(memory.previous_explanations),
            "common_questions_count": len(memory.common_questions),
            "error_patterns_count": len(memory.error_patterns),
            "learning_points_count": len(memory.learning_points),
            "recent_learning": memory.learning_points[-5:] if memory.learning_points else [],
            "last_interaction": memory.last_interaction.isoformat() if memory.last_interaction else None,
        }


# Singleton instance
_voice_memory_system: VoiceMemorySystem | None = None


def get_voice_memory() -> VoiceMemorySystem:
    """Obtener instancia singleton del Voice Memory System."""
    global _voice_memory_system
    if _voice_memory_system is None:
        _voice_memory_system = VoiceMemorySystem()
    return _voice_memory_system


def reset_voice_memory() -> None:
    """Resetear instancia singleton."""
    global _voice_memory_system
    _voice_memory_system = None