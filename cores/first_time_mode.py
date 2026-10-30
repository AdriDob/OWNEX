"""First-Time Special Mode — objetivo: $1500 semana 1, $3000 primeras 3 semanas.

Este modo configura OWNEX para máximo ingreso en el corto plazo:
- Prioriza Pulse (tareas de IA que pagan en 24-72h)
- Targets de BB con triage rápido (Immunefi, Intigriti)
- Forge bounties de rápida resolución
- Metas diarias agresivas
- Auto-ajuste basado en resultados

Uso:
    python go --first-time          # Activar modo first-time
    python go --first-time-status   # Ver progreso vs metas
    python go --first-time-stop     # Volver a modo normal
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.first_time_mode")


# ── Configuración agresiva para primeras 3 semanas ────────────────

FIRST_TIME_CONFIG = {
    # Metas
    "week_1_goal": 1500,
    "week_2_goal": 1000,
    "week_3_goal": 500,
    "total_3week_goal": 3000,
    # Distribución de esfuerzo semanal (horas)
    "weekly_hours": {
        "pulse": 20,  # Tareas de IA (pago más rápido)
        "forge": 10,  # Dev bounties
        "bb_hunting": 10,  # Bug bounty
        "setup": 5,  # Configuración de cuentas
    },
    # Plataformas prioritarias (ordenadas por velocidad de pago)
    "priority_platforms": [
        # Pago más rápido primero
        {"name": "outlier", "type": "pulse", "pay_speed": "24-72h", "avg_pay": 20},
        {"name": "dataannotation", "type": "pulse", "pay_speed": "24-72h", "avg_pay": 15},
        {"name": "remotasks", "type": "pulse", "pay_speed": "24-72h", "avg_pay": 10},
        {"name": "immunefi", "type": "bb", "pay_speed": "1-2 weeks", "avg_pay": 1000},
        {"name": "intigriti", "type": "bb", "pay_speed": "2-3 weeks", "avg_pay": 500},
        {"name": "superteam", "type": "forge", "pay_speed": "1-2 weeks", "avg_pay": 300},
        {"name": "opire", "type": "forge", "pay_speed": "1-2 weeks", "avg_pay": 150},
    ],
    # Targets de BB con triage más rápido
    "fast_bb_targets": [
        {"platform": "immunefi", "slug": "solana", "domain": "solana.com", "avg_bounty": 5000},
        {"platform": "immunefi", "slug": "ethereum", "domain": "ethereum.org", "avg_bounty": 3000},
        {"platform": "intigriti", "slug": "intigriti", "domain": "intigriti.com", "avg_bounty": 500},
        {"platform": "hackerone", "slug": "hackeronepublic", "domain": "hackerone.com", "avg_bounty": 1000},
    ],
    # Metas diarias
    "daily_goals": {
        "pulse_tasks": 8,  # tareas de IA por día
        "forge_bounties": 2,  # bounties aplicados por día
        "bb_endpoints": 50,  # endpoints escaneados por día
        "submissions": 1,  # submissions por día
    },
    # Auto-submit agresivo (más permisivo)
    "auto_submit_threshold": 70,  # Score mínimo para auto-submit (más bajo = más submissions)
    # Notificaciones
    "notify_on_opportunity": True,
    "notify_on_payout": True,
    "notify_daily_summary": True,
}


class FirstTimeMode:
    """Modo especial para maximizar ingresos en las primeras 3 semanas."""

    def __init__(self) -> None:
        self._config = FIRST_TIME_CONFIG
        self._data_dir = os.path.expanduser("~/.config/ownex/first_time/")
        os.makedirs(self._data_dir, exist_ok=True)
        self._start_date = datetime.now(UTC)
        self._daily_progress: dict[str, Any] = {}

    @property
    def is_active(self) -> bool:
        """Check if first-time mode is active."""
        flag_file = os.path.join(self._data_dir, ".active")
        return os.path.exists(flag_file)

    def activate(self) -> dict[str, Any]:
        """Activate first-time mode."""
        flag_file = os.path.join(self._data_dir, ".active")
        with open(flag_file, "w") as f:
            f.write(datetime.now(UTC).isoformat())

        # Save config
        config_file = os.path.join(self._data_dir, "config.json")
        with open(config_file, "w") as f:
            json.dump(self._config, f, indent=2)

        # Set environment variables for aggressive mode
        os.environ["CATEYE_AUTO_SUBMIT_THRESHOLD"] = str(self._config["auto_submit_threshold"])
        os.environ["RASTRO_FIRST_TIME_MODE"] = "1"

        logger.info("[FIRST_TIME] Modo activado — Meta: $1500 semana 1")
        return {"activated": True, "config": self._config}

    def deactivate(self) -> dict[str, Any]:
        """Deactivate first-time mode."""
        flag_file = os.path.join(self._data_dir, ".active")
        if os.path.exists(flag_file):
            os.remove(flag_file)

        os.environ.pop("CATEYE_AUTO_SUBMIT_THRESHOLD", None)
        os.environ.pop("RASTRO_FIRST_TIME_MODE", None)

        logger.info("[FIRST_TIME] Modo desactivado")
        return {"deactivated": True}

    def get_week_number(self) -> int:
        """Get current week number (1-3)."""
        days_elapsed = (datetime.now(UTC) - self._start_date).days
        return min(3, (days_elapsed // 7) + 1)

    def get_week_goal(self) -> float:
        """Get the current week's goal."""
        week = self.get_week_number()
        if week == 1:
            return self._config["week_1_goal"]
        elif week == 2:
            return self._config["week_2_goal"]
        else:
            return self._config["week_3_goal"]

    def get_daily_goal(self) -> dict[str, Any]:
        """Get today's goals."""
        return {
            "pulse_tasks": self._config["daily_goals"]["pulse_tasks"],
            "forge_bounties": self._config["daily_goals"]["forge_bounties"],
            "bb_endpoints": self._config["daily_goals"]["bb_endpoints"],
            "submissions": self._config["daily_goals"]["submissions"],
        }

    def record_progress(self, category: str, amount: float, count: int = 1) -> None:
        """Record daily progress."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        if today not in self._daily_progress:
            self._daily_progress[today] = {
                "pulse_tasks": 0,
                "pulse_revenue": 0.0,
                "forge_bounties": 0,
                "forge_revenue": 0.0,
                "bb_submissions": 0,
                "bb_revenue": 0.0,
                "total_revenue": 0.0,
            }

        self._daily_progress[today][category] += count
        if amount > 0:
            self._daily_progress[today][f"{category}_revenue"] = (
                self._daily_progress[today].get(f"{category}_revenue", 0) + amount
            )
            self._daily_progress[today]["total_revenue"] += amount

        # Save to file
        progress_file = os.path.join(self._data_dir, "progress.json")
        with open(progress_file, "w") as f:
            json.dump(self._daily_progress, f, indent=2, default=str)

    def get_progress(self) -> dict[str, Any]:
        """Get full progress report."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        today_progress = self._daily_progress.get(today, {})

        # Calculate totals
        total_revenue = sum(d.get("total_revenue", 0) for d in self._daily_progress.values())
        total_pulse = sum(d.get("pulse_tasks", 0) for d in self._daily_progress.values())
        total_forge = sum(d.get("forge_bounties", 0) for d in self._daily_progress.values())
        total_bb = sum(d.get("bb_submissions", 0) for d in self._daily_progress.values())

        week_goal = self.get_week_goal()
        days_elapsed = (datetime.now(UTC) - self._start_date).days
        week_elapsed = days_elapsed % 7

        return {
            "active": self.is_active,
            "start_date": self._start_date.isoformat(),
            "days_elapsed": days_elapsed,
            "week_number": self.get_week_number(),
            "week_goal": week_goal,
            "week_elapsed_days": week_elapsed,
            "today": today_progress,
            "totals": {
                "revenue": round(total_revenue, 2),
                "pulse_tasks": total_pulse,
                "forge_bounties": total_forge,
                "bb_submissions": total_bb,
            },
            "progress_to_goal": round(total_revenue / week_goal * 100, 1) if week_goal > 0 else 0,
            "on_track": total_revenue >= (week_goal * (week_elapsed / 7)),
            "daily_goal": self.get_daily_goal(),
        }

    def get_priority_actions(self) -> list[dict[str, Any]]:
        """Get priority actions for today."""
        progress = self.get_progress()
        actions = []

        today = progress.get("today", {})
        daily_goal = progress.get("daily_goal", {})

        # Check pulse tasks
        pulse_done = today.get("pulse_tasks", 0)
        pulse_goal = daily_goal.get("pulse_tasks", 8)
        if pulse_done < pulse_goal:
            actions.append(
                {
                    "priority": 1,
                    "action": "Completar tareas de Pulse",
                    "remaining": pulse_goal - pulse_done,
                    "platforms": ["outlier", "dataannotation", "remotasks"],
                    "estimated_revenue": (pulse_goal - pulse_done) * 15,
                }
            )

        # Check forge bounties
        forge_done = today.get("forge_bounties", 0)
        forge_goal = daily_goal.get("forge_bounties", 2)
        if forge_done < forge_goal:
            actions.append(
                {
                    "priority": 2,
                    "action": "Aplicar a Forge bounties",
                    "remaining": forge_goal - forge_done,
                    "platforms": ["superteam", "opire", "algora"],
                    "estimated_revenue": (forge_goal - forge_done) * 200,
                }
            )

        # Check BB submissions
        bb_done = today.get("bb_submissions", 0)
        bb_goal = daily_goal.get("submissions", 1)
        if bb_done < bb_goal:
            actions.append(
                {
                    "priority": 3,
                    "action": "Submitir reportes BB",
                    "remaining": bb_goal - bb_done,
                    "platforms": ["immunefi", "intigriti"],
                    "estimated_revenue": (bb_goal - bb_done) * 500,
                }
            )

        return sorted(actions, key=lambda x: x["priority"])

    def generate_daily_plan(self) -> dict[str, Any]:
        """Generate today's action plan."""
        self.get_progress()
        actions = self.get_priority_actions()

        return {
            "date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "week": self.get_week_number(),
            "week_goal": self.get_week_goal(),
            "actions": actions,
            "schedule": {
                "08:00": "Revisar dashboard + aprobar reportes",
                "09:00": "Completar 3 tareas Pulse",
                "10:00": "Aplicar a 1 Forge bounty",
                "11:00": "Escanear targets BB",
                "12:00": "Almuerzo (sistema sigue corriendo)",
                "13:00": "Completar 3 tareas Pulse",
                "14:00": "Submitir reportes listos",
                "15:00": "Aplicar a 1 Forge bounty",
                "16:00": "Completar 2 tareas Pulse",
                "17:00": "Revisión del día + plan mañana",
            },
            "estimated_daily_revenue": sum(a.get("estimated_revenue", 0) for a in actions),
        }


