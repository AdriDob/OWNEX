"""Session Manager — autoguardado de sesiones de trabajo para OWNEX.

Permite al operador dejar de trabajar en cualquier momento y recuperar
exactamente dónde se quedó al reiniciar el sistema (tarea en curso, notas de
progreso, evidencia parcial, momentum, targets referenciados).

Persistencia:
  * Principal: tabla ``work_sessions`` / ``work_session_tasks`` en SQLite
    (mismo motor que el resto de OWNEX, con WAL y busy_timeout).
  * Respaldo: archivo JSON en ``~/.config/ownex/session/state.json`` por si la
    BD no está disponible en un arranque.

Uso típico::

    from cores.session_manager import session_manager

    sess = session_manager.start_session(focus="bounty", daily_goal="Subir 2 reports")
    session_manager.set_current_task(
        "Validar hallazgo X en HackerOne",
        status="in_progress",
        notes="Revisando screenshots de /api/verdicts",
        linked_type="target",
        linked_id=12,
    )
    session_manager.save_progress(momentum=7, evidence_item={"url": "...", "note": "..."})

Al arrancar la app (ver ``api/lifespan.py``), se llama a
``session_manager.restore_or_start()`` para dejar el estado listo en el
dashboard.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from database.db import SessionLocal, engine
from database.models_sessions import WorkSession, WorkSessionTask

logger = logging.getLogger("ownex.session_manager")

FOCO_OPTIONS = ["bounty", "skill", "pulse", "recon", "writeup", "setup", "otro"]

# Carpeta de respaldo JSON (misma convención que cores/work_log.py)
_BACKUP_DIR = os.path.expanduser("~/.config/ownex/session/")
_BACKUP_PATH = os.path.join(_BACKUP_DIR, "state.json")


def _ensure_backup_dir() -> None:
    with contextlib.suppress(OSError):
        os.makedirs(_BACKUP_DIR, exist_ok=True)


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso)
    except Exception:
        return None


def _json_dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _json_load(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


class SessionManager:
    """Gestor de sesiones de trabajo con autoguardado."""

    def __init__(self) -> None:
        self._current_session_id: str | None = None
        self._ensure_tables()
        _ensure_backup_dir()

    # ── Tablas ──────────────────────────────────────────────────────────

    def _ensure_tables(self) -> None:
        """Crea las tablas de sesiones si no existen."""
        try:
            from database.db import Base

            Base.metadata.create_all(engine)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[session_manager] No se pudieron crear tablas: %s", exc)

    # ── Helpers de BD ───────────────────────────────────────────────────

    def _db(self) -> SessionLocal:
        return SessionLocal()

    def _persist_backup(self, payload: dict[str, Any]) -> None:
        """Escribe una copia de seguridad en JSON (independiente de la BD)."""
        try:
            with open(_BACKUP_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
        except OSError as exc:
            logger.warning("[session_manager] No se pudo escribir backup JSON: %s", exc)

    def _load_backup(self) -> dict[str, Any]:
        try:
            with open(_BACKUP_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    # ── API pública ─────────────────────────────────────────────────────

    def start_session(
        self,
        focus: str = "bounty",
        daily_goal: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Inicia una nueva sesión de trabajo y la marca como activa.

        Si ya hay una sesión activa, la cierra primero (ended_at) y empieza
        una nueva.
        """
        focus = focus if focus in FOCO_OPTIONS else "otro"
        now = _now()
        session_id = f"wrk-{int(now.timestamp() * 1000)}"

        with self._db() as db:
            # Cerrar sesión activa previa
            db.query(WorkSession).filter(WorkSession.status == "active").update(
                {"status": "completed", "ended_at": now}
            )
            db.commit()

            ws = WorkSession(
                session_id=session_id,
                focus=focus,
                daily_goal=daily_goal,
                started_at=now,
                status="active",
                notes=notes,
            )
            db.add(ws)
            db.commit()
            db.refresh(ws)

        self._current_session_id = session_id
        self._persist_backup(
            {
                "session_id": session_id,
                "focus": focus,
                "daily_goal": daily_goal,
                "started_at": _iso(now),
                "status": "active",
                "notes": notes,
                "current_task": None,
            }
        )
        logger.info("[session_manager] Sesión iniciada: %s (focus=%s)", session_id, focus)
        return ws.to_dict()

    def get_current_session(self) -> dict[str, Any] | None:
        """Devuelve la sesión activa, o la más reciente si no hay activa."""
        with self._db() as db:
            ws = (
                db.query(WorkSession)
                .filter(WorkSession.status == "active")
                .order_by(WorkSession.started_at.desc())
                .first()
            )
            if ws is None:
                return None
            return ws.to_dict()

    def restore_or_start(self, focus: str = "bounty", daily_goal: str | None = None) -> dict[str, Any]:
        """Restaura la última sesión o inicia una si no existe.

        Se llama al arrancar la app para que el operador continúe donde lo
        dejó.
        """
        current = self.get_current_session()
        if current is not None:
            self._current_session_id = current["session_id"]
            logger.info("[session_manager] Sesión restaurada: %s", self._current_session_id)
            return current
        return self.start_session(focus=focus, daily_goal=daily_goal)

    def set_current_task(
        self,
        title: str,
        status: str = "in_progress",
        notes: str | None = None,
        priority: str | None = "medium",
        linked_type: str | None = None,
        linked_id: int | None = None,
        momentum: int | None = None,
        targets_referenced: list[int] | None = None,
        evidence_partial: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Guarda (o crea y guarda) la tarea en curso de la sesión activa."""
        sid = session_id or self._current_session_id
        if sid is None:
            started = self.start_session(focus="bounty")
            sid = started["session_id"]

        momentum = max(1, min(10, int(momentum))) if momentum is not None else 5

        with self._db() as db:
            ws = db.query(WorkSession).filter(WorkSession.session_id == sid).first()
            if ws is None:
                raise ValueError(f"Sesión no encontrada: {sid}")

            # Cerrar tarea previa "in_progress" de esta sesión y crear la nueva
            db.query(WorkSessionTask).filter(
                WorkSessionTask.session_id == sid,
                WorkSessionTask.status == "in_progress",
            ).update({"status": "completed"})
            db.commit()

            task = WorkSessionTask(
                session_id=sid,
                title=title,
                status=status,
                priority=priority,
                notes=notes,
                linked_type=linked_type,
                linked_id=linked_id,
                momentum=momentum,
                targets_referenced=_json_dump(targets_referenced or []),
                evidence_partial=_json_dump(evidence_partial or []),
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            result = task.to_dict()

        self._persist_backup(
            {
                "session_id": sid,
                "focus": None,
                "daily_goal": None,
                "started_at": None,
                "status": "active",
                "current_task": result,
            }
        )
        logger.info("[session_manager] Tarea guardada: %s (status=%s)", title, status)
        return result

    def save_progress(
        self,
        notes: str | None = None,
        evidence_item: dict[str, Any] | None = None,
        momentum: int | None = None,
        targets_referenced: list[int] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Autoguarda progreso de la tarea actual (notas, evidencia, momentum)."""
        sid = session_id or self._current_session_id
        if sid is None:
            return {"success": False, "message": "No hay sesión activa. Usá start_session o set_current_task."}

        with self._db() as db:
            ws = db.query(WorkSession).filter(WorkSession.session_id == sid).first()
            if ws is None:
                return {"success": False, "message": "Sesión no encontrada"}

            task = (
                db.query(WorkSessionTask)
                .filter(WorkSessionTask.session_id == sid)
                .order_by(WorkSessionTask.updated_at.desc())
                .first()
            )
            if task is None:
                return {"success": False, "message": "No hay tarea en curso en esta sesión"}

            if notes is not None:
                task.notes = notes
            if momentum is not None:
                task.momentum = max(1, min(10, int(momentum)))
            if targets_referenced is not None:
                task.targets_referenced = _json_dump(targets_referenced)
            if evidence_item is not None:
                ev = _json_load(task.evidence_partial, [])
                ev.append(evidence_item)
                task.evidence_partial = _json_dump(ev)
            db.commit()
            db.refresh(task)
            result = task.to_dict()

        self._persist_backup(
            {
                "session_id": sid,
                "current_task": result,
                "saved_at": _iso(_now()),
            }
        )
        logger.info("[session_manager] Progreso guardado: sesión %s", sid)
        return {"success": True, "task": result}

    def complete_session(self, session_id: str | None = None) -> dict[str, Any]:
        """Cierra la sesión activa (ended_at + status=completed)."""
        sid = session_id or self._current_session_id
        if sid is None:
            return {"success": False, "message": "No hay sesión activa"}
        now = _now()
        with self._db() as db:
            ws = db.query(WorkSession).filter(WorkSession.session_id == sid).first()
            if ws is None:
                return {"success": False, "message": "Sesión no encontrada"}
            ws.status = "completed"
            ws.ended_at = now
            db.commit()
            db.refresh(ws)
        if self._current_session_id == sid:
            self._current_session_id = None
        self._persist_backup({"session_id": sid, "status": "completed", "ended_at": _iso(now)})
        logger.info("[session_manager] Sesión completada: %s", sid)
        return ws.to_dict()

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Lista las últimas sesiones para el dashboard."""
        with self._db() as db:
            rows = db.query(WorkSession).order_by(WorkSession.started_at.desc()).limit(max(1, min(limit, 50))).all()
            return [r.to_dict() for r in rows]

    # ── Test helper ─────────────────────────────────────────────────────

    def reset(self) -> None:
        """Borra todas las sesiones y tareas (solo para entornos de prueba)."""
        with self._db() as db:
            db.query(WorkSessionTask).delete()
            db.query(WorkSession).delete()
            db.commit()
        self._current_session_id = None

    def get_status(self) -> dict[str, Any]:
        """Resumen del estado de sesión para el dashboard (estado actual)."""
        current = self.get_current_session()
        if current is None:
            return {
                "success": True,
                "has_active_session": False,
                "message": "No hay sesión de trabajo iniciada.",
                "current_task": None,
            }
        task = None
        if current.get("current_task"):
            task = current["current_task"][-1] if isinstance(current["current_task"], list) else None
        return {
            "success": True,
            "has_active_session": True,
            "session_id": current["session_id"],
            "focus": current.get("focus"),
            "daily_goal": current.get("daily_goal"),
            "started_at": current.get("started_at"),
            "status": current.get("status"),
            "current_task": task,
        }


# Instancia singleton lista para importar desde cualquier módulo.
session_manager = SessionManager()
