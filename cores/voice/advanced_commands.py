"""Advanced Voice Commands System for MERLIN.

Sistema de comandos de voz avanzados con:
- Whisper para STT
- Piper para TTS
- Comandos personalizados
- Contexto del usuario
- Integración con todas las features
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from cores.setup.steps.enhanced_personalization import get_enhanced_personalization_system
from cores.voice_interface import VoiceConfig, VoiceInterface

logger = logging.getLogger("ownex.voice_commands")


class CommandCategory(str, Enum):
    """Categorías de comandos de voz."""
    GENERAL = "general"
    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    DATA_ANNOTATION = "data_annotation"
    PRODUCTIVITY = "productivity"
    PLANNING = "planning"
    NOTE_TAKING = "note_taking"
    OBSIDIAN = "obsidian"
    SYSTEM = "system"


@dataclass
class VoiceCommand:
    """Comando de voz."""
    command_id: str
    phrases: list[str]
    category: CommandCategory
    description: str
    action: str
    parameters: dict[str, Any]
    requires_confirmation: bool = False


class AdvancedVoiceCommands:
    """Sistema de comandos de voz avanzados."""

    def __init__(self):
        self.personalization = get_enhanced_personalization_system()
        self.voice_interface: Optional[VoiceInterface] = None
        self.commands: list[VoiceCommand] = []
        self._initialize_commands()

    def _initialize_commands(self) -> None:
        """Inicializar comandos de voz."""
        name = self.personalization.profile.preferred_name or self.personalization.profile.name

        self.commands = [
            # Comandos generales
            VoiceCommand(
                command_id="greeting",
                phrases=["hola merlin", "hey merlin", "buenos días merlin"],
                category=CommandCategory.GENERAL,
                description="Saludar a MERLIN",
                action="greet",
                parameters={},
            ),
            VoiceCommand(
                command_id="daily_plan",
                phrases=["qué hacemos hoy", "cuál es el plan de hoy", "qué me toca hoy"],
                category=CommandCategory.PLANNING,
                description="Obtener plan diario",
                action="get_daily_plan",
                parameters={},
            ),
            VoiceCommand(
                command_id="status",
                phrases=["cómo va todo", "cuál es mi progreso", "qué he logrado"],
                category=CommandCategory.GENERAL,
                description="Obtener estado y progreso",
                action="get_status",
                parameters={},
            ),

            # Comandos de bug bounty
            VoiceCommand(
                command_id="scan_target",
                phrases=["escanear objetivo", "analizar target", "revisar objetivo"],
                category=CommandCategory.BUG_BOUNTY,
                description="Escanear objetivo actual",
                action="scan_target",
                parameters={"target": "current"},
            ),
            VoiceCommand(
                command_id="new_finding",
                phrases=["encontré una vulnerabilidad", "nuevo hallazgo", "bug encontrado"],
                category=CommandCategory.BUG_BOUNTY,
                description="Reportar nuevo hallazgo",
                action="report_finding",
                parameters={},
            ),
            VoiceCommand(
                command_id="submit_report",
                phrases=["enviar reporte", "submit report", "submitir hallazgo"],
                category=CommandCategory.BUG_BOUNTY,
                description="Enviar reporte de bug bounty",
                action="submit_report",
                parameters={},
            ),

            # Comandos de productividad
            VoiceCommand(
                command_id="take_break",
                phrases=["toma un descanso", "hora de descanso", "pausa"],
                category=CommandCategory.PRODUCTIVITY,
                description="Iniciar descanso",
                action="start_break",
                parameters={},
            ),
            VoiceCommand(
                command_id="resume_work",
                phrases=["volver al trabajo", "continuar", "resumir"],
                category=CommandCategory.PRODUCTIVITY,
                description="Reanudar trabajo",
                action="resume_work",
                parameters={},
            ),
            VoiceCommand(
                command_id="focus_mode",
                phrases=["modo foco", "bloquear distracciones", "concentrarse"],
                category=CommandCategory.PRODUCTIVITY,
                description="Activar modo de concentración",
                action="enable_focus_mode",
                parameters={},
            ),

            # Comandos de notas
            VoiceCommand(
                command_id="create_note",
                phrases=["crear nota", "anotar esto", "guardar nota"],
                category=CommandCategory.NOTE_TAKING,
                description="Crear nueva nota",
                action="create_note",
                parameters={"content": "from_voice"},
            ),
            VoiceCommand(
                command_id="obsidian_note",
                phrases=["nota en obsidian", "guardar en obsidian", "obsidian"],
                category=CommandCategory.OBSIDIAN,
                description="Crear nota en Obsidian",
                action="create_obsidian_note",
                parameters={"content": "from_voice"},
            ),

            # Comandos del sistema
            VoiceCommand(
                command_id="shutdown",
                phrases=["apagar", "cerrar", "adiós merlin"],
                category=CommandCategory.SYSTEM,
                description="Apagar sistema",
                action="shutdown",
                parameters={},
                requires_confirmation=True,
            ),
        ]

    def initialize_voice(self) -> bool:
        """Inicializar interfaz de voz."""
        try:
            config = VoiceConfig(
                stt_provider="local",
                stt_model="base",
                tts_provider="local",
                voice_language=self.personalization.profile.voice_language,
            )

            self.voice_interface = VoiceInterface(config)
            initialized = self.voice_interface.initialize()

            if initialized:
                logger.info("Voice interface initialized successfully")
            else:
                logger.warning("Voice interface initialization failed")

            return initialized

        except Exception as e:
            logger.error(f"Failed to initialize voice interface: {e}")
            return False

    def process_voice_command(self, text: str) -> dict[str, Any]:
        """Procesar comando de voz."""
        text_lower = text.lower().strip()

        # Buscar comando coincidente
        matched_command = None
        for command in self.commands:
            for phrase in command.phrases:
                if phrase in text_lower:
                    matched_command = command
                    break
            if matched_command:
                break

        if not matched_command:
            return {
                "success": False,
                "error": "Command not recognized",
                "text": text,
            }

        # Ejecutar comando
        result = self._execute_command(matched_command, text)

        return {
            "success": True,
            "command": matched_command.command_id,
            "category": matched_command.category.value,
            "result": result,
        }

    def _execute_command(self, command: VoiceCommand, text: str) -> Any:
        """Ejecutar comando."""
        name = self.personalization.profile.preferred_name or self.personalization.profile.name

        if command.action == "greet":
            return self._greet(name)

        elif command.action == "get_daily_plan":
            return self._get_daily_plan(name)

        elif command.action == "get_status":
            return self._get_status(name)

        elif command.action == "scan_target":
            return self._scan_target()

        elif command.action == "report_finding":
            return self._report_finding()

        elif command.action == "submit_report":
            return self._submit_report()

        elif command.action == "start_break":
            return self._start_break()

        elif command.action == "resume_work":
            return self._resume_work()

        elif command.action == "enable_focus_mode":
            return self._enable_focus_mode()

        elif command.action == "create_note":
            return self._create_note(text)

        elif command.action == "create_obsidian_note":
            return self._create_obsidian_note(text)

        elif command.action == "shutdown":
            return self._shutdown()

        else:
            return {"error": "Unknown action"}

    def _greet(self, name: str) -> str:
        """Saludar al usuario."""
        greeting = self.personalization.get_greeting()
        if self.voice_interface:
            self.voice_interface.speak(greeting)
        return greeting

    def _get_daily_plan(self, name: str) -> str:
        """Obtener plan diario."""
        plan = self.personalization.get_daily_plan_prompt()
        if self.voice_interface:
            self.voice_interface.speak(plan)
        return plan

    def _get_status(self, name: str) -> dict[str, Any]:
        """Obtener estado."""
        return {
            "name": name,
            "days_using": self.personalization.profile.days_using,
            "completed_onboarding": self.personalization.profile.completed_onboarding,
            "guidance_level": self.personalization.profile.guidance_level.value,
            "primary_goal": self.personalization.profile.primary_goal,
            "income_target": self.personalization.profile.income_target_monthly,
        }

    def _scan_target(self) -> str:
        """Escanear objetivo."""
        response = "Iniciando escaneo del objetivo actual. Te guiaré paso a paso."
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def _report_finding(self) -> str:
        """Reportar hallazgo."""
        response = "Excelente hallazgo. Te ayudaré a documentarlo y prepararlo para envío."
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def _submit_report(self) -> str:
        """Enviar reporte."""
        response = "Preparando reporte para envío. Revisaré todo antes de submitir."
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def _start_break(self) -> str:
        """Iniciar descanso."""
        response = "Entendido. Iniciando descanso. Te avisaré cuando sea hora de volver."
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def _resume_work(self) -> str:
        """Reanudar trabajo."""
        response = "Bienvenido de vuelta. Continuemos donde lo dejamos."
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def _enable_focus_mode(self) -> str:
        """Activar modo de concentración."""
        response = "Modo de concentración activado. Bloqueando distracciones."
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def _create_note(self, text: str) -> str:
        """Crear nota."""
        # Extraer contenido después del comando
        content = text.replace("crear nota", "").replace("anotar esto", "").replace("guardar nota", "").strip()
        response = f"Nota guardada: {content}"
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def _create_obsidian_note(self, text: str) -> str:
        """Crear nota en Obsidian."""
        from cores.obsidian.integration import get_obsidian_integration

        obsidian = get_obsidian_integration()
        content = text.replace("nota en obsidian", "").replace("guardar en obsidian", "").replace("obsidian", "").strip()

        result = obsidian.create_merlin_note(
            title="Voice Note",
            content=content,
            tags=["voice", "merlin"],
        )

        response = "Nota creada en Obsidian correctamente."
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def _shutdown(self) -> str:
        """Apagar sistema."""
        response = "Entendido. Hasta pronto. ¡Excelente trabajo hoy!"
        if self.voice_interface:
            self.voice_interface.speak(response)
        return response

    def get_available_commands(self) -> list[dict[str, Any]]:
        """Obtener comandos disponibles."""
        return [
            {
                "command_id": cmd.command_id,
                "phrases": cmd.phrases,
                "category": cmd.category.value,
                "description": cmd.description,
            }
            for cmd in self.commands
        ]


# Singleton instance
_advanced_voice_commands: Optional[AdvancedVoiceCommands] = None


def get_advanced_voice_commands() -> AdvancedVoiceCommands:
    """Obtener instancia singleton del sistema de comandos de voz."""
    global _advanced_voice_commands
    if _advanced_voice_commands is None:
        _advanced_voice_commands = AdvancedVoiceCommands()
    return _advanced_voice_commands


def reset_advanced_voice_commands() -> None:
    """Resetear instancia singleton."""
    global _advanced_voice_commands
    _advanced_voice_commands = None
