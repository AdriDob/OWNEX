"""Guided Onboarding System for OWNEX OMEGA.

Sistema de onboarding guiado para primeros días:
- Guía paso a paso
- Lecciones personalizadas
- Progresión gradual
- Contexto del usuario
- Integración con todas las features
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.setup.steps.enhanced_personalization import get_enhanced_personalization_system


class OnboardingDay(StrEnum):
    """Días de onboarding."""
    DAY_1 = "day_1"
    DAY_2 = "day_2"
    DAY_3 = "day_3"
    DAY_4 = "day_4"
    DAY_5 = "day_5"
    DAY_6 = "day_6"
    DAY_7 = "day_7"


class LessonStatus(StrEnum):
    """Estado de lección."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class Lesson:
    """Lección de onboarding."""
    lesson_id: str
    day: OnboardingDay
    title: str
    description: str
    content: str
    duration_minutes: int
    status: LessonStatus = LessonStatus.NOT_STARTED
    completed_at: str | None = None
    notes: str = ""


@dataclass
class OnboardingProgress:
    """Progreso de onboarding."""
    user_name: str
    current_day: OnboardingDay
    lessons_completed: int = 0
    lessons_total: int = 0
    completion_percentage: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    notes: list[str] = field(default_factory=list)


class GuidedOnboardingSystem:
    """Sistema de onboarding guiado."""

    def __init__(self, storage_path: Path | None = None):
        self.personalization = get_enhanced_personalization_system()
        self.storage_path = storage_path or Path.home() / ".ownex" / "onboarding"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.progress: OnboardingProgress | None = None
        self.lessons: list[Lesson] = []
        self._load_progress()
        self._initialize_lessons()

    def _load_progress(self) -> None:
        """Cargar progreso desde almacenamiento."""
        progress_file = self.storage_path / "progress.json"

        if progress_file.exists():
            with open(progress_file) as f:
                data = json.load(f)
                self.progress = OnboardingProgress(**data)

    def _save_progress(self) -> None:
        """Guardar progreso a almacenamiento."""
        if not self.progress:
            return

        progress_file = self.storage_path / "progress.json"

        with open(progress_file, "w") as f:
            json.dump(self.progress.__dict__, f, indent=2, default=str)

    def _initialize_lessons(self) -> None:
        """Inicializar lecciones de onboarding."""
        name = self.personalization.profile.preferred_name or self.personalization.profile.name
        guidance = self.personalization.profile.guidance_level
        work_mode = self.personalization.profile.work_mode

        self.lessons = [
            # Day 1
            Lesson(
                lesson_id="day1_1",
                day=OnboardingDay.DAY_1,
                title="Bienvenido a OWNEX OMEGA",
                description="Introducción al sistema y tu asistente MERLIN",
                content=f"""
¡Hola {name}! 🧙

Bienvenido a OWNEX OMEGA, tu sistema de inteligencia autónoma para bug bounty y productividad remunerada.

Soy MERLIN, tu asistente personal. Estaré contigo durante todo el proceso, guiándote paso a paso.

## ¿Qué es OWNEX OMEGA?

OWNEX OMEGA es un sistema completo que te ayudará a:
- Encontrar vulnerabilidades en bug bounty
- Encontrar bugs en código (dev bounty)
- Anotar datos remuneradamente
- Gestionar tu productividad
- Planificar tu día a día
- Crear notas automáticas en Obsidian

## Tu Nivel de Guía

He configurado el sistema para guiarte con nivel: {guidance.value}

Esto significa que:
- Te daré instrucciones detalladas
- Explicaré cada paso
- Estaré disponible para preguntas
- Adaptaré mi ayuda a tu nivel

## Tu Modo de Trabajo

He configurado el sistema para: {work_mode.value}

En las próximas lecciones, te enseñaré específicamente sobre este modo de trabajo.

¡Empecemos! 🚀
""",
                duration_minutes=15,
            ),
            Lesson(
                lesson_id="day1_2",
                day=OnboardingDay.DAY_1,
                title="Configuración Inicial",
                description="Configurar tu entorno de trabajo",
                content=f"""
{guidance.value == "high_guidance" and "Llevaré de la mano" or "Te guiaré"} en la configuración de tu entorno.

## Paso 1: Verificar Requisitos

Vamos a verificar que todo esté listo:
- Python 3.11+ instalado ✓
- OWNEX OMEGA instalado ✓
- Obsidian configurado ✓

## Paso 2: Configurar tu Workspace

Vamos a organizar tu espacio de trabajo:
1. Crea una carpeta para tus proyectos
2. Configura tu vault de Obsidian
3. Configura tus horarios de trabajo

## Paso 3: Primera Interacción con MERLIN

Prueba decirme: "Hola MERLIN, ¿qué hacemos hoy?"

Yo te responderé con tu plan diario personalizado.

¡Siguiente lección! 🎯
""",
                duration_minutes=20,
            ),

            # Day 2
            Lesson(
                lesson_id="day2_1",
                day=OnboardingDay.DAY_2,
                title="Fundamentos de Bug Bounty",
                description="Aprender los conceptos básicos de bug bounty",
                content=f"""
{guidance.value == "high_guidance" and "Te explicaré" or "Repasaremos"} los fundamentos de bug bounty.

## ¿Qué es Bug Bounty?

Bug bounty es un programa donde empresas pagan por encontrar vulnerabilidades en sus sistemas.

## Tipos de Vulnerabilidades

Las más comunes que buscarás:
1. **XSS (Cross-Site Scripting)** - Inyección de scripts
2. **SQL Injection** - Inyección de SQL
3. **CSRF (Cross-Site Request Forgery)** - Falsificación de peticiones
4. **IDOR (Insecure Direct Object Reference)** - Referencia insegura a objetos
5. **Authentication Bypass** - Bypass de autenticación

## Plataformas Principales

1. **HackerOne** - La más grande
2. **Bugcrowd** - Muy popular
3. **Intigriti** - Enfocada en privacidad
4. **YesWeHack** - Europea

## Tu Primer Objetivo

Tu primer objetivo será familiarizarte con una plataforma.

{guidance.value == "high_guidance" and "Te guiaré paso a paso" or "Te daré instrucciones"} para registrarte en HackerOne.

¡Siguiente lección! 🎯
""",
                duration_minutes=25,
            ),
            Lesson(
                lesson_id="day2_2",
                day=OnboardingDay.DAY_2,
                title="Primera Práctica",
                description="Tu primera práctica de bug bounty",
                content=f"""
Ahora que conoces los fundamentos, es hora de tu primera práctica.

## Ejercicio Práctico

Vamos a hacer un ejercicio simple:
1. Seleccionar un target de práctica
2. Explorar la aplicación
3. Buscar vulnerabilidades simples
4. Documentar tus hallazgos

## Target de Prctica

Te sugiero usar:
- **Hacker101** (práctica de HackerOne)
- **PortSwigger Web Security Academy** (práctica gratuita)

## Mi Guía

{guidance.value == "high_guidance" and "Estaré contigo en cada paso" or "Estaré disponible"} para ayudarte con dudas.

## Documentación

Te enseñaré a documentar tus hallazgos correctamente.

¡Practicar! 🎯
""",
                duration_minutes=30,
            ),

            # Day 3
            Lesson(
                lesson_id="day3_1",
                day=OnboardingDay.DAY_3,
                title="Sistema de Planificación Diaria",
                description="Aprender a usar el sistema de planificación",
                content="""
El sistema de planificación diaria es tu clave para la productividad.

## ¿Cómo Funciona?

Cada día, MERLIN genera un plan personalizado:
- Tareas específicas según tu modo de trabajo
- Horarios configurados
- Breaks programados
- Seguimiento de progreso

## Tu Plan Diario

Tu plan incluye:
1. Revisión de objetivos
2. Tareas priorizadas
3. Sesiones de enfoque
4. Breaks
5. Registro en Obsidian

## Integración con Obsidian

Todo tu progreso se guarda automáticamente en Obsidian:
- Notas diarias
- Progreso
- Logros
- Reflexiones

## Ejercicio

Vamos a generar tu primer plan diario:
- Revisa tu plan de hoy
- Completa las primeras tareas
- Observa cómo se actualiza tu progreso

¡Planifica! 🎯
""",
                duration_minutes=20,
            ),
            Lesson(
                lesson_id="day3_2",
                day=OnboardingDay.DAY_3,
                title="Voice Commands",
                description="Aprender a usar comandos de voz",
                content="""
Los comandos de voz te permiten interactuar conmigo sin usar el teclado.

## Comandos Básicos

1. **"Hola MERLIN"** - Saludar
2. **"¿Qué hacemos hoy?"** - Obtener plan diario
3. **"Crear nota"** - Crear nota en Obsidian
4. **"Toma un descanso"** - Iniciar break
5. **"Volver al trabajo"** - Reanudar trabajo

## Comandos de Bug Bounty

1. **"Escanear objetivo"** - Escanear target actual
2. **"Encontré una vulnerabilidad"** - Reportar hallazgo
3. **"Enviar reporte"** - Submitir reporte

## Configuración

Asegúrate de tener:
- Whisper instalado (para reconocimiento de voz)
- Piper instalado (para síntesis de voz)
- Micrófono configurado

## Ejercicio

Prueba los comandos básicos:
- Di "Hola MERLIN"
- Pregunta "¿Qué hacemos hoy?"
- Pide "Crear nota"

¡Practica con voz! 🎯
""",
                duration_minutes=25,
            ),

            # Day 4-7: Más lecciones según modo de trabajo
        ]

    def start_onboarding(self) -> OnboardingProgress:
        """Iniciar onboarding."""
        name = self.personalization.profile.preferred_name or self.personalization.profile.name

        self.progress = OnboardingProgress(
            user_name=name,
            current_day=OnboardingDay.DAY_1,
            lessons_total=len(self.lessons),
        )

        self._save_progress()
        return self.progress

    def get_current_lesson(self) -> Lesson | None:
        """Obtener lección actual."""
        if not self.progress:
            return None

        # Encontrar primera lección no completada del día actual
        day_lessons = [lesson for lesson in self.lessons if lesson.day == self.progress.current_day]
        for lesson in day_lessons:
            if lesson.status == LessonStatus.NOT_STARTED:
                return lesson

        # Si todas las lecciones del día están completas, avanzar al siguiente día
        self._advance_day()
        return self.get_current_lesson()

    def complete_lesson(self, lesson_id: str, notes: str = "") -> bool:
        """Completar lección."""
        lesson = next((existing_lesson for existing_lesson in self.lessons if existing_lesson.lesson_id == lesson_id), None)

        if not lesson:
            return False

        lesson.status = LessonStatus.COMPLETED
        lesson.completed_at = datetime.now().isoformat()
        lesson.notes = notes

        if self.progress:
            self.progress.lessons_completed += 1
            self.progress.completion_percentage = (self.progress.lessons_completed / self.progress.lessons_total) * 100

        self._save_progress()
        return True

    def _advance_day(self) -> None:
        """Avanzar al siguiente día de onboarding."""
        if not self.progress:
            return

        days_order = list(OnboardingDay)
        current_index = days_order.index(self.progress.current_day)

        if current_index < len(days_order) - 1:
            self.progress.current_day = days_order[current_index + 1]
            self._save_progress()

    def get_onboarding_summary(self) -> dict[str, Any]:
        """Obtener resumen de onboarding."""
        if not self.progress:
            return {"error": "Onboarding not started"}

        return {
            "user_name": self.progress.user_name,
            "current_day": self.progress.current_day.value,
            "lessons_completed": self.progress.lessons_completed,
            "lessons_total": self.progress.lessons_total,
            "completion_percentage": self.progress.completion_percentage,
            "started_at": self.progress.started_at,
            "completed_at": self.progress.completed_at,
            "notes": self.progress.notes,
        }

    def is_onboarding_complete(self) -> bool:
        """Verificar si onboarding está completo."""
        if not self.progress:
            return False

        return self.progress.current_day == OnboardingDay.DAY_7 and self.progress.lessons_completed == self.progress.lessons_total


# Singleton instance
_guided_onboarding_system: GuidedOnboardingSystem | None = None


def get_guided_onboarding_system() -> GuidedOnboardingSystem:
    """Obtener instancia singleton del sistema de onboarding guiado."""
    global _guided_onboarding_system
    if _guided_onboarding_system is None:
        _guided_onboarding_system = GuidedOnboardingSystem()
    return _guided_onboarding_system


def reset_guided_onboarding_system() -> None:
    """Resetear instancia singleton."""
    global _guided_onboarding_system
    _guided_onboarding_system = None
