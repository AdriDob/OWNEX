"""Mega Fast Mode — modo permanente de máxima velocidad de ingresos.

Evolución del First-Time Mode. No tiene fecha de fin.
Objetivo: maximizar ingresos desde el día 1 y para siempre.

Características:
- Metas agresivas que escalan con el rendimiento
- Auto-ajuste basado en resultados reales
- Priorización dinámica de plataformas
- Milestones de crecimiento
- Nunca se detiene, siempre optimiza

Uso:
    python go --mega-fast          # Activar
    python go --mega-fast-status   # Ver progreso
    python go --mega-fast-plan     # Plan del día
    python go --mega-fast-stop     # Desactivar
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("orion.mega_fast")


# ── Configuración Mega Fast ──────────────────────────────────────

MEGA_FAST_CONFIG = {
    # Metas escalables (se ajustan solas basado en rendimiento)
    "initial_weekly_goal": 1500,
    "current_weekly_goal": 1500,
    "max_weekly_goal": 10000,
    "growth_rate": 1.2,  # 20% más cada semana si se cumple la meta
    # Metas diarias agresivas
    "daily_goals": {
        "pulse_tasks": 10,
        "forge_bounties": 3,
        "bb_submissions": 2,
        "new_platforms": 1,
    },
    # Plataformas con mayor ROI primero
    "platform_priority": [
        {"name": "outlier", "type": "pulse", "roi": "$$$", "speed": "24h"},
        {"name": "dataannotation", "type": "pulse", "roi": "$$$", "speed": "24h"},
        {"name": "remotasks", "type": "pulse", "roi": "$$", "speed": "24h"},
        {"name": "immunefi", "type": "bb", "roi": "$$$$$", "speed": "1-2w"},
        {"name": "intigriti", "type": "bb", "roi": "$$$$", "speed": "2-3w"},
        {"name": "superteam", "type": "forge", "roi": "$$$$", "speed": "1-2w"},
        {"name": "opire", "type": "forge", "roi": "$$$", "speed": "1-2w"},
        {"name": "algora", "type": "forge", "roi": "$$$", "speed": "1-2w"},
        {"name": "gitcoin", "type": "forge", "roi": "$$$", "speed": "1-2w"},
    ],
    # Auto-submit agresivo
    "auto_submit_threshold": 65,  # Más permisivo = más submissions
    # Milestones de crecimiento
    "milestones": [
        {"week": 1, "goal": 1500, "reward": "🎉 Primera semana!"},
        {"week": 2, "goal": 2000, "reward": "🚀 Escalando!"},
        {"week": 3, "goal": 2500, "reward": "💪 Momento!"},
        {"week": 4, "goal": 3000, "reward": "🔥 $12k mes 1!"},
        {"week": 8, "goal": 5000, "reward": "💎 $20k mes 2!"},
        {"week": 12, "goal": 7500, "reward": "👑 $30k mes 3!"},
        {"week": 24, "goal": 10000, "reason": "🏆 $40k/mes sostenido!"},
    ],
    # Horas diarias de trabajo activo
    "active_hours": 3,  # Vos trabajás 3h, OWNEX trabaja 21h
    # Auto-ajuste
    "auto_adjust": True,
    "scale_up_if_hit": True,
    "scale_down_if_miss": False,  # Nunca bajar la meta
}


class MegaFastMode:
    """Modo permanente de máxima velocidad de ingresos."""

    def __init__(self) -> None:
        self._config = MEGA_FAST_CONFIG.copy()
        self._data_dir = os.path.expanduser("~/.config/ownex/mega_fast/")
        os.makedirs(self._data_dir, exist_ok=True)
        self._start_date = datetime.now(UTC)
        self._progress: dict[str, Any] = {}
        self._weekly_results: list[dict[str, Any]] = []

    @property
    def is_active(self) -> bool:
        flag_file = os.path.join(self._data_dir, ".active")
        return os.path.exists(flag_file)

    def activate(self) -> dict[str, Any]:
        """Activar Mega Fast Mode."""
        flag_file = os.path.join(self._data_dir, ".active")
        with open(flag_file, "w") as f:
            f.write(datetime.now(UTC).isoformat())

        config_file = os.path.join(self._data_dir, "config.json")
        with open(config_file, "w") as f:
            json.dump(self._config, f, indent=2)

        os.environ["CATEYE_AUTO_SUBMIT_THRESHOLD"] = str(self._config["auto_submit_threshold"])
        os.environ["RASTRO_MEGA_FAST_MODE"] = "1"

        logger.info("[MEGA_FAST] Modo activado — Meta: $%s/semana", self._config["current_weekly_goal"])
        return {"activated": True, "config": self._config}

    def deactivate(self) -> None:
        """Desactivar Mega Fast Mode."""
        flag_file = os.path.join(self._data_dir, ".active")
        if os.path.exists(flag_file):
            os.remove(flag_file)
        os.environ.pop("CATEYE_AUTO_SUBMIT_THRESHOLD", None)
        os.environ.pop("RASTRO_MEGA_FAST_MODE", None)

    def get_week_number(self) -> int:
        """Obtener número de semana."""
        days = (datetime.now(UTC) - self._start_date).days
        return (days // 7) + 1

    def get_current_goal(self) -> float:
        """Obtener meta semanal actual (auto-ajustada)."""
        return self._config["current_weekly_goal"]

    def adjust_goal(self, week_revenue: float) -> dict[str, Any]:
        """Auto-ajustar meta basado en rendimiento."""
        current_goal = self._config["current_weekly_goal"]
        hit_goal = week_revenue >= current_goal

        result = {
            "week": self.get_week_number(),
            "revenue": week_revenue,
            "goal": current_goal,
            "hit": hit_goal,
            "previous_goal": current_goal,
        }

        if hit_goal and self._config["scale_up_if_hit"]:
            # Subir meta 20%
            new_goal = min(
                current_goal * self._config["growth_rate"],
                self._config["max_weekly_goal"],
            )
            self._config["current_weekly_goal"] = round(new_goal, 2)
            result["new_goal"] = self._config["current_weekly_goal"]
            result["scaled"] = "up"
        else:
            result["new_goal"] = current_goal
            result["scaled"] = "same"

        # Guardar resultado semanal
        self._weekly_results.append(result)
        self._save_progress()

        return result

    def get_milestone(self) -> dict[str, Any]:
        """Obtener milestone actual."""
        week = self.get_week_number()
        for m in self._config["milestones"]:
            if week <= m["week"]:
                return {**m, "weeks_remaining": m["week"] - week}
        # Si pasó todos los milestones, usar el último
        return {**self._config["milestones"][-1], "weeks_remaining": 0, "completed_all": True}

    def record_daily(self, category: str, count: int, revenue: float) -> None:
        """Registrar progreso diario."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        if today not in self._progress:
            self._progress[today] = {
                "pulse_tasks": 0,
                "pulse_revenue": 0.0,
                "forge_bounties": 0,
                "forge_revenue": 0.0,
                "bb_submissions": 0,
                "bb_revenue": 0.0,
                "total_revenue": 0.0,
            }

        self._progress[today][category] = self._progress[today].get(category, 0) + count
        if revenue > 0:
            rev_key = f"{category}_revenue"
            self._progress[today][rev_key] = self._progress[today].get(rev_key, 0) + revenue
            self._progress[today]["total_revenue"] += revenue

        self._save_progress()

    def _save_progress(self) -> None:
        """Guardar progreso a disco."""
        data = {
            "start_date": self._start_date.isoformat(),
            "config": self._config,
            "daily": self._progress,
            "weekly": self._weekly_results,
        }
        with open(os.path.join(self._data_dir, "data.json"), "w") as f:
            json.dump(data, f, indent=2, default=str)

    def get_status(self) -> dict[str, Any]:
        """Obtener estado completo."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        today_prog = self._progress.get(today, {})

        # Totales
        total_rev = sum(d.get("total_revenue", 0) for d in self._progress.values())
        total_pulse = sum(d.get("pulse_tasks", 0) for d in self._progress.values())
        total_forge = sum(d.get("forge_bounties", 0) for d in self._progress.values())
        total_bb = sum(d.get("bb_submissions", 0) for d in self._progress.values())

        # Progreso semanal
        week_start = datetime.now(UTC) - timedelta(days=datetime.now(UTC).weekday())
        week_revenue = sum(
            d.get("total_revenue", 0)
            for date_str, d in self._progress.items()
            if datetime.fromisoformat(date_str) >= week_start
        )

        week_goal = self.get_current_goal()
        days_elapsed = datetime.now(UTC).weekday() + 1

        return {
            "active": self.is_active,
            "week": self.get_week_number(),
            "week_goal": week_goal,
            "week_revenue": round(week_revenue, 2),
            "week_progress": round(week_revenue / week_goal * 100, 1) if week_goal > 0 else 0,
            "days_elapsed": days_elapsed,
            "on_track": week_revenue >= (week_goal * (days_elapsed / 7)),
            "milestone": self.get_milestone(),
            "today": today_prog,
            "totals": {
                "revenue": round(total_rev, 2),
                "pulse_tasks": total_pulse,
                "forge_bounties": total_forge,
                "bb_submissions": total_bb,
            },
            "daily_goal": self._config["daily_goals"],
        }

    def get_daily_plan(self) -> dict[str, Any]:
        """Generar plan del día."""
        status = self.get_status()
        actions = []

        today = status.get("today", {})
        goals = status.get("daily_goal", {})

        # Pulse
        pulse_done = today.get("pulse_tasks", 0)
        pulse_goal = goals.get("pulse_tasks", 10)
        if pulse_done < pulse_goal:
            actions.append(
                {
                    "priority": 1,
                    "action": "Pulse tasks",
                    "remaining": pulse_goal - pulse_done,
                    "estimated": (pulse_goal - pulse_done) * 15,
                }
            )

        # Forge
        forge_done = today.get("forge_bounties", 0)
        forge_goal = goals.get("forge_bounties", 3)
        if forge_done < forge_goal:
            actions.append(
                {
                    "priority": 2,
                    "action": "Forge bounties",
                    "remaining": forge_goal - forge_done,
                    "estimated": (forge_goal - forge_done) * 200,
                }
            )

        # BB
        bb_done = today.get("bb_submissions", 0)
        bb_goal = goals.get("bb_submissions", 2)
        if bb_done < bb_goal:
            actions.append(
                {
                    "priority": 3,
                    "action": "BB submissions",
                    "remaining": bb_goal - bb_done,
                    "estimated": (bb_goal - bb_done) * 500,
                }
            )

        return {
            "date": datetime.now(UTC).strftime("%Y-%m-%d"),
            "week": status["week"],
            "week_goal": status["week_goal"],
            "actions": sorted(actions, key=lambda x: x["priority"]),
            "estimated_daily": sum(a.get("estimated", 0) for a in actions),
            "milestone": status.get("milestone", {}),
        }


# ── Singleton ─────────────────────────────────────────────────────

_mega_fast: MegaFastMode | None = None


def get_mega_fast() -> MegaFastMode:
    """Get singleton MegaFastMode."""
    global _mega_fast
    if _mega_fast is None:
        _mega_fast = MegaFastMode()
    return _mega_fast


# ── CLI ───────────────────────────────────────────────────────────


def cmd_activate() -> int:
    mode = get_mega_fast()
    result = mode.activate()

    print("\n" + "=" * 60)
    print("  🚀 MEGA FAST MODE — ACTIVADO")
    print("=" * 60)
    print(f"\n  Meta semanal inicial: ${result['config']['current_weekly_goal']}")
    print(f"  Meta máxima: ${result['config']['max_weekly_goal']}")
    print(f"  Crecimiento: {int((result['config']['growth_rate'] - 1) * 100)}% por semana si cumplís")
    print("\n  Milestones:")
    for m in result["config"]["milestones"]:
        print(f"    Semana {m['week']}: ${m['goal']} — {m.get('reward', m.get('reason', ''))}")
    print("\n  Comandos:")
    print("    python go --mega-fast-status   # Progreso")
    print("    python go --mega-fast-plan     # Plan del día")
    print("    python go --mega-fast-stop     # Desactivar")
    print("=" * 60)
    return 0


def cmd_status() -> int:
    mode = get_mega_fast()
    s = mode.get_status()

    if not s.get("active"):
        print("❌ Mega Fast Mode no está activo. Ejecutá: python go --mega-fast")
        return 1

    print("\n" + "=" * 60)
    print("  📊 MEGA FAST MODE — Progreso")
    print("=" * 60)
    print(f"\n  Semana: {s['week']}")
    print(f"  Meta: ${s['week_goal']}")
    print(f"  Revenue semana: ${s['week_revenue']} ({s['week_progress']}%)")
    print(f"  En camino: {'✅' if s['on_track'] else '⚠️'}")

    m = s.get("milestone", {})
    print(f"\n  Milestone: {m.get('reward', m.get('reason', ''))}")
    if m.get("weeks_remaining", 0) > 0:
        print(f"  Semanas para próximo: {m['weeks_remaining']}")

    t = s.get("totals", {})
    print("\n  Totales:")
    print(f"    💰 ${t.get('revenue', 0):.2f}")
    print(f"    ⚡ Pulse: {t.get('pulse_tasks', 0)}")
    print(f"    🔨 Forge: {t.get('forge_bounties', 0)}")
    print(f"    🎯 BB: {t.get('bb_submissions', 0)}")
    print("=" * 60)
    return 0


def cmd_plan() -> int:
    mode = get_mega_fast()
    plan = mode.get_daily_plan()

    print("\n" + "=" * 60)
    print(f"  📅 PLAN — {plan['date']}")
    print("=" * 60)
    print(f"\n  Semana {plan['week']} | Meta: ${plan['week_goal']}")
    print(f"  Estimado hoy: ${plan['estimated_daily']:.0f}")

    for a in plan["actions"]:
        print(f"    {a['priority']}. {a['action']}: {a['remaining']} restantes (~${a['estimated']})")

    m = plan.get("milestone", {})
    if m:
        print(f"\n  🎯 {m.get('reward', '')}")
    print("=" * 60)
    return 0


def cmd_stop() -> int:
    mode = get_mega_fast()
    mode.deactivate()
    print("✅ Mega Fast Mode desactivado.")
    return 0
