"""Daily Planning and Productivity System for OWNEX OMEGA.

Sistema de planificación diaria y productividad para:
- Planes diarios personalizados
- Seguimiento de progreso
- Focus en productividad remunerada
- Bug bounty, dev bounty, data annotation
- Reminders y breaks
- Integración con Obsidian
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.obsidian.integration import get_obsidian_integration
from cores.setup.steps.enhanced_personalization import get_enhanced_personalization_system


class TaskPriority(StrEnum):
    """Prioridad de tarea."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(StrEnum):
    """Estado de tarea."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskCategory(StrEnum):
    """Categoría de tarea."""

    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    DATA_ANNOTATION = "data_annotation"
    LEARNING = "learning"
    PLANNING = "planning"
    ADMIN = "admin"
    BREAK = "break"


@dataclass
class Task:
    """Tarea diaria."""

    task_id: str
    title: str
    description: str
    category: TaskCategory
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    estimated_minutes: int = 60
    completed_minutes: int = 0
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None


@dataclass
class DailyPlan:
    """Plan diario."""

    date: str
    tasks: list[Task] = field(default_factory=list)
    total_estimated_minutes: int = 0
    total_completed_minutes: int = 0
    progress_percentage: float = 0.0
    breaks_scheduled: int = 0
    breaks_taken: int = 0
    focus_sessions: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProductivityMetrics:
    """Métricas de productividad."""

    date: str
    tasks_completed: int = 0
    tasks_total: int = 0
    focus_hours: float = 0.0
    break_hours: float = 0.0
    revenue_generated: float = 0.0
    bugs_found: int = 0
    reports_submitted: int = 0
    learning_hours: float = 0.0
    efficiency_score: float = 0.0


class DailyPlanningSystem:
    """Sistema de planificación diaria."""

    def __init__(self, storage_path: Path | None = None):
        self.personalization = get_enhanced_personalization_system()
        self.obsidian = get_obsidian_integration()
        self.storage_path = storage_path or Path.home() / ".ownex" / "daily_plans"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_plans()

    def _load_plans(self) -> None:
        """Cargar planes desde almacenamiento."""
        self.plans: dict[str, DailyPlan] = {}
        for plan_file in self.storage_path.glob("*.json"):
            with open(plan_file) as f:
                data = json.load(f)
                date = data["date"]
                tasks = [Task(**task) for task in data["tasks"]]
                self.plans[date] = DailyPlan(
                    date=date,
                    tasks=tasks,
                    total_estimated_minutes=data["total_estimated_minutes"],
                    total_completed_minutes=data["total_completed_minutes"],
                    progress_percentage=data["progress_percentage"],
                    breaks_scheduled=data["breaks_scheduled"],
                    breaks_taken=data["breaks_taken"],
                    focus_sessions=data["focus_sessions"],
                    created_at=data["created_at"],
                    updated_at=data["updated_at"],
                )

    def _save_plan(self, plan: DailyPlan) -> None:
        """Guardar plan a almacenamiento."""
        plan.updated_at = datetime.now().isoformat()
        plan_file = self.storage_path / f"{plan.date}.json"

        with open(plan_file, "w") as f:
            json.dump(
                {
                    "date": plan.date,
                    "tasks": [task.__dict__ for task in plan.tasks],
                    "total_estimated_minutes": plan.total_estimated_minutes,
                    "total_completed_minutes": plan.total_completed_minutes,
                    "progress_percentage": plan.progress_percentage,
                    "breaks_scheduled": plan.breaks_scheduled,
                    "breaks_taken": plan.breaks_taken,
                    "focus_sessions": plan.focus_sessions,
                    "created_at": plan.created_at,
                    "updated_at": plan.updated_at,
                },
                f,
                indent=2,
                default=str,
            )

    def generate_daily_plan(self, date: datetime | None = None) -> DailyPlan:
        """Generar plan diario basado en perfil del usuario."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")

        # Si ya existe plan para este día, retornarlo
        if date_str in self.plans:
            return self.plans[date_str]

        # Generar nuevo plan
        plan = DailyPlan(date=date_str)

        guidance = self.personalization.profile.guidance_level
        experience = self.personalization.profile.experience_level
        work_mode = self.personalization.profile.work_mode

        # Generar tareas según perfil
        if work_mode.value == "bug_bounty" or work_mode.value == "mixed":
            plan.tasks.extend(self._generate_bug_bounty_tasks(guidance, experience))

        if work_mode.value == "dev_bounty" or work_mode.value == "mixed":
            plan.tasks.extend(self._generate_dev_bounty_tasks(guidance, experience))

        if work_mode.value == "data_annotation" or work_mode.value == "mixed":
            plan.tasks.extend(self._generate_data_annotation_tasks(guidance, experience))

        # Agregar tareas de aprendizaje para principiantes
        if experience.value == "beginner":
            plan.tasks.extend(self._generate_learning_tasks(guidance))

        # Agregar tareas de planificación
        plan.tasks.extend(self._generate_planning_tasks(guidance))

        # Calcular tiempos
        plan.total_estimated_minutes = sum(task.estimated_minutes for task in plan.tasks)

        # Agregar breaks
        plan.breaks_scheduled = self._calculate_breaks(plan.total_estimated_minutes)

        self.plans[date_str] = plan
        self._save_plan(plan)

        return plan

    def _generate_bug_bounty_tasks(self, guidance, experience) -> list[Task]:
        """Generar tareas de bug bounty."""
        tasks = []

        if guidance.value == "high_guidance":
            tasks.extend(
                [
                    Task(
                        task_id="bb1",
                        title="Revisar objetivos de bug bounty",
                        description="MERLIN te guiará paso a paso en cómo configurar tus objetivos de bug bounty",
                        category=TaskCategory.BUG_BOUNTY,
                        priority=TaskPriority.CRITICAL,
                        estimated_minutes=30,
                    ),
                    Task(
                        task_id="bb2",
                        title="Explorar plataformas de bug bounty",
                        description="MERLIN te mostrará las mejores plataformas para empezar (HackerOne, Bugcrowd, etc.)",
                        category=TaskCategory.BUG_BOUNTY,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=45,
                    ),
                    Task(
                        task_id="bb3",
                        title="Seleccionar primer objetivo",
                        description="MERLIN te ayudará a elegir tu primer target basado en tu nivel",
                        category=TaskCategory.BUG_BOUNTY,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=30,
                    ),
                ]
            )
        else:
            tasks.extend(
                [
                    Task(
                        task_id="bb1",
                        title="Revisar targets activos",
                        description="Revisar objetivos actuales y priorizar",
                        category=TaskCategory.BUG_BOUNTY,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=30,
                    ),
                    Task(
                        task_id="bb2",
                        title="Análisis de objetivo seleccionado",
                        description="Análisis profundo del target",
                        category=TaskCategory.BUG_BOUNTY,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=60,
                    ),
                ]
            )

        return tasks

    def _generate_dev_bounty_tasks(self, guidance, experience) -> list[Task]:
        """Generar tareas de dev bounty."""
        tasks = []

        if guidance.value == "high_guidance":
            tasks.extend(
                [
                    Task(
                        task_id="db1",
                        title="Configurar entorno de dev bounty",
                        description="MERLIN te guiará en la configuración de herramientas para dev bounty",
                        category=TaskCategory.DEV_BOUNTY,
                        priority=TaskPriority.CRITICAL,
                        estimated_minutes=30,
                    ),
                    Task(
                        task_id="db2",
                        title="Explorar repositorios de código abierto",
                        description="MERLIN te mostrará cómo encontrar repositorios con programas de dev bounty",
                        category=TaskCategory.DEV_BOUNTY,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=45,
                    ),
                ]
            )
        else:
            tasks.extend(
                [
                    Task(
                        task_id="db1",
                        title="Revisar repositorios seleccionados",
                        description="Revisar repositorios activos",
                        category=TaskCategory.DEV_BOUNTY,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=30,
                    ),
                    Task(
                        task_id="db2",
                        title="Análisis de código",
                        description="Análisis de código del repositorio",
                        category=TaskCategory.DEV_BOUNTY,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=60,
                    ),
                ]
            )

        return tasks

    def _generate_data_annotation_tasks(self, guidance, experience) -> list[Task]:
        """Generar tareas de data annotation."""
        tasks = []

        if guidance.value == "high_guidance":
            tasks.extend(
                [
                    Task(
                        task_id="da1",
                        title="Explorar plataformas de data annotation",
                        description="MERLIN te mostrará las mejores plataformas para data annotation remunerada",
                        category=TaskCategory.DATA_ANNOTATION,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=30,
                    ),
                    Task(
                        task_id="da2",
                        title="Configurar cuenta en plataforma seleccionada",
                        description="MERLIN te guiará en el proceso de configuración",
                        category=TaskCategory.DATA_ANNOTATION,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=20,
                    ),
                ]
            )
        else:
            tasks.extend(
                [
                    Task(
                        task_id="da1",
                        title="Revisar tareas de annotation pendientes",
                        description="Revisar tareas disponibles",
                        category=TaskCategory.DATA_ANNOTATION,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=15,
                    ),
                    Task(
                        task_id="da2",
                        title="Completar tareas de annotation",
                        description="Completar tareas seleccionadas",
                        category=TaskCategory.DATA_ANNOTATION,
                        priority=TaskPriority.HIGH,
                        estimated_minutes=60,
                    ),
                ]
            )

        return tasks

    def _generate_learning_tasks(self, guidance) -> list[Task]:
        """Generar tareas de aprendizaje."""
        tasks = [
            Task(
                task_id="learn1",
                title="Tutorial de OWASP Top 10",
                description="MERLIN te guiará en el aprendizaje de las vulnerabilidades más comunes",
                category=TaskCategory.LEARNING,
                priority=TaskPriority.MEDIUM,
                estimated_minutes=45,
            ),
            Task(
                task_id="learn2",
                title="Práctica de herramientas de seguridad",
                description="MERLIN te enseñará a usar herramientas básicas de seguridad",
                category=TaskCategory.LEARNING,
                priority=TaskPriority.MEDIUM,
                estimated_minutes=30,
            ),
        ]

        return tasks

    def _generate_planning_tasks(self, guidance) -> list[Task]:
        """Generar tareas de planificación."""
        tasks = [
            Task(
                task_id="plan1",
                title="Revisar plan del día",
                description="Revisar y ajustar el plan diario con MERLIN",
                category=TaskCategory.PLANNING,
                priority=TaskPriority.CRITICAL,
                estimated_minutes=15,
            ),
            Task(
                task_id="plan2",
                title="Registrar progreso en Obsidian",
                description="MERLIN te ayudará a registrar tu progreso en Obsidian",
                category=TaskCategory.PLANNING,
                priority=TaskPriority.MEDIUM,
                estimated_minutes=10,
            ),
        ]

        return tasks

    def _calculate_breaks(self, total_minutes: int) -> int:
        """Calcular número de breaks necesarios."""
        # Break cada 90 minutos
        return max(1, total_minutes // 90)

    def update_task_status(self, date: str, task_id: str, status: TaskStatus) -> bool:
        """Actualizar estado de tarea."""
        if date not in self.plans:
            return False

        plan = self.plans[date]
        task = next((t for t in plan.tasks if t.task_id == task_id), None)

        if not task:
            return False

        task.status = status

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now().isoformat()
            plan.total_completed_minutes += task.estimated_minutes
        elif status == TaskStatus.IN_PROGRESS:
            plan.total_completed_minutes += 10  # Add 10 minutes for starting

        # Recalcular progreso
        plan.progress_percentage = (
            (plan.total_completed_minutes / plan.total_estimated_minutes) * 100
            if plan.total_estimated_minutes > 0
            else 0
        )

        self._save_plan(plan)
        return True

    def add_break(self, date: str) -> bool:
        """Agregar break al plan."""
        if date not in self.plans:
            return False

        plan = self.plans[date]
        plan.breaks_taken += 1

        self._save_plan(plan)
        return True

    def get_daily_plan(self, date: datetime | None = None) -> DailyPlan | None:
        """Obtener plan diario."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")

        if date_str not in self.plans:
            return self.generate_daily_plan(date)

        return self.plans[date_str]

    def get_productivity_metrics(self, date: datetime | None = None) -> ProductivityMetrics:
        """Obtener métricas de productividad."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        plan = self.get_daily_plan(date)

        if not plan:
            return ProductivityMetrics(date=date_str)

        tasks_completed = len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])
        tasks_total = len(plan.tasks)

        return ProductivityMetrics(
            date=date_str,
            tasks_completed=tasks_completed,
            tasks_total=tasks_total,
            focus_hours=plan.total_completed_minutes / 60,
            break_hours=plan.breaks_taken * 15 / 60,  # Assume 15 min breaks
            efficiency_score=plan.progress_percentage,
        )

    def sync_with_obsidian(self, date: datetime | None = None) -> bool:
        """Sincronizar plan con Obsidian."""
        if not self.personalization.profile.obsidian_enabled:
            return False

        plan = self.get_daily_plan(date)
        if not plan:
            return False

        # Crear nota diaria con el plan
        content = self._format_plan_for_obsidian(plan)
        self.obsidian.append_to_daily_note(content, date)

        return True

    def _format_plan_for_obsidian(self, plan: DailyPlan) -> str:
        """Formatear plan para Obsidian."""

        content = f"""

## 📋 Plan del Día

### ✅ Tareas ({len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])}/{len(plan.tasks)})

"""

        for task in plan.tasks:
            status_emoji = (
                "✅" if task.status == TaskStatus.COMPLETED else "⏳" if task.status == TaskStatus.IN_PROGRESS else "⬜"
            )
            content += f"- {status_emoji} **{task.title}** ({task.category.value})\n"
            if task.notes:
                content += f"  - {task.notes}\n"

        content += f"\n### 📊 Progreso\n- Progreso: {plan.progress_percentage:.1f}%\n- Tiempo estimado: {plan.total_estimated_minutes} min\n- Tiempo completado: {plan.total_completed_minutes} min\n- Breaks: {plan.breaks_taken}/{plan.breaks_scheduled}\n"

        return content

    def get_weekly_summary(self) -> dict[str, Any]:
        """Obtener resumen semanal."""
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())

        total_tasks = 0
        completed_tasks = 0
        total_hours = 0.0

        for i in range(7):
            date = week_start + timedelta(days=i)
            plan = self.get_daily_plan(date)
            if plan:
                total_tasks += len(plan.tasks)
                completed_tasks += len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])
                total_hours += plan.total_completed_minutes / 60

        return {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": (week_start + timedelta(days=6)).strftime("%Y-%m-%d"),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "total_hours": total_hours,
            "avg_hours_per_day": total_hours / 7,
        }


# Singleton instance
_daily_planning_system: DailyPlanningSystem | None = None


def get_daily_planning_system() -> DailyPlanningSystem:
    """Obtener instancia singleton del sistema de planificación diaria."""
    global _daily_planning_system
    if _daily_planning_system is None:
        _daily_planning_system = DailyPlanningSystem()
    return _daily_planning_system


def reset_daily_planning_system() -> None:
    """Resetear instancia singleton."""
    global _daily_planning_system
    _daily_planning_system = None