# ── Singleton ─────────────────────────────────────────────────────

_first_time: FirstTimeMode | None = None


def get_first_time_mode() -> FirstTimeMode:
    """Get singleton FirstTimeMode."""
    global _first_time
    if _first_time is None:
        _first_time = FirstTimeMode()
    return _first_time


# ── CLI Commands ──────────────────────────────────────────────────


def cmd_activate() -> int:
    """Activate first-time mode."""
    mode = get_first_time_mode()
    result = mode.activate()

    print("\n" + "=" * 60)
    print("  🚀 FIRST-TIME MODE ACTIVADO")
    print("=" * 60)
    print(f"\n  Meta Semana 1: ${result['config']['week_1_goal']}")
    print(f"  Meta Semana 2: ${result['config']['week_2_goal']}")
    print(f"  Meta Semana 3: ${result['config']['week_3_goal']}")
    print(f"  Meta Total 3 semanas: ${result['config']['total_3week_goal']}")
    print("\n  Plataformas prioritarias:")
    for p in result["config"]["priority_platforms"]:
        print(f"    • {p['name']} ({p['type']}) — pago: {p['avg_pay']}")
    print("\n  Metas diarias:")
    for k, v in result["config"]["daily_goals"].items():
        print(f"    • {k}: {v}")
    print("\n  Para ver progreso: python go --first-time-status")
    print("  Para plan del día: python go --first-time-plan")
    print("=" * 60)

    return 0


