"""
Life Management System — Sistema de Gestión de Vida Personal

Módulo para acompañar la vida personal diaria del usuario con:
- Task Management extendido
- Calendar Integration (Google, Outlook)
- Goal Setting & Tracking (metas a largo plazo)
- Habit Tracking (hábitos diarios)
- Psychological Support System (consejos, motivación)
- Daily Routine Organizer
- PC Usage Tracking (tiempo de uso, productividad)
- Personalized Advice Engine
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.life_management")


class TaskPriority(Enum):
    """Prioridad de tarea."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(Enum):
    """Estado de tarea."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskCategory(Enum):
    """Categoría de tarea."""
    WORK = "work"
    PERSONAL = "personal"
    HEALTH = "health"
    FINANCE = "finance"
    LEARNING = "learning"
    SOCIAL = "social"
    HOME = "home"
    HOBBY = "hobby"


class GoalCategory(Enum):
    """Categoría de meta."""
    CAREER = "career"
    FINANCE = "finance"
    HEALTH = "health"
    RELATIONSHIPS = "relationships"
    PERSONAL_GROWTH = "personal_growth"
    SKILLS = "skills"
    TRAVEL = "travel"
    HOME = "home"


class GoalStatus(Enum):
    """Estado de meta."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ON_TRACK = "on_track"
    BEHIND = "behind"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class HabitFrequency(Enum):
    """Frecuencia de hábito."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class HabitStatus(Enum):
    """Estado de hábito."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MoodLevel(Enum):
    """Nivel de estado de ánimo."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class AdviceCategory(Enum):
    """Categoría de consejo."""
    PRODUCTIVITY = "productivity"
    HEALTH = "health"
    MENTAL_HEALTH = "mental_health"
    FINANCE = "finance"
    RELATIONSHIPS = "relationships"
    PERSONAL_GROWTH = "personal_growth"
    MOTIVATION = "motivation"
    SLEEP = "sleep"
    NUTRITION = "nutrition"
    EXERCISE = "exercise"


@dataclass
class Task:
    """Tarea personal extendida."""
    task_id: str
    title: str
    description: str
    category: TaskCategory
    priority: TaskPriority
    status: TaskStatus
    due_date: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    estimated_minutes: int = 30
    actual_minutes: int = 0
    tags: list[str] = field(default_factory=list)
    subtasks: list[str] = field(default_factory=list)
    recurring: bool = False
    recurring_frequency: str | None = None
    reminder_enabled: bool = False
    reminder_time: str | None = None
    linked_goal_id: str | None = None
    linked_habit_id: str | None = None


@dataclass
class Goal:
    """Meta a largo plazo."""
    goal_id: str
    title: str
    description: str
    category: GoalCategory
    status: GoalStatus
    target_date: datetime
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    progress_percentage: int = 0
    milestones: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    reminders: list[str] = field(default_factory=list)
    daily_focus: bool = False
    vision_board: bool = False
    journaling: bool = False


@dataclass
class Habit:
    """Hábito diario."""
    habit_id: str
    title: str
    description: str
    frequency: HabitFrequency
    status: HabitStatus
    created_at: datetime = field(default_factory=datetime.now)
    streak_days: int = 0
    best_streak: int = 0
    completed_dates: list[str] = field(default_factory=list)
    target_days: list[str] = field(default_factory=list)
    target_time: str | None = None
    reminder_enabled: bool = True
    linked_goal_id: str | None = None
    triggers: list[str] = field(default_factory=list)
    rewards: list[str] = field(default_factory=list)
    difficulty: str = "medium"  # easy, medium, hard


@dataclass
class HabitEntry:
    """Entrada de hábito diario."""
    entry_id: str
    habit_id: str
    date: str
    completed: bool
    mood_before: MoodLevel | None = None
    mood_after: MoodLevel | None = None
    notes: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DailyMood:
    """Estado de ánimo diario."""
    date: str
    mood_morning: MoodLevel | None = None
    mood_afternoon: MoodLevel | None = None
    mood_evening: MoodLevel | None = None
    mood_night: MoodLevel | None = None
    energy_level: int = 5  # 1-10
    stress_level: int = 5  # 1-10
    sleep_quality: int = 5  # 1-10
    notes: str = ""
    gratitude: list[str] = field(default_factory=list)
    challenges: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)


@dataclass
class DailyRoutine:
    """Rutina diaria."""
    routine_id: str
    title: str
    date: str
    wake_up_time: str
    sleep_time: str
    meals: list[dict[str, Any]] = field(default_factory=list)
    work_blocks: list[dict[str, Any]] = field(default_factory=list)
    break_times: list[dict[str, Any]] = field(default_factory=list)
    exercise_time: str | None = None
    learning_time: str | None = None
    social_time: str | None = None
    relaxation_time: str | None = None
    actual_wake_up: str | None = None
    actual_sleep: str | None = None
    adherence_score: int = 0


@dataclass
class PCUsageSession:
    """Sesión de uso de PC."""
    session_id: str
    start_time: datetime
    end_time: datetime | None = None
    duration_minutes: int = 0
    applications: list[str] = field(default_factory=list)
    category: str = "work"  # work, entertainment, learning, other
    productivity_score: int = 5  # 1-10
    task_completed: bool = False
    distractions: list[str] = field(default_factory=list)


@dataclass
class PersonalizedAdvice:
    """Consejo personalizado."""
    advice_id: str
    category: AdviceCategory
    title: str
    content: str
    relevance_score: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    action_items: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


class LifeManagementSystem:
    """Sistema de gestión de vida personal."""

    def __init__(self, user_id: str, storage_path: str):
        """Inicializar sistema de gestión de vida."""
        self.user_id = user_id
        self.storage_path = storage_path

        # Cargar datos existentes
        self.tasks: dict[str, Task] = {}
        self.goals: dict[str, Goal] = {}
        self.habits: dict[str, Habit] = {}
        self.habit_entries: dict[str, HabitEntry] = {}
        self.daily_moods: dict[str, DailyMood] = {}
        self.daily_routines: dict[str, DailyRoutine] = {}
        self.pc_usage: dict[str, PCUsageSession] = {}
        self.advices: dict[str, PersonalizedAdvice] = {}

        self._load_data()

    def _load_data(self) -> None:
        """Cargar datos desde almacenamiento."""
        # Implementar carga desde JSON o base de datos
        pass

    def _save_data(self) -> None:
        """Guardar datos a almacenamiento."""
        # Implementar guardado a JSON o base de datos
        pass

    # ============ TASK MANAGEMENT ============

    def create_task(
        self,
        title: str,
        description: str,
        category: TaskCategory,
        priority: TaskPriority,
        due_date: datetime | None = None,
        estimated_minutes: int = 30,
        tags: list[str] | None = None,
        recurring: bool = False,
        recurring_frequency: str | None = None,
        linked_goal_id: str | None = None,
        linked_habit_id: str | None = None,
    ) -> Task:
        """Crear nueva tarea."""
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=TaskStatus.PENDING,
            due_date=due_date,
            estimated_minutes=estimated_minutes,
            tags=tags or [],
            recurring=recurring,
            recurring_frequency=recurring_frequency,
            linked_goal_id=linked_goal_id,
            linked_habit_id=linked_habit_id,
        )

        self.tasks[task_id] = task
        self._save_data()

        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Actualizar estado de tarea."""
        if task_id not in self.tasks:
            return False

        self.tasks[task_id].status = status

        if status == TaskStatus.COMPLETED:
            self.tasks[task_id].completed_at = datetime.now()

        self._save_data()
        return True

    def get_tasks_by_date(self, date: datetime) -> list[Task]:
        """Obtener tareas para una fecha específica."""
        date_str = date.strftime("%Y-%m-%d")
        return [
            task for task in self.tasks.values()
            if task.due_date and task.due_date.strftime("%Y-%m-%d") == date_str
        ]

    def get_tasks_by_priority(self, priority: TaskPriority) -> list[Task]:
        """Obtener tareas por prioridad."""
        return [task for task in self.tasks.values() if task.priority == priority]

    def get_tasks_by_category(self, category: TaskCategory) -> list[Task]:
        """Obtener tareas por categoría."""
        return [task for task in self.tasks.values() if task.category == category]

    # ============ GOAL MANAGEMENT ============

    def create_goal(
        self,
        title: str,
        description: str,
        category: GoalCategory,
        target_date: datetime,
        milestones: list[str] | None = None,
        daily_focus: bool = False,
        vision_board: bool = False,
        journaling: bool = False,
    ) -> Goal:
        """Crear nueva meta a largo plazo."""
        goal_id = f"goal_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        goal = Goal(
            goal_id=goal_id,
            title=title,
            description=description,
            category=category,
            status=GoalStatus.NOT_STARTED,
            target_date=target_date,
            milestones=milestones or [],
            daily_focus=daily_focus,
            vision_board=vision_board,
            journaling=journaling,
        )

        self.goals[goal_id] = goal
        self._save_data()

        return goal

    def update_goal_progress(self, goal_id: str, progress: int) -> bool:
        """Actualizar progreso de meta."""
        if goal_id not in self.goals:
            return False

        self.goals[goal_id].progress_percentage = progress

        if progress == 100:
            self.goals[goal_id].status = GoalStatus.COMPLETED
            self.goals[goal_id].completed_at = datetime.now()
        elif progress > 0:
            self.goals[goal_id].status = GoalStatus.IN_PROGRESS

        self._save_data()
        return True

    def get_active_goals(self) -> list[Goal]:
        """Obtener metas activas."""
        return [
            goal for goal in self.goals.values()
            if goal.status in [GoalStatus.NOT_STARTED, GoalStatus.IN_PROGRESS, GoalStatus.ON_TRACK]
        ]

    def get_goals_by_category(self, category: GoalCategory) -> list[Goal]:
        """Obtener metas por categoría."""
        return [goal for goal in self.goals.values() if goal.category == category]

    # ============ HABIT TRACKING ============

    def create_habit(
        self,
        title: str,
        description: str,
        frequency: HabitFrequency,
        target_time: str | None = None,
        linked_goal_id: str | None = None,
        difficulty: str = "medium",
    ) -> Habit:
        """Crear nuevo hábito."""
        habit_id = f"habit_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        habit = Habit(
            habit_id=habit_id,
            title=title,
            description=description,
            frequency=frequency,
            status=HabitStatus.ACTIVE,
            target_time=target_time,
            linked_goal_id=linked_goal_id,
            difficulty=difficulty,
        )

        self.habits[habit_id] = habit
        self._save_data()

        return habit

    def log_habit_entry(
        self,
        habit_id: str,
        completed: bool,
        mood_before: MoodLevel | None = None,
        mood_after: MoodLevel | None = None,
        notes: str = "",
    ) -> HabitEntry:
        """Registrar entrada de hábito."""
        entry_id = f"entry_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        date = datetime.now().strftime("%Y-%m-%d")

        entry = HabitEntry(
            entry_id=entry_id,
            habit_id=habit_id,
            date=date,
            completed=completed,
            mood_before=mood_before,
            mood_after=mood_after,
            notes=notes,
        )

        self.habit_entries[entry_id] = entry

        # Actualizar streak del hábito
        if completed and habit_id in self.habits:
            habit = self.habits[habit_id]
            if date not in habit.completed_dates:
                habit.completed_dates.append(date)
                habit.streak_days += 1
                if habit.streak_days > habit.best_streak:
                    habit.best_streak = habit.streak_days

        self._save_data()
        return entry

    def get_habit_streak(self, habit_id: str) -> int:
        """Obtener streak de hábito."""
        if habit_id not in self.habits:
            return 0
        return self.habits[habit_id].streak_days

    def get_active_habits(self) -> list[Habit]:
        """Obtener hábitos activos."""
        return [habit for habit in self.habits.values() if habit.status == HabitStatus.ACTIVE]

    # ============ DAILY MOOD TRACKING ============

    def log_daily_mood(
        self,
        mood_morning: MoodLevel | None = None,
        mood_afternoon: MoodLevel | None = None,
        mood_evening: MoodLevel | None = None,
        mood_night: MoodLevel | None = None,
        energy_level: int = 5,
        stress_level: int = 5,
        sleep_quality: int = 5,
        notes: str = "",
        gratitude: list[str] | None = None,
        challenges: list[str] | None = None,
        achievements: list[str] | None = None,
    ) -> DailyMood:
        """Registrar estado de ánimo diario."""
        date = datetime.now().strftime("%Y-%m-%d")

        daily_mood = DailyMood(
            date=date,
            mood_morning=mood_morning,
            mood_afternoon=mood_afternoon,
            mood_evening=mood_evening,
            mood_night=mood_night,
            energy_level=energy_level,
            stress_level=stress_level,
            sleep_quality=sleep_quality,
            notes=notes,
            gratitude=gratitude or [],
            challenges=challenges or [],
            achievements=achievements or [],
        )

        self.daily_moods[date] = daily_mood
        self._save_data()

        return daily_mood

    def get_mood_trends(self, days: int = 7) -> dict[str, Any]:
        """Obtener tendencias de estado de ánimo."""
        trends = {
            "average_mood": [],
            "average_energy": [],
            "average_stress": [],
            "average_sleep": [],
        }

        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self.daily_moods:
                mood = self.daily_moods[date]
                trends["average_mood"].append(mood.energy_level)
                trends["average_energy"].append(mood.energy_level)
                trends["average_stress"].append(mood.stress_level)
                trends["average_sleep"].append(mood.sleep_quality)

        return trends

    # ============ PERSONALIZED ADVICE ============

    def generate_advice(
        self,
        category: AdviceCategory,
        context: dict[str, Any] | None = None,
    ) -> PersonalizedAdvice:
        """Generar consejo personalizado."""
        advice_id = f"advice_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Aquí integraríamos con MERLIN para generar consejos personalizados
        # Por ahora, usar consejos predefinidos

        advice_content = self._get_advice_content(category, context)

        advice = PersonalizedAdvice(
            advice_id=advice_id,
            category=category,
            title=advice_content["title"],
            content=advice_content["content"],
            relevance_score=advice_content["relevance_score"],
            context=context or {},
            action_items=advice_content["action_items"],
            resources=advice_content["resources"],
        )

        self.advices[advice_id] = advice
        self._save_data()

        return advice

    def _get_advice_content(self, category: AdviceCategory, context: dict[str, Any]) -> dict[str, Any]:
        """Obtener contenido de consejo basado en categoría y contexto."""
        # Implementar lógica de generación de consejos
        # Por ahora, retornar consejo genérico
        return {
            "title": f"Consejo de {category.value}",
            "content": "Contenido del consejo...",
            "relevance_score": 80,
            "action_items": ["Item 1", "Item 2"],
            "resources": ["Recurso 1", "Recurso 2"],
        }

    def get_advice_for_today(self) -> list[PersonalizedAdvice]:
        """Obtener consejos del día basados en contexto actual."""
        # Analizar estado de ánimo, tareas pendientes, hábitos, etc.
        # Generar consejos relevantes
        return []

    # ============ PC USAGE TRACKING ============

    def start_pc_session(self, category: str = "work") -> PCUsageSession:
        """Iniciar sesión de uso de PC."""
        session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        session = PCUsageSession(
            session_id=session_id,
            start_time=datetime.now(),
            category=category,
        )

        self.pc_usage[session_id] = session
        self._save_data()

        return session

    def end_pc_session(
        self,
        session_id: str,
        productivity_score: int = 5,
        task_completed: bool = False,
        distractions: list[str] | None = None,
    ) -> bool:
        """Finalizar sesión de uso de PC."""
        if session_id not in self.pc_usage:
            return False

        session = self.pc_usage[session_id]
        session.end_time = datetime.now()
        session.duration_minutes = int((session.end_time - session.start_time).total_seconds() / 60)
        session.productivity_score = productivity_score
        session.task_completed = task_completed
        session.distractions = distractions or []

        self._save_data()
        return True

    def get_daily_pc_usage(self, date: datetime) -> dict[str, Any]:
        """Obtener estadísticas de uso de PC para un día."""
        date_str = date.strftime("%Y-%m-%d")

        sessions = [
            session for session in self.pc_usage.values()
            if session.start_time.strftime("%Y-%m-%d") == date_str
        ]

        total_minutes = sum(session.duration_minutes for session in sessions)
        productive_minutes = sum(
            session.duration_minutes for session in sessions if session.category == "work"
        )

        return {
            "total_minutes": total_minutes,
            "productive_minutes": productive_minutes,
            "entertainment_minutes": total_minutes - productive_minutes,
            "average_productivity": sum(session.productivity_score for session in sessions) / len(sessions) if sessions else 0,
            "sessions_count": len(sessions),
        }

    # ============ INTEGRATION WITH MERLIN ============

    def get_merlin_insight(self) -> str:
        """Obtener insight de MERLIN sobre vida personal."""
        # Integrar con MERLIN para generar insights personalizados
        # Por ahora, retornar insight genérico
        return "Insight de MERLIN sobre tu vida personal..."

    def get_daily_summary(self) -> dict[str, Any]:
        """Obtener resumen diario completo."""
        date = datetime.now().strftime("%Y-%m-%d")

        tasks_pending = len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])
        tasks_completed = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])

        habits_completed = len([h for h in self.habits.values() if date in h.completed_dates])
        habits_total = len(self.habits)

        goals_progress = sum(g.progress_percentage for g in self.goals.values())

        return {
            "date": date,
            "tasks": {
                "pending": tasks_pending,
                "completed": tasks_completed,
                "total": len(self.tasks),
            },
            "habits": {
                "completed": habits_completed,
                "total": habits_total,
                "completion_rate": habits_completed / habits_total if habits_total > 0 else 0,
            },
            "goals": {
                "total_progress": goals_progress,
                "total_goals": len(self.goals),
            },
            "mood": self.daily_moods.get(date).__dict__ if date in self.daily_moods else None,
            "pc_usage": self.get_daily_pc_usage(datetime.now()),
        }


# Singleton instance
_life_management_system: LifeManagementSystem | None = None


def get_life_management_system(user_id: str = "default", storage_path: str = "~/.config/ownex/life_management") -> LifeManagementSystem:
    """Obtener instancia singleton del sistema de gestión de vida."""
    global _life_management_system

    if _life_management_system is None:
        _life_management_system = LifeManagementSystem(user_id, storage_path)

    return _life_management_system
