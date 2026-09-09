"""Life & Personal Assistant — módulo unificado de vida personal y ayuda.

Combina:
1. Gestión de tareas diarias
2. Tracking de metas y hábitos
3. Asistente personal con IA
4. Gestión de salud y bienestar
5. Aprendizaje y explicaciones
6. Integración con ingresos OWNEX
7. Planificación diaria/semanal/mensual
8. PC usage tracking
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("orion.life_assistant")


# ── Data Models ──────────────────────────────────────────────────


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    priority: str = "medium"  # low, medium, high, critical
    category: str = "work"  # work, personal, health, learning, income
    status: str = "pending"  # pending, in_progress, completed, cancelled
    due_date: str = ""
    estimated_minutes: int = 30
    completed_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    tags: list[str] = field(default_factory=list)


@dataclass
class Goal:
    id: str
    title: str
    description: str = ""
    category: str = "income"  # income, health, learning, personal, career
    target_value: float = 0.0
    current_value: float = 0.0
    unit: str = "USD"
    deadline: str = ""
    status: str = "active"  # active, completed, paused, failed
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    milestones: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Habit:
    id: str
    title: str
    description: str = ""
    frequency: str = "daily"  # daily, weekly, monthly
    target_count: int = 1
    current_streak: int = 0
    best_streak: int = 0
    completions: list[str] = field(default_factory=list)  # dates completed
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class HealthEntry:
    date: str
    sleep_hours: float = 0.0
    exercise_minutes: int = 0
    water_glasses: int = 0
    mood: str = "neutral"  # great, good, neutral, bad, terrible
    energy: int = 5  # 1-10
    notes: str = ""


@dataclass
class LearningEntry:
    id: str
    topic: str
    content: str = ""
    source: str = ""
    understanding: int = 5  # 1-10
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class PCUsage:
    date: str
    total_minutes: int = 0
    productive_minutes: int = 0
    entertainment_minutes: int = 0
    idle_minutes: int = 0
    top_apps: dict[str, int] = field(default_factory=dict)


@dataclass
class PersonalNote:
    id: str
    title: str
    content: str = ""
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ── Life Assistant ───────────────────────────────────────────────


class LifeAssistant:
    """Asistente personal unificado de vida."""

    def __init__(self) -> None:
        self._data_dir = os.path.expanduser("~/.config/ownex/life/")
        os.makedirs(self._data_dir, exist_ok=True)
        self._tasks: dict[str, Task] = {}
        self._goals: dict[str, Goal] = {}
        self._habits: dict[str, Habit] = {}
        self._health: dict[str, HealthEntry] = {}
        self._learning: dict[str, LearningEntry] = {}
        self._pc_usage: dict[str, PCUsage] = {}
        self._notes: dict[str, PersonalNote] = {}
        self._load_data()

    # ── Persistence ──────────────────────────────────────────────

    def _load_data(self) -> None:
        """Load all data from disk."""
        data_map = {
            "tasks.json": ("_tasks", Task),
            "goals.json": ("_goals", Goal),
            "habits.json": ("_habits", Habit),
            "learning.json": ("_learning", LearningEntry),
            "notes.json": ("_notes", PersonalNote),
        }
        for filename, (attr, cls) in data_map.items():
            filepath = os.path.join(self._data_dir, filename)
            if os.path.exists(filepath):
                with open(filepath) as f:
                    data = json.load(f)
                    loaded = {}
                    for item_id, item_data in data.items():
                        with contextlib.suppress(Exception):
                            loaded[item_id] = cls(**item_data)
                    setattr(self, attr, loaded)

    def _save_data(self, attr: str, filename: str) -> None:
        """Save data to disk."""
        data = getattr(self, attr, {})
        filepath = os.path.join(self._data_dir, filename)
        serializable = {k: v.__dict__ for k, v in data.items()}
        with open(filepath, "w") as f:
            json.dump(serializable, f, indent=2, default=str)

    def _save_all(self) -> None:
        """Save all data to disk."""
        self._save_data("_tasks", "tasks.json")
        self._save_data("_goals", "goals.json")
        self._save_data("_habits", "habits.json")
        self._save_data("_learning", "learning.json")
        self._save_data("_notes", "notes.json")

    # ── Tasks ─────────────────────────────────────────────────────

    def add_task(self, title: str, **kwargs: Any) -> Task:
        """Add a new task."""
        task_id = f"task_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        task = Task(id=task_id, title=title, **kwargs)
        self._tasks[task_id] = task
        self._save_data("_tasks", "tasks.json")
        return task

    def complete_task(self, task_id: str) -> Task | None:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if task:
            task.status = "completed"
            task.completed_at = datetime.now(UTC).isoformat()
            self._save_data("_tasks", "tasks.json")
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save_data("_tasks", "tasks.json")
            return True
        return False

    def get_tasks(
        self,
        status: str = "",
        category: str = "",
        priority: str = "",
    ) -> list[Task]:
        """Get tasks with optional filters."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if category:
            tasks = [t for t in tasks if t.category == category]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def get_today_tasks(self) -> list[Task]:
        """Get tasks due today or overdue."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return [t for t in self._tasks.values() if t.status == "pending" and (not t.due_date or t.due_date <= today)]

    # ── Goals ─────────────────────────────────────────────────────

    def add_goal(self, title: str, **kwargs: Any) -> Goal:
        """Add a new goal."""
        goal_id = f"goal_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        goal = Goal(id=goal_id, title=title, **kwargs)
        self._goals[goal_id] = goal
        self._save_data("_goals", "goals.json")
        return goal

    def update_goal_progress(self, goal_id: str, value: float) -> Goal | None:
        """Update goal progress."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.current_value = value
            if goal.current_value >= goal.target_value:
                goal.status = "completed"
            self._save_data("_goals", "goals.json")
        return goal

    def get_goals(self, status: str = "") -> list[Goal]:
        """Get goals with optional filter."""
        goals = list(self._goals.values())
        if status:
            goals = [g for g in goals if g.status == status]
        return goals

    # ── Habits ────────────────────────────────────────────────────

    def add_habit(self, title: str, **kwargs: Any) -> Habit:
        """Add a new habit."""
        habit_id = f"habit_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        habit = Habit(id=habit_id, title=title, **kwargs)
        self._habits[habit_id] = habit
        self._save_data("_habits", "habits.json")
        return habit

    def complete_habit(self, habit_id: str, date: str = "") -> Habit | None:
        """Mark a habit as completed for a date."""
        habit = self._habits.get(habit_id)
        if not habit:
            return None

        date = date or datetime.now(UTC).strftime("%Y-%m-%d")
        if date not in habit.completions:
            habit.completions.append(date)
            # Update streak
            if habit.frequency == "daily":
                habit.current_streak = self._calculate_streak(habit.completions)
            habit.best_streak = max(habit.best_streak, habit.current_streak)
            self._save_data("_habits", "habits.json")
        return habit

    def _calculate_streak(self, dates: list[str]) -> int:
        """Calculate current streak from completion dates."""
        if not dates:
            return 0
        sorted_dates = sorted(dates, reverse=True)
        streak = 1
        for i in range(len(sorted_dates) - 1):
            d1 = datetime.fromisoformat(sorted_dates[i])
            d2 = datetime.fromisoformat(sorted_dates[i + 1])
            if (d1 - d2).days == 1:
                streak += 1
            else:
                break
        return streak

    def get_habits(self) -> list[Habit]:
        """Get all habits."""
        return list(self._habits.values())

    def get_today_habits(self) -> list[dict[str, Any]]:
        """Get habits with today's completion status."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        result = []
        for habit in self._habits.values():
            result.append(
                {
                    "habit": habit,
                    "completed_today": today in habit.completions,
                }
            )
        return result

    # ── Health ────────────────────────────────────────────────────

    def log_health(self, **kwargs: Any) -> HealthEntry:
        """Log health data for today."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        entry = HealthEntry(date=today, **kwargs)
        self._health[today] = entry
        with open(os.path.join(self._data_dir, "health.json"), "w") as f:
            json.dump({k: v.__dict__ for k, v in self._health.items()}, f, indent=2, default=str)
        return entry

    def get_health(self, days: int = 7) -> list[HealthEntry]:
        """Get health entries for the last N days."""
        entries = []
        for i in range(days):
            date = (datetime.now(UTC) - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self._health:
                entries.append(self._health[date])
        return entries

    # ── Learning ──────────────────────────────────────────────────

    def add_learning(self, topic: str, **kwargs: Any) -> LearningEntry:
        """Add a learning entry."""
        entry_id = f"learn_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        entry = LearningEntry(id=entry_id, topic=topic, **kwargs)
        self._learning[entry_id] = entry
        self._save_data("_learning", "learning.json")
        return entry

    def get_learning(self, topic: str = "") -> list[LearningEntry]:
        """Get learning entries."""
        entries = list(self._learning.values())
        if topic:
            entries = [e for e in entries if e.topic.lower() == topic.lower()]
        return sorted(entries, key=lambda e: e.created_at, reverse=True)

    # ── Notes ─────────────────────────────────────────────────────

    def add_note(self, title: str, **kwargs: Any) -> PersonalNote:
        """Add a personal note."""
        note_id = f"note_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        note = PersonalNote(id=note_id, title=title, **kwargs)
        self._notes[note_id] = note
        self._save_data("_notes", "notes.json")
        return note

    def get_notes(self, category: str = "") -> list[PersonalNote]:
        """Get notes with optional category filter."""
        notes = list(self._notes.values())
        if category:
            notes = [n for n in notes if n.category == category]
        return sorted(notes, key=lambda n: n.updated_at, reverse=True)

    # ── Daily Summary ─────────────────────────────────────────────

    def get_daily_summary(self) -> dict[str, Any]:
        """Get a comprehensive daily summary."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        tasks_today = self.get_today_tasks()
        habits_today = self.get_today_habits()
        health_today = self._health.get(today)

        # Income goals progress
        income_goals = [g for g in self._goals.values() if g.category == "income"]
        total_income_progress = sum(g.current_value for g in income_goals)
        total_income_target = sum(g.target_value for g in income_goals)

        return {
            "date": today,
            "tasks": {
                "total": len(tasks_today),
                "pending": len([t for t in tasks_today if t.status == "pending"]),
                "completed": len([t for t in tasks_today if t.status == "completed"]),
                "tasks": [{"id": t.id, "title": t.title, "priority": t.priority} for t in tasks_today],
            },
            "habits": {
                "total": len(habits_today),
                "completed": len([h for h in habits_today if h["completed_today"]]),
                "habits": [
                    {"id": h["habit"].id, "title": h["habit"].title, "completed": h["completed_today"]}
                    for h in habits_today
                ],
            },
            "health": health_today.__dict__ if health_today else {},
            "goals": {
                "income_progress": round(total_income_progress, 2),
                "income_target": round(total_income_target, 2),
                "progress_pct": round(total_income_progress / max(total_income_target, 1) * 100, 1),
            },
            "streak": self._get_best_streak(),
        }

    def _get_best_streak(self) -> dict[str, Any]:
        """Get best current streak across all habits."""
        best = None
        best_streak = 0
        for habit in self._habits.values():
            if habit.current_streak > best_streak:
                best_streak = habit.current_streak
                best = habit
        return {
            "habit": best.title if best else "",
            "streak": best_streak,
        }

    # ── AI Assistant ──────────────────────────────────────────────

    async def ask(self, question: str, context: dict[str, Any] | None = None) -> str:
        """Ask the AI assistant a question."""
        try:
            from core.ai_worker import get_ai_worker

            worker = get_ai_worker()
            llm = worker.llm

            # Build context
            context_str = ""
            if context:
                context_str = f"Context: {json.dumps(context, indent=2, default=str)}"

            # Get daily summary for context
            summary = self.get_daily_summary()

            system = """You are OWNEX's personal life assistant. You help the user manage their life, goals, habits, and income. Be concise, actionable, and supportive. Always suggest specific next steps."""

            user = f"""User's current status:
- Tasks today: {summary["tasks"]["pending"]} pending, {summary["tasks"]["completed"]} completed
- Habits today: {summary["habits"]["completed"]}/{summary["habits"]["total"]} completed
- Income progress: ${summary["goals"]["income_progress"]} / ${summary["goals"]["income_target"]}
{context_str}

User question: {question}

Provide a helpful, actionable response."""

            response = await llm.generate(system, user, max_tokens=512, temperature=0.7)
            return response
        except Exception as e:
            return f"Assistant error: {e}. Please check AI Worker configuration."

    # ── Weekly/Monthly Planning ───────────────────────────────────

    def get_weekly_plan(self) -> dict[str, Any]:
        """Get the weekly plan."""
        today = datetime.now(UTC)
        week_start = today - timedelta(days=today.weekday())
        week_days = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        daily_plans = []
        for day in week_days:
            tasks = [t for t in self._tasks.values() if t.due_date == day and t.status == "pending"]
            daily_plans.append(
                {
                    "date": day,
                    "day_name": (week_start + timedelta(days=week_days.index(day))).strftime("%A"),
                    "tasks": len(tasks),
                    "task_titles": [t.title for t in tasks[:3]],
                }
            )

        return {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "goals": [g.__dict__ for g in self.get_goals("active")],
            "daily_plans": daily_plans,
        }


# ── Singleton ─────────────────────────────────────────────────────

_life_assistant: LifeAssistant | None = None


def get_life_assistant() -> LifeAssistant:
    """Get singleton LifeAssistant."""
    global _life_assistant
    if _life_assistant is None:
        _life_assistant = LifeAssistant()
    return _life_assistant
