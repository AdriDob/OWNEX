"""Voice Visual Interface - Interfaz visual mientras habla.

Sistema que permite mostrar visualmente mientras OWNEX habla:
- Resaltar archivos
- Mostrar código
- Mostrar gráficos
- Mostrar progreso
- Resaltar cambios
- Seguir la narración
"""

from __future__ import annotations

import logging
from typing import Any

from cores.voice_department.models import VoiceVisualContext

logger = logging.getLogger("ownex.voice_department.visual_interface")


class VoiceVisualInterface:
    """Interfaz visual mientras habla."""

    def __init__(self):
        self.current_visual_context: VoiceVisualContext | None = None

    def create_visual_context(self, visual_config: dict[str, Any] | None = None) -> VoiceVisualContext:
        """Crear contexto visual."""
        context = VoiceVisualContext()

        if visual_config:
            if visual_config.get("highlight_files"):
                context.highlight_files = visual_config["highlight_files"]
            if visual_config.get("show_code"):
                context.show_code = visual_config["show_code"]
                context.code_content = visual_config.get("code_content", "")
            if visual_config.get("show_graphs"):
                context.show_graphs = visual_config["show_graphs"]
            if visual_config.get("show_progress"):
                context.show_progress = visual_config["show_progress"]
                context.progress_value = visual_config.get("progress_value", 0.0)
            if visual_config.get("highlight_changes"):
                context.highlight_changes = visual_config["highlight_changes"]
            if visual_config.get("follow_narration") is not None:
                context.follow_narration = visual_config["follow_narration"]

        self.current_visual_context = context
        return context

    def highlight_files(self, file_paths: list[str]) -> VoiceVisualContext:
        """Resaltar archivos específicos."""
        if not self.current_visual_context:
            self.current_visual_context = VoiceVisualContext()

        self.current_visual_context.highlight_files = file_paths
        return self.current_visual_context

    def show_code_snippet(self, code: str, language: str = "python") -> VoiceVisualContext:
        """Mostrar snippet de código."""
        if not self.current_visual_context:
            self.current_visual_context = VoiceVisualContext()

        self.current_visual_context.show_code = True
        self.current_visual_context.code_content = f"```{language}\n{code}\n```"
        return self.current_visual_context

    def show_graph(self, graph_data: dict[str, Any]) -> VoiceVisualContext:
        """Mostrar gráfico."""
        if not self.current_visual_context:
            self.current_visual_context = VoiceVisualContext()

        self.current_visual_context.show_graphs = True
        return self.current_visual_context

    def show_progress(self, value: float, message: str = "") -> VoiceVisualContext:
        """Mostrar progreso."""
        if not self.current_visual_context:
            self.current_visual_context = VoiceVisualContext()

        self.current_visual_context.show_progress = True
        self.current_visual_context.progress_value = value
        return self.current_visual_context

    def highlight_changes(self, changed_files: list[str]) -> VoiceVisualContext:
        """Resaltar cambios en archivos."""
        if not self.current_visual_context:
            self.current_visual_context = VoiceVisualContext()

        self.current_visual_context.highlight_changes = True
        self.current_visual_context.highlight_files = changed_files
        return self.current_visual_context

    def generate_visual_state(self) -> dict[str, Any]:
        """Generar estado visual para el frontend."""
        if not self.current_visual_context:
            return {
                "highlight_files": [],
                "show_code": False,
                "code_content": "",
                "show_graphs": False,
                "show_progress": False,
                "progress_value": 0.0,
                "highlight_changes": False,
                "follow_narration": True,
            }

        return {
            "highlight_files": self.current_visual_context.highlight_files,
            "show_code": self.current_visual_context.show_code,
            "code_content": self.current_visual_context.code_content,
            "show_graphs": self.current_visual_context.show_graphs,
            "show_progress": self.current_visual_context.show_progress,
            "progress_value": self.current_visual_context.progress_value,
            "highlight_changes": self.current_visual_context.highlight_changes,
            "follow_narration": self.current_visual_context.follow_narration,
        }

    def clear_visual_context(self) -> VoiceVisualContext:
        """Limpiar contexto visual."""
        self.current_visual_context = VoiceVisualContext()
        return self.current_visual_context


# Singleton instance
_voice_visual_interface: VoiceVisualInterface | None = None


def get_voice_visual_interface() -> VoiceVisualInterface:
    """Obtener instancia singleton del Voice Visual Interface."""
    global _voice_visual_interface
    if _voice_visual_interface is None:
        _voice_visual_interface = VoiceVisualInterface()
    return _voice_visual_interface


def reset_voice_visual_interface() -> None:
    """Resetear instancia singleton."""
    global _voice_visual_interface
    _voice_visual_interface = None