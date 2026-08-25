"""Convergencia SSOT de máquinas de estado + resolución de data-dir (audit P0-2/P0-5).

ExecState (core/execution_queue.py) = ciclo de ejecución canónico.
OpportunityStage = proyección económica derivada vía mapper ÚNICO en
cores/revenue_tracker/revenue_tracker.py. Estos tests garantizan que la tabla
nunca quede desincronizada cuando se agreguen estados nuevos.
"""

from __future__ import annotations

from core.execution_queue import ExecState
from cores.revenue_tracker.revenue_tracker import (
    OpportunityStage,
    exec_state_for_stage,
    stage_from_exec_state,
)


def test_stage_from_exec_state_is_exhaustive() -> None:
    """TODO ExecState debe tener mapeo explícito — agregar un estado sin
    mapear rompe este test (patrón test_work_taxonomy)."""
    mapped_keys = set(stage_from_exec_state.__globals__["_stage_from_exec_map"]())
    assert set(s.value for s in ExecState) <= mapped_keys


def test_roundtrip_projection_never_invents_money_stages() -> None:
    """La proyección nunca puede decir PAID salvo que el exec state sea PAID."""
    for state in ExecState:
        projected = stage_from_exec_state(state)
        if projected is OpportunityStage.PAID:
            assert state is ExecState.PAID
        if state in (ExecState.FAILED, ExecState.DEAD_LETTER, ExecState.BLOCKED):
            assert projected is OpportunityStage.REJECTED


def test_reverse_map_covers_all_stages() -> None:
    """exec_state_for_stage devuelve un ExecState válido para los 8 stages
    (mapa lossy por diseño: ACCEPTED y REWARDED comparten VERIFICATION)."""
    for stage in OpportunityStage:
        exec_val = exec_state_for_stage(stage)
        assert ExecState(exec_val) in ExecState


def test_accepted_maps_to_verification_not_paid() -> None:
    """ACCEPTED/REWARDED = bounty otorgado pero caja no aterrizada → VERIFICATION."""
    assert stage_from_exec_state("verification") is OpportunityStage.SUBMITTED
    assert exec_state_for_stage(OpportunityStage.ACCEPTED) == "verification"
    assert exec_state_for_stage(OpportunityStage.REWARDED) == "verification"


def test_store_default_honors_ownex_data_dir(monkeypatch, tmp_path) -> None:
    """El default del store resuelve OWNEX_DATA_DIR (frozen bundles), jamás
    un path repo-parents fuera del árbol (audit P0-5)."""
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path / "ownexdata"))
    from core.execution_queue import _default_store_path

    resolved = _default_store_path()
    assert str(tmp_path / "ownexdata") in str(resolved)
    assert resolved.name == "execution_queue.json"


def test_store_default_dev_falls_inside_repo() -> None:
    """Sin env var, dev cae dentro del repo ./data (no parents[2] roto)."""
    import os

    old = os.environ.pop("OWNEX_DATA_DIR", None)
    try:
        resolved = _default_store_path_importable()
        assert "Rastro/data" in str(resolved)
    finally:
        if old is not None:
            os.environ["OWNEX_DATA_DIR"] = old


def _default_store_path_importable():
    from core.execution_queue import _default_store_path

    return _default_store_path()
