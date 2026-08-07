"""Daily Task Board — tareas diarias propuestas por OWNEX, desde el día 1.

OWNEX arma cada día una lista accionable de tareas guiadas, en orden, desde
el día 1 en adelante. Las tareas se derivan del estado real del sistema
(recomendaciones de guía, perfil, dev bounty, vpn, dinero) y del progreso
del operador. El operador las marca como hechas y OWNEX avanza con nuevas.

Persistencia: ~/.config/ownex/daily_tasks/state.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, date, datetime
from typing import Any

logger = logging.getLogger("core.daily_tasks")


class DailyTaskBoard:
    """Tablero de tareas diarias propuestas por OWNEX."""

    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/daily_tasks/")
        os.makedirs(self.data_dir, exist_ok=True)

    # ── Estado persistente ──

    @property
    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"started_on": None, "day": 0, "tasks": []}

    def _save(self, state: dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    # ── Inicio / día actual ──

    @property
    def _today(self) -> str:
        return date.today().isoformat()

    def ensure_started(self) -> dict[str, Any]:
        """Asegura que el tablero tenga una fecha de inicio y día >= 1."""
        state = self._load()
        if not state.get("started_on"):
            state["started_on"] = self._today
            state["day"] = 1
            logger.info("[DAILY_TASKS] Comienza el día 1: %s", state["started_on"])
        else:
            # Avanzar el día según días calendario transcurridos
            try:
                started = date.fromisoformat(state["started_on"])
                elapsed = max(0, (date.today() - started).days)
                state["day"] = max(state.get("day", 1), elapsed + 1)
            except Exception:
                state["day"] = state.get("day", 1)
        self._save(state)
        return state

    def get_day(self) -> int:
        return self.ensure_started().get("day", 1)

    # ── Generación de tareas del día ──

    def get_tasks(self, force_refresh: bool = False) -> dict[str, Any]:
        """Devuelve las tareas del día actual. Si no existen o se pide
        refresco, las genera a partir del estado real del sistema."""
        state = self.ensure_started()
        day = state.get("day", 1)
        tasks = state.get("tasks", [])

        if force_refresh or not tasks or tasks[0].get("day") != day:
            tasks = self._build_day_tasks(day)
            state["tasks"] = tasks
            self._save(state)

        done = sum(1 for t in tasks if t.get("status") == "done")
        return {
            "success": True,
            "day": day,
            "started_on": state.get("started_on"),
            "tasks": tasks,
            "progress": round(done / len(tasks)) if tasks else 0,
            "done": done,
            "total": len(tasks),
            "message": self._day_context(day),
        }

    def _build_day_tasks(self, day: int) -> list[dict[str, Any]]:
        """Construye la lista de tareas guiadas para un día concreto.

        Día 1 = arranque: vincular github, config init, explorar legal,
        definir plan. Luego un camino guiado de construcción del perfil,
        bounties y plataforma, avanzando con wave del día."""
        base: list[dict[str, Any]] = []
        base = self._day1_tasks() if day == 1 else self._ongoing_tasks(day)

        # Siempre incluye el resumen del día como tarea de cierre
        base.append(
            {
                "id": f"d{day}-summary",
                "day": day,
                "title": "Cerrar el día: registrar avance y proyección",
                "detail": "Decidir qué aprendiste y qué vas a hacer mañana.",
                "link": "/mission-control",
                "status": "pending",
            }
        )
        return base

    def _day1_tasks(self) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        order = 0

        config_steps = [
            ("Vincular tu perfil de GitHub (recibe auto-push de bounties).", "github"),
            ("Crear el repo portfolio (usuario/repo) y activar auto-push en OWNEX.", "github"),
            ("Tener GITHUB_TOKEN con scope repo disponible en vault/.env.", "github"),
            ("Definir el plan de plata objetivo (quiero $X por semana).", "plata"),
            ("Elegir plataformas de inicio: dev bounty y (si accedés) Outlier/DA.", "plataforma"),
        ]
        for topic, cat in config_steps:
            order += 1
            already = self._state_flag(cat)
            self._append_task(tasks, order, day=1, title=topic, cat=cat, done=already, link="/mission-control")

        # Recomendaciones del sistema aún no hechas (prioridad alta)
        recs = self._system_recommendations()
        for r in recs[:6]:
            order += 1
            tasks.append(
                {
                    "id": f"d1-sys-{order}",
                    "day": 1,
                    "title": r.get("action", ""),
                    "detail": r.get("why", ""),
                    "status": "pending",
                    "cat": r.get("priority", "baja"),
                    "link": "/mission-control",
                }
            )
        return tasks

    def _append_task(self, tasks: list, order: int, day: int, title: str, cat: str, done: bool, link: str) -> None:
        tasks.append(
            {
                "id": f"d{day}-{order}",
                "day": day,
                "title": title,
                "detail": "",
                "status": "done" if done else "pending",
                "cat": cat,
                "link": link,
            }
        )

    def _ongoing_tasks(self, day: int) -> list[dict[str, Any]]:
        """Tareas de días 2+ guiadas por estado real y progreso."""
        tasks: list[dict[str, Any]] = []

        # Bloque guiado por recomendaciones reales del sistema
        for order, r in enumerate(self._system_recommendations(), start=1):
            tasks.append(
                {
                    "id": f"d{day}-r{order}",
                    "day": day,
                    "title": r.get("action", ""),
                    "detail": r.get("why", ""),
                    "cat": r.get("priority", "media"),
                    "status": "pending",
                    "link": "/mission-control",
                }
            )
        try:
            from core.profile_builder import get_profile_builder

            status = get_profile_builder().get_status()
            if status.get("score", 0) < 60:
                tasks.append(
                    {
                        "id": f"d{day}-profile",
                        "day": day,
                        "title": "Subir el score del perfil de GitHub (actual: {score})".format(
                            score=status.get("score", 0)
                        ),
                        "detail": "Generá y subí el README, ajustá la bio, fijá pinned repos.",
                        "cat": status.get("linked") and "media" or "alta",
                        "status": "pending",
                        "link": "/mission-control",
                    }
                )
        except Exception:
            pass

        # Bloque progresivo: cada día nuevo OWNEX sugiere 1 bounty apto
        # (ratcheting: el auto-push suma commits al fetch del día)
        tasks.append(
            {
                "id": f"d{day}-bounty",
                "day": day,
                "title": f"Aprobar tu bounty del día #{day} del autopilot",
                "detail": "En el autopilot toca 'Descubrir' y valida el mejor para hoy (" + f"día {day}" + ").",
                "cat": "media",
                "status": "pending",
                "link": "/mission-control",
            }
        )

        # Balance semanal: semana 1 = nota de dinero
        if day % 7 == 0 and day >= 7:
            tasks.append(
                {
                    "id": f"d{day}-money",
                    "day": day,
                    "title": "Revisar proyección semanal de plata",
                    "detail": "Abrí el Money Plan y verificá que vas al target.",
                    "cat": "media",
                    "status": "pending",
                    "link": "/mission-control",
                }
            )

        return tasks

    def _system_recommendations(self) -> list[dict[str, Any]]:
        """Recolecta recomendaciones accionables del estado real del sistema."""
        recs: list[dict[str, Any]] = []
        try:
            from core.profile_builder import get_profile_builder

            for r in get_profile_builder().recommendations():
                recs.append(
                    {"action": r.get("action", ""), "why": r.get("why", ""), "priority": r.get("priority", "media")}
                )
        except Exception:
            pass
        try:
            from core.vpn_assistant import get_vpn_assistant

            report = get_vpn_assistant().readiness_report()
            if not report.get("ready", False):
                for issue in report.get("issues", [])[:2]:
                    recs.append(
                        {
                            "action": f"Resolver VPN: {issue}",
                            "why": "Necesario para Outlier/DA (tu fuente base de plata).",
                            "priority": "alta",
                        }
                    )
        except Exception:
            pass
        try:
            from core.dev_bounty_autopilot import get_dev_bounty_autopilot

            if not get_dev_bounty_autopilot().is_active():
                recs.append(
                    {
                        "action": "Activar Dev Bounty Autopilot",
                        "why": "Descubre y prepara bounts aptos; vos solo validás.",
                        "priority": "alta",
                    }
                )
            else:
                pending = get_dev_bounty_autopilot()._count_pending_proposals()
                if pending:
                    recs.append(
                        {
                            "action": f"Validar los {pending} bounty(s) listos en el autopilot",
                            "why": "Cada one cerrado = plata real + historial en GitHub.",
                            "priority": "alta",
                        }
                    )
        except Exception:
            pass

        # ── Credential vault ──
        try:
            from core.credentials.vault import get_credentials

            creds = get_credentials()
            if not creds.github_token:
                recs.append(
                    {
                        "action": "Configurar GITHUB_TOKEN en vault",
                        "why": "Permite auditoría completa del perfil + auto-push de bounties.",
                        "priority": "alta",
                        "cat": "config",
                    }
                )
        except Exception:
            pass

        # ── Platform connectors ──
        try:
            from core.platform_connectors import get_platform_manager

            pm = get_platform_manager()
            status = pm.get_status()
            not_connected = [
                p for p, v in status.get("platforms", {}).items() if v.get("enabled") and not v.get("has_creds")
            ]
            if not_connected:
                top = not_connected[:3]
                recs.append(
                    {
                        "action": f"Configurar credenciales para: {', '.join(top)}",
                        "why": f"{len(not_connected)} plataformas habilitadas sin credentials → no pueden descubrir pagos.",
                        "priority": "alta",
                        "cat": "config",
                    }
                )
        except Exception:
            pass

        # ── Trust engine ──
        try:
            from core.trust_engine import get_trust_engine

            t = get_trust_engine()
            ts = t.get_status()
            no_trust = [p for p in ts.get("platforms_with_data", []) if p not in ts.get("high_trust_platforms", [])]
            if no_trust:
                recs.append(
                    {
                        "action": f"Build trust en: {', '.join(no_trust[:3])}",
                        "why": f"{len(no_trust)} plataformas con datos pero bajo trust → auto-approval bloqueado.",
                        "priority": "media",
                        "cat": "config",
                    }
                )
        except Exception:
            pass

        # ── Payment tracker ──
        try:
            from core.payment_tracker import get_payment_tracker

            pt = get_payment_tracker()
            pending = pt.get_pending_payments()
            if pending:
                recs.append(
                    {
                        "action": f"Confirmar {len(pending)} pago(s) pendientes",
                        "why": "Payments sin confirmar bloquean el feedback loop de trust + payout net.",
                        "priority": "alta",
                        "cat": "config",
                    }
                )
        except Exception:
            pass

        # ── Payout net ──
        try:
            from core.payout_net import get_payout_net

            pn = get_payout_net()
            ps = pn.get_status()
            if ps.get("created", 0) == 0:
                recs.append(
                    {
                        "action": "Configurar método de payout favorito (PayoutNet)",
                        "why": "Sin payout method configurado, las oportunidades no recomiendan cómo cobrar.",
                        "priority": "alta",
                        "cat": "config",
                    }
                )
        except Exception:
            pass

        # ── Goal evaluator ──
        try:
            from core.goal_evaluator import get_goal_evaluator

            ge = get_goal_evaluator()
            gs = ge.get_status()
            if gs.get("success") and not gs.get("last_eval"):
                recs.append(
                    {
                        "action": "Definir objetivo mensual de ingresos (Money Plan)",
                        "why": "Sin goals activos, OWNEX no puede priorizar oportunidades por EV.",
                        "priority": "alta",
                        "cat": "config",
                    }
                )
        except Exception:
            pass

        # ── Work bank ──
        try:
            from cores.direct_work_engine.workbank import get_workbank

            wb = get_workbank()
            items = list(wb._items.values()) if hasattr(wb, "_items") else []
            ready = len([i for i in items if getattr(i, "status", "") == "ready_to_deliver"])
            if ready > 0:
                recs.append(
                    {
                        "action": f"Preparar y entregar {ready} trabajo(s) listos",
                        "why": "Work Bank tiene items ready_to_deliver — cobrar acelera el feedback loop.",
                        "priority": "alta",
                        "cat": "config",
                    }
                )
        except Exception:
            pass

        # ── Money plan ──
        try:
            from core.money_plan import get_money_plan

            mp = get_money_plan().get()
            if not mp.get("target_set", False) and not mp.get("weekly_target"):
                recs.append(
                    {
                        "action": "Setear money plan target ($/semana) en MissionControl",
                        "why": "OWNEX prioriza oportunidades por EV; sin target no sabe qué es 'suficiente'.",
                        "priority": "media",
                        "cat": "config",
                    }
                )
        except Exception:
            pass

        return recs

    def _day_context(self, day: int) -> str:
        if day == 1:
            return "Día 1 — Hoy armamos la base: vinculá tu perfil y prepará el camino."
        if day < 5:
            return f"Día {day}: estamos cimentando — cada tarea es un ladrillo."
        if day < 15:
            return f"Día {day}: modo acción. Los bounties y tu perfil ya traccionan."
        return f"Día {day}: ritmo sostenido. OWNEX te va solventando la ruta."

    # ── Acciones del operador ──

    def update_task_status(self, task_id: str, status: str) -> dict[str, Any]:
        if status not in ("pending", "doing", "done"):
            return {"success": False, "message": "Estado inválido."}
        state = self._load()
        for t in state.get("tasks", []):
            if t.get("id") == task_id:
                t["status"] = status
                if status == "done":
                    t["completed_at"] = datetime.now(UTC).isoformat()
                self._save(state)
                return {"success": True, "task_id": task_id, "status": status}
        return {"success": False, "message": "Tarea no encontrada."}

    def advance_day(self) -> dict[str, Any]:
        """Forzar a pasar a la próximo día (prueba/modo demo)."""
        state = self._load()
        state["day"] = state.get("day", 1) + 1
        state["tasks"] = self._build_day_tasks(state["day"])
        self._save(state)
        return {"success": True, "day": state["day"], "tasks": state["tasks"]}

    def complete_done_from_state(self) -> dict[str, Any]:
        """Marca como done las tareas del día cuyo hito ya está resuelto
        en el estado real del sistema (ej. GitHub ya vinculado)."""
        state = self._load()
        marked = 0
        for t in state.get("tasks", []):
            if t.get("status") == "done":
                continue
            flag = t.get("cat", "")
            if flag and self._state_flag(flag):
                t["status"] = "done"
                t["completed_at"] = datetime.now(UTC).isoformat()
                marked += 1
        if marked:
            self._save(state)
        return {"success": True, "auto_done": marked}

    # ── Helpers ──

    def _state_flag(self, key: str) -> bool:
        """Devuelve True si el estado del sistema ya tiene el hito hecho."""
        try:
            if key == "github":
                from core.profile_builder import get_profile_builder

                return get_profile_builder().get_status().get("linked", False)
            if key == "plataforma":
                from core.dev_bounty_autopilot import get_dev_bounty_autopilot

                return get_dev_bounty_autopilot().is_active()
            if key == "vpn":
                from core.vpn_assistant import get_vpn_assistant

                r = get_vpn_assistant().readiness_report()
                return bool(r.get("ready", False))
            if key == "config":
                return bool(self._github_token())
        except Exception:
            return False

    def _github_token(self) -> str:
        try:
            from core.credentials.vault import get_credentials

            return get_credentials().github_token
        except Exception:
            return os.environ.get("GITHUB_TOKEN", "")

    def _title_for(self, action: str) -> str:
        return action

    @staticmethod
    def _day_suffix(day: int) -> str:
        return f"Día {day}"


def get_daily_task_board() -> DailyTaskBoard:
    global _board
    if _board is None:
        _board = DailyTaskBoard()
    return _board


_board: DailyTaskBoard | None = None
