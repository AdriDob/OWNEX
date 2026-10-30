"""Modelos de persistencia para el gestor de sesiones de trabajo (autoguardado).

Tablas:
  * ``work_sessions`` — una sesión de trabajo por bloque diario (fecha, foco,
    objetivo, horas, estado de finalización).
  * ``work_session_tasks`` — la tarea en curso dentro de una sesión, con notas
    de progreso y evidencia parcial, para poder recuperar exactamente dónde se
    quedó el operador tras un reinicio.

Estos modelos heredan de ``database.db.Base`` para que se creen automáticamente
junto al resto del esquema (ver ``cores.session_manager._ensure_tables``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base


class WorkSession(Base):
    """Sesión de trabajo diaria — sobrevive a reinicios del sistema."""

    __tablename__ = "work_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    focus: Mapped[str | None] = mapped_column(String, nullable=True)  # bounty|skill|pulse|recon|setup|otro
    daily_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="active")  # active|completed|abandoned
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON libre del operador
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    current_task: Mapped[list[WorkSessionTask]] = relationship(back_populates="session", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        # current_task se carga de forma perezosa; si la sesión de BD ya se
        # cerró, devolvemos [] en lugar de lanzar DetachedInstanceError.
        try:
            tasks = [t.to_dict() for t in self.current_task]
        except Exception:
            tasks = []
        return {
            "id": self.id,
            "session_id": self.session_id,
            "focus": self.focus,
            "daily_goal": self.daily_goal,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "total_minutes": self.total_minutes,
            "status": self.status,
            "notes": self.notes,
            "current_task": tasks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkSessionTask(Base):
    """Tarea en curso dentro de una sesión — el punto exacto de recuperación."""

    __tablename__ = "work_session_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("work_sessions.session_id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="in_progress")  # pending|in_progress|waiting|completed
    priority: Mapped[str | None] = mapped_column(String, nullable=True, default="medium")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # progreso parcial del operador
    linked_type: Mapped[str | None] = mapped_column(String, nullable=True)  # target|evidence|report|...
    linked_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    momentum: Mapped[int] = mapped_column(Integer, default=5)  # 1-10 energía/foco
    targets_referenced: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array de ids
    evidence_partial: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON lista evidencia parcial
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped[WorkSession] = relationship(back_populates="current_task")

    def to_dict(self) -> dict[str, Any]:
        import json as _json

        return {
            "id": self.id,
            "session_id": self.session_id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "notes": self.notes,
            "linked_type": self.linked_type,
            "linked_id": self.linked_id,
            "momentum": self.momentum,
            "targets_referenced": _json.loads(self.targets_referenced) if self.targets_referenced else [],
            "evidence_partial": _json.loads(self.evidence_partial) if self.evidence_partial else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
