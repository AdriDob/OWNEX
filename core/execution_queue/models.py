"""Execution Queue v1 — state machine única para ejecuciones OWNEX.

Unifica executors existentes (browser/coder/assisted) bajo un ciclo:
DISCOVERED→QUALIFIED→READY→QUEUED→EXECUTING→WAITING_HUMAN→SUBMITTED→VERIFICATION→PAID
con rechazos (REJECTED/BLOCKED/FAILED) y dead-letter. Sin I/O: lógica pura,
test-first; la persistencia y los adapters llegan en el siguiente corte.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any


class ExecState(StrEnum):
    DISCOVERED = "discovered"
    QUALIFIED = "qualified"
    READY = "ready"
    QUEUED = "queued"
    EXECUTING = "executing"
    WAITING_HUMAN = "waiting_human"
    SUBMITTED = "submitted"
    VERIFICATION = "verification"
    PAID = "paid"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


_TERMINAL = {ExecState.PAID, ExecState.REJECTED, ExecState.BLOCKED}
TRANSITIONS: dict[ExecState, set[ExecState]] = {
    ExecState.DISCOVERED: {ExecState.QUALIFIED, ExecState.REJECTED},
    ExecState.QUALIFIED: {ExecState.READY, ExecState.REJECTED},
    ExecState.READY: {ExecState.QUEUED},
    ExecState.QUEUED: {ExecState.EXECUTING},
    ExecState.EXECUTING: {ExecState.WAITING_HUMAN, ExecState.SUBMITTED, ExecState.FAILED},
    ExecState.WAITING_HUMAN: {ExecState.EXECUTING, ExecState.SUBMITTED, ExecState.REJECTED, ExecState.BLOCKED},
    ExecState.SUBMITTED: {ExecState.VERIFICATION, ExecState.REJECTED},
    ExecState.VERIFICATION: {ExecState.PAID, ExecState.FAILED},
    ExecState.FAILED: {ExecState.QUEUED, ExecState.DEAD_LETTER},  # retry con límite externo
}


def can_transition(current: ExecState | str, target: ExecState | str) -> bool:
    c, t = ExecState(current), ExecState(target)
    return t in TRANSITIONS.get(c, set())


def assert_transition(current: ExecState | str, target: ExecState | str) -> None:
    if not can_transition(current, target):
        raise ValueError(f"transición inválida: {current} → {target}")


def is_terminal(state: ExecState | str) -> bool:
    return ExecState(state) in _TERMINAL


# ── Persistencia mínima (JSON atómico, patrón WorkBank) ──


def _default_store_path() -> Path:
    """Data-dir aware default (patrón workbank.py): frozen bundles resuelven
    OWNEX_DATA_DIR desde start_backend.py (%LOCALAPPDATA%/OWNEX); dev mantiene
    ./data en la RAÍZ del repo. Fix 2026-08-25: al migrar el módulo plano a
    paquete (core/execution_queue/models.py), parents[1] pasó a resolver a
    core/ y escribía dentro del árbol de código; parents[2] = raíz."""
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "execution_queue.json"


class ExecutionQueueStore:
    """Cola persistente por item_id con transiciones validadas."""

    def __init__(
        self,
        store_path: str | Path | None = None,
        on_transition: Callable[[str, str, str, dict], Any] | None = None,
    ) -> None:
        self._path = Path(store_path or _default_store_path())
        self._items: dict[str, dict] = {}
        self._on_transition = on_transition
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists():
                self._items = json.loads(self._path.read_text())
        except Exception:
            self._items = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._items, indent=2))

    def _emit_transition(self, item_id: str, old_state: str, new_state: str, payload: dict) -> None:
        """Emit transition event if callback is registered."""
        if self._on_transition:
            try:
                self._on_transition(item_id, old_state, new_state, payload)
            except Exception:
                pass  # Never let event emission break the transition

    def add(self, item_id: str, payload: dict | None = None) -> dict:
        self._items[item_id] = {
            "state": ExecState.DISCOVERED.value,
            "payload": payload or {},
            "history": [ExecState.DISCOVERED.value],
        }
        self._save()
        self._emit_transition(item_id, "none", ExecState.DISCOVERED.value, payload or {})
        return self._items[item_id]

    def get(self, item_id: str) -> dict | None:
        return self._items.get(item_id)

    def transition(self, item_id: str, target: ExecState | str) -> dict:
        item = self._items[item_id]
        cur = ExecState(item["state"])
        tgt = ExecState(target)
        assert_transition(cur, tgt)
        old_state = cur.value
        item["state"] = tgt.value
        item["history"].append(tgt.value)
        self._save()
        self._emit_transition(item_id, old_state, tgt.value, item.get("payload", {}))
        return item

    def pending_by_state(self, *states: str) -> list[str]:
        return [k for k, v in self._items.items() if v["state"] in states]