def cmd_status() -> int:
    """Show first-time mode status."""
    mode = get_first_time_mode()
    progress = mode.get_progress()

    if not progress.get("active"):
        print("❌ First-time mode no está activo. Ejecutá: python go --first-time")
        return 1

    print("\n" + "=" * 60)
    print("  📊 FIRST-TIME MODE — Progreso")
    print("=" * 60)
    print(f"\n  Semana: {progress['week_number']}/3")
    print(f"  Meta semana: ${progress['week_goal']}")
    print(f"  Días transcurridos: {progress['days_elapsed']}")
    print(f"  Progreso: {progress['progress_to_goal']}%")
    print(f"  En camino: {'✅' if progress['on_track'] else '⚠️'}")

    totals = progress.get("totals", {})
    print("\n  Totales acumulados:")
    print(f"    💰 Revenue: ${totals.get('revenue', 0):.2f}")
    print(f"    ⚡ Pulse tasks: {totals.get('pulse_tasks', 0)}")
    print(f"    🔨 Forge bounties: {totals.get('forge_bounties', 0)}")
    print(f"    🎯 BB submissions: {totals.get('bb_submissions', 0)}")

    today = progress.get("today", {})
    print("\n  Hoy:")
    print(f"    Pulse: {today.get('pulse_tasks', 0)}/{progress['daily_goal'].get('pulse_tasks', 8)}")
    print(f"    Forge: {today.get('forge_bounties', 0)}/{progress['daily_goal'].get('forge_bounties', 2)}")
    print(f"    BB: {today.get('bb_submissions', 0)}/{progress['daily_goal'].get('submissions', 1)}")

    print("=" * 60)
    return 0


def cmd_plan() -> int:
    """Show today's plan."""
    mode = get_first_time_mode()
    plan = mode.generate_daily_plan()

    print("\n" + "=" * 60)
    print(f"  📅 PLAN DEL DÍA — {plan['date']}")
    print("=" * 60)
    print(f"\n  Semana: {plan['week']}/3 | Meta: ${plan['week_goal']}")
    print(f"  Revenue estimado hoy: ${plan['estimated_daily_revenue']:.0f}")

    print("\n  Acciones prioritarias:")
    for action in plan["actions"]:
        print(f"    {action['priority']}. {action['action']}")
        print(f"       Restante: {action['remaining']} | Est: ${action['estimated_revenue']}")

    print("\n  Horario sugerido:")
    for time, task in plan["schedule"].items():
        print(f"    {time}: {task}")

    print("=" * 60)
    return 0


def cmd_stop() -> int:
    """Deactivate first-time mode."""
    mode = get_first_time_mode()
    mode.deactivate()
    print("✅ First-time mode desactivado. Volviste a modo normal.")
    return 0
