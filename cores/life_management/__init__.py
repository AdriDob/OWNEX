"""
Life Management Module — Módulo de Gestión de Vida Personal

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

from cores.life_management.system import (
    AdviceCategory,
    DailyMood,
    DailyRoutine,
    Goal,
    GoalCategory,
    GoalStatus,
    Habit,
    HabitEntry,
    HabitFrequency,
    HabitStatus,
    LifeManagementSystem,
    MoodLevel,
    PCUsageSession,
    PersonalizedAdvice,
    Task,
    TaskCategory,
    TaskPriority,
    TaskStatus,
    get_life_management_system,
)

__all__ = [
    "AdviceCategory",
    "DailyMood",
    "DailyRoutine",
    "Goal",
    "GoalCategory",
    "GoalStatus",
    "Habit",
    "HabitEntry",
    "HabitFrequency",
    "HabitStatus",
    "LifeManagementSystem",
    "MoodLevel",
    "PCUsageSession",
    "PersonalizedAdvice",
    "Task",
    "TaskCategory",
    "TaskPriority",
    "TaskStatus",
    "get_life_management_system",
]
