"""Tests del Session Manager (autoguardado de sesiones de trabajo).

Valida que el operador pueda iniciar una sesión, guardar una tarea en curso,
guardar progreso, completar la sesión y restaurar la última sesión al
reiniciar — sin perder progreso.
"""

from __future__ import annotations

from cores.session_manager import session_manager


def _fresh_manager() -> None:
    """Reinicia el singleton y limpia la BD para tests limpios."""
    session_manager.reset()


def test_start_and_get_session() -> None:
    _fresh_manager()
    started = session_manager.start_session(focus="bounty", daily_goal="Subir 2 reports", notes="nota inicial")
    assert started["status"] == "active"
    assert started["focus"] == "bounty"
    assert started["daily_goal"] == "Subir 2 reports"

    current = session_manager.get_current_session()
    assert current is not None
    assert current["session_id"] == started["session_id"]
    assert current["focus"] == "bounty"


def test_set_and_save_task() -> None:
    _fresh_manager()
    session_manager.start_session(focus="pulse")

    task = session_manager.set_current_task(
        title="Validar hallazgo X",
        status="in_progress",
        notes="Revisando screenshots",
        priority="high",
        linked_type="target",
        linked_id=42,
        momentum=7,
        targets_referenced=[42, 13],
        evidence_partial=[{"url": "http://x", "note": "hallazgo clave"}],
    )
    assert task["title"] == "Validar hallazgo X"
    assert task["status"] == "in_progress"
    assert task["momentum"] == 7
    assert task["linked_id"] == 42
    assert task["targets_referenced"] == [42, 13]
    assert len(task["evidence_partial"]) == 1

    # save_progress actualiza la misma tarea
    result = session_manager.save_progress(
        notes="Avanzando",
        momentum=9,
        evidence_item={"url": "http://y", "note": "otro hallazgo"},
    )
    assert result["success"] is True
    assert result["task"]["notes"] == "Avanzando"
    assert result["task"]["momentum"] == 9
    assert len(result["task"]["evidence_partial"]) == 2


def test_complete_and_restore() -> None:
    _fresh_manager()
    session_manager.start_session(focus="skill")
    completed = session_manager.complete_session()
    assert completed["status"] == "completed"

    # Al restaurar, como no hay activa, crea una nueva
    restored = session_manager.restore_or_start(focus="skill")
    assert restored["status"] == "active"
    assert restored["focus"] == "skill"


def test_get_status() -> None:
    _fresh_manager()
    status = session_manager.get_status()
    assert status["success"] is True
    assert status["has_active_session"] is False

    session_manager.start_session(focus="bounty")
    session_manager.set_current_task("Tarea prueba", status="in_progress")
    status = session_manager.get_status()
    assert status["has_active_session"] is True
    assert status["current_task"]["title"] == "Tarea prueba"


def test_list_recent() -> None:
    _fresh_manager()
    session_manager.start_session(focus="bounty")
    session_manager.complete_session()
    session_manager.start_session(focus="recon")

    recents = session_manager.list_recent(limit=5)
    assert len(recents) == 2
    assert recents[0]["focus"] == "recon"  # la más reciente primero
