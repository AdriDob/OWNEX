"""Enhanced Personalization System for OWNEX OMEGA.

Sistema de personalización avanzado con:
- Nombre personal
- Preguntas personales
- Contexto de primeros días
- Integración Obsidian
- Modo guiado
- Configuración personalizada
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class UserExperienceLevel(StrEnum):
    """Nivel de experiencia del usuario."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class WorkMode(StrEnum):
    """Modo de trabajo preferido."""

    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    DATA_ANNOTATION = "data_annotation"
    FREELANCE = "freelance"
    MIXED = "mixed"


class GuidanceLevel(StrEnum):
    """Nivel de guía requerido."""

    HIGH_GUIDANCE = "high_guidance"  # Llevar de la mano
    MEDIUM_GUIDANCE = "medium_guidance"
    LOW_GUIDANCE = "low_guidance"
    SELF_DIRECTED = "self_directed"


@dataclass
class PersonalProfile:
    """Perfil personal del usuario."""

    # Información básica
    name: str = ""
    preferred_name: str = ""
    timezone: str = "UTC"
    language: str = "es"

    # Experiencia
    experience_level: UserExperienceLevel = UserExperienceLevel.BEGINNER
    work_mode: WorkMode = WorkMode.BUG_BOUNTY
    guidance_level: GuidanceLevel = GuidanceLevel.HIGH_GUIDANCE

    # Objetivos
    primary_goal: str = "Ganar dinero con bug bounty"
    secondary_goals: list[str] = field(default_factory=list)
    income_target_monthly: float = 1000.0

    # Contexto
    is_first_time_user: bool = True
    days_using: int = 0
    completed_onboarding: bool = False

    # Preferencias
    voice_enabled: bool = True
    voice_language: str = "es"
    obsidian_enabled: bool = True
    obsidian_vault_path: str = ""
    obsidian_daily_notes: bool = True

    # Estilo de trabajo
    work_hours_start: str = "09:00"
    work_hours_end: str = "18:00"
    work_days: list[str] = field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri"])
    break_reminders: bool = True

    # Productividad
    daily_tasks_enabled: bool = True
    daily_planning_enabled: bool = True
    progress_tracking: bool = True

    # Integraciones
    calendar_integration: bool = False
    email_integration: bool = False
    task_integration: str = ""  # "obsidian", "todoist", etc.

    # Personalidad del asistente
    assistant_name: str = "MERLIN"
    assistant_tone: str = "friendly_guided"  # friendly_guided, professional, casual
    assistant_proactivity: str = "high"  # high, medium, low

    # Features específicas
    bug_bounty_focus: bool = True
    dev_bounty_focus: bool = True
    data_annotation_focus: bool = True
    productivity_focus: bool = True

    # Meta
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OnboardingStep:
    """Paso del onboarding."""

    step_id: str
    title: str
    description: str
    questions: list[dict[str, Any]]
    is_required: bool = True
    can_skip: bool = False


class EnhancedPersonalizationSystem:
    """Sistema de personalización mejorado."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or Path.home() / ".ownex" / "personalization.json"
        self.profile = PersonalProfile()
        self._load_profile()

    def _load_profile(self) -> None:
        """Cargar perfil desde archivo."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                    self.profile = PersonalProfile(**data)
            except Exception:
                # Si falla, usar perfil default
                pass

    def _save_profile(self) -> None:
        """Guardar perfil a archivo."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.profile.updated_at = datetime.now().isoformat()

        with open(self.config_path, "w") as f:
            json.dump(self.profile.__dict__, f, indent=2, default=str)

    def get_onboarding_steps(self) -> list[OnboardingStep]:
        """Obtener pasos de onboarding."""
        return [
            OnboardingStep(
                step_id="welcome",
                title="¡Bienvenido a OWNEX OMEGA!",
                description="Vamos a personalizar tu experiencia para maximizar tu productividad",
                questions=[
                    {
                        "id": "name",
                        "question": "¿Cómo te llamas?",
                        "type": "text",
                        "placeholder": "Adriel",
                        "required": True,
                    },
                    {
                        "id": "preferred_name",
                        "question": "¿Cómo prefieres que te llame?",
                        "type": "text",
                        "placeholder": "Adriel",
                        "required": False,
                    },
                ],
            ),
            OnboardingStep(
                step_id="experience",
                title="Tu Experiencia",
                description="Para adaptar MERLIN a tu nivel",
                questions=[
                    {
                        "id": "experience_level",
                        "question": "¿Cuál es tu nivel de experiencia?",
                        "type": "select",
                        "options": [
                            {"value": "beginner", "label": "Principiante - Estoy aprendiendo"},
                            {"value": "intermediate", "label": "Intermedio - Tengo algo de experiencia"},
                            {"value": "advanced", "label": "Avanzado - Tengo experiencia sólida"},
                            {"value": "expert", "label": "Experto - Soy profesional"},
                        ],
                        "default": "beginner",
                        "required": True,
                    },
                    {
                        "id": "work_mode",
                        "question": "¿En qué quieres trabajar principalmente?",
                        "type": "select",
                        "options": [
                            {"value": "bug_bounty", "label": "Bug Bounty - Encontrar vulnerabilidades"},
                            {"value": "dev_bounty", "label": "Dev Bounty - Encontrar bugs en código"},
                            {"value": "data_annotation", "label": "Anotación de datos"},
                            {"value": "freelance", "label": "Freelance - Varios proyectos"},
                            {"value": "mixed", "label": "Mixto - Un poco de todo"},
                        ],
                        "default": "bug_bounty",
                        "required": True,
                    },
                ],
            ),
            OnboardingStep(
                step_id="guidance",
                title="Nivel de Guía",
                description="Cuánto necesitas que MERLIN te guíe",
                questions=[
                    {
                        "id": "guidance_level",
                        "question": "¿Cuánta guía necesitas?",
                        "type": "select",
                        "options": [
                            {
                                "value": "high_guidance",
                                "label": "Alta - Llévame de la mano paso a paso",
                            },
                            {
                                "value": "medium_guidance",
                                "label": "Media - Guía cuando sea necesario",
                            },
                            {
                                "value": "low_guidance",
                                "label": "Baja - Solo sugerencias ocasionales",
                            },
                            {
                                "value": "self_directed",
                                "label": "Autónomo - Prefiero hacerlo solo",
                            },
                        ],
                        "default": "high_guidance",
                        "required": True,
                    },
                ],
            ),
            OnboardingStep(
                step_id="goals",
                title="Tus Objetivos",
                description="Qué quieres lograr con OWNEX OMEGA",
                questions=[
                    {
                        "id": "primary_goal",
                        "question": "¿Cuál es tu objetivo principal?",
                        "type": "text",
                        "placeholder": "Ganar $1000/mes con bug bounty",
                        "required": True,
                    },
                    {
                        "id": "income_target",
                        "question": "¿Cuánto quieres ganar al mes?",
                        "type": "number",
                        "placeholder": "1000",
                        "default": 1000,
                        "required": True,
                    },
                ],
            ),
            OnboardingStep(
                step_id="integrations",
                title="Integraciones",
                description="Configurar herramientas que ya usas",
                questions=[
                    {
                        "id": "obsidian_enabled",
                        "question": "¿Tienes Obsidian instalado?",
                        "type": "boolean",
                        "default": True,
                        "required": True,
                    },
                    {
                        "id": "obsidian_vault_path",
                        "question": "¿Dónde está tu vault de Obsidian?",
                        "type": "text",
                        "placeholder": "/home/adrie/Documents/ObsidianVault",
                        "required": False,
                        "condition": "obsidian_enabled == true",
                    },
                    {
                        "id": "obsidian_daily_notes",
                        "question": "¿Quieres que MERLIN cree notas diarias?",
                        "type": "boolean",
                        "default": True,
                        "required": False,
                    },
                ],
            ),
            OnboardingStep(
                step_id="productivity",
                title="Productividad",
                description="Configurar tu sistema de trabajo",
                questions=[
                    {
                        "id": "work_hours_start",
                        "question": "¿A qué hora empiezas a trabajar?",
                        "type": "time",
                        "default": "09:00",
                        "required": True,
                    },
                    {
                        "id": "work_hours_end",
                        "question": "¿A qué hora terminas de trabajar?",
                        "type": "time",
                        "default": "18:00",
                        "required": True,
                    },
                    {
                        "id": "daily_planning",
                        "question": "¿Quieres planificación diaria automática?",
                        "type": "boolean",
                        "default": True,
                        "required": True,
                    },
                ],
            ),
            OnboardingStep(
                step_id="voice",
                title="Voice Commands",
                description="Configurar comandos de voz",
                questions=[
                    {
                        "id": "voice_enabled",
                        "question": "¿Quieres usar comandos de voz?",
                        "type": "boolean",
                        "default": True,
                        "required": True,
                    },
                    {
                        "id": "voice_language",
                        "question": "¿Idioma para comandos de voz?",
                        "type": "select",
                        "options": [
                            {"value": "es", "label": "Español"},
                            {"value": "en", "label": "English"},
                        ],
                        "default": "es",
                        "required": True,
                    },
                ],
            ),
            OnboardingStep(
                step_id="confirmation",
                title="Confirmación",
                description="Revisa tu configuración",
                questions=[
                    {
                        "id": "confirm",
                        "question": "¿Todo correcto? Podrás cambiar esto después.",
                        "type": "boolean",
                        "default": True,
                        "required": True,
                    },
                ],
            ),
        ]

    def process_step_answers(self, step_id: str, answers: dict[str, Any]) -> bool:
        """Procesar respuestas de un paso de onboarding."""
        if step_id == "welcome":
            self.profile.name = answers.get("name", "")
            self.profile.preferred_name = answers.get("preferred_name", self.profile.name)

        elif step_id == "experience":
            self.profile.experience_level = UserExperienceLevel(answers.get("experience_level", "beginner"))
            self.profile.work_mode = WorkMode(answers.get("work_mode", "bug_bounty"))

        elif step_id == "guidance":
            self.profile.guidance_level = GuidanceLevel(answers.get("guidance_level", "high_guidance"))

        elif step_id == "goals":
            self.profile.primary_goal = answers.get("primary_goal", "")
            self.profile.income_target_monthly = float(answers.get("income_target", 1000))

        elif step_id == "integrations":
            self.profile.obsidian_enabled = answers.get("obsidian_enabled", True)
            self.profile.obsidian_vault_path = answers.get("obsidian_vault_path", "")
            self.profile.obsidian_daily_notes = answers.get("obsidian_daily_notes", True)

        elif step_id == "productivity":
            self.profile.work_hours_start = answers.get("work_hours_start", "09:00")
            self.profile.work_hours_end = answers.get("work_hours_end", "18:00")
            self.profile.daily_planning_enabled = answers.get("daily_planning", True)

        elif step_id == "voice":
            self.profile.voice_enabled = answers.get("voice_enabled", True)
            self.profile.voice_language = answers.get("voice_language", "es")

        elif step_id == "confirmation":
            if answers.get("confirm", True):
                self.profile.completed_onboarding = True
                self._save_profile()
                return True

        self._save_profile()
        return True

    def get_greeting(self) -> str:
        """Obtener saludo personalizado."""
        name = self.profile.preferred_name or self.profile.name
        if not name:
            return "¡Hola! Soy MERLIN, tu asistente de inteligencia autónoma."

        if self.profile.days_using == 0:
            return f"¡Hola {name}! ¡Bienvenido a OWNEX OMEGA! Estoy aquí para guiarte paso a paso."
        elif self.profile.days_using < 7:
            return f"¡Hola {name}! Veo que llevas {self.profile.days_using} días con nosotros. ¿Cómo va tu progreso?"
        else:
            return f"¡Hola {name}! Estoy listo para ayudarte a alcanzar tus objetivos hoy."

    def get_daily_plan_prompt(self) -> str:
        """Obtener prompt para planificación diaria."""
        name = self.profile.preferred_name or self.profile.name
        goal = self.profile.primary_goal
        target = self.profile.income_target_monthly

        guidance = {
            "high_guidance": "Te guiaré paso a paso en cada tarea.",
            "medium_guidance": "Te daré sugerencias cuando las necesites.",
            "low_guidance": "Estaré disponible para consultas.",
            "self_directed": "Respetaré tu autonomía.",
        }

        return f"""
¡Hola {name}! 🧙

Hoy vamos a trabajar hacia tu objetivo: {goal}

Meta mensual: ${target:.0f}

Nivel de guía: {guidance.get(self.profile.guidance_level.value, "")}

¿Qué hacemos hoy? Te sugiero:

1. Revisar objetivos del día
2. Planificar tareas priorizadas
3. Ejecutar con mi asistencia
4. Registrar progreso

¿Por dónde quieres empezar?
"""

    def is_first_time_user(self) -> bool:
        """Verificar si es usuario primerizo."""
        return self.profile.is_first_time_user or self.profile.days_using == 0

    def increment_usage_days(self) -> None:
        """Incrementar días de uso."""
        self.profile.days_using += 1
        self._save_profile()

    def get_obsidian_config(self) -> dict[str, Any]:
        """Obtener configuración de Obsidian."""
        return {
            "enabled": self.profile.obsidian_enabled,
            "vault_path": self.profile.obsidian_vault_path,
            "daily_notes": self.profile.obsidian_daily_notes,
            "template": self._get_obsidian_template(),
        }

    def _get_obsidian_template(self) -> str:
        """Obtener template de nota diaria para Obsidian."""
        name = self.profile.preferred_name or self.profile.name
        return f"""---
created: {{date}}
tags: [daily, plan]
type: daily-note
---

# {{date}}

## 🧙 MERLIN Daily Plan for {name}

### 🎯 Objetivo del Día
{{daily_goal}}

### ✅ Tareas Prioritarias
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

### 📊 Progreso
- [ ] Progreso 1
- [ ] Progreso 2

### 💡 Notas
- Nota 1
- Nota 2

### 🏆 Logros del Día
- Logro 1
- Logro 2

### 📝 Reflexión
{{reflection}}

---
*Generated by MERLIN - OWNEX OMEGA*
"""


# Singleton instance
_enhanced_personalization_system: EnhancedPersonalizationSystem | None = None


def get_enhanced_personalization_system() -> EnhancedPersonalizationSystem:
    """Obtener instancia singleton del sistema de personalización."""
    global _enhanced_personalization_system
    if _enhanced_personalization_system is None:
        _enhanced_personalization_system = EnhancedPersonalizationSystem()
    return _enhanced_personalization_system


def reset_enhanced_personalization_system() -> None:
    """Resetear instancia singleton."""
    global _enhanced_personalization_system
    _enhanced_personalization_system = None
