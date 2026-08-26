"""Execution Mirror — puente WorkBank/Pagos ↔ ExecutionQueue (Parte 2, FINAL RELEASE).

Cierra la integración declarada PARTIAL en FINAL_RELEASE_AUDIT §3: las acciones
reales del usuario en el Work Bank y las confirmaciones de pago del RevenueTracker
se reflejan en la máquina de estados canónica (13 estados) para que Desktop/Mobile/
Watch lean UNA sola cola.

Reglas:
- Idempotente: re-aplicar el mismo mirror NUNCA rompe (estados ya alcanzados → no-op).
- Best-effort: un fallo del espejo JAMÁS rompe el flujo del Work Bank ni el cobro.
- Honestidad: PAID solo vía VERIFICATION; sin confirmación de pago → sigue SUBMITTED.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ownex.execution.mirror")


def _get_store() -> Any:
    from core.execution_queue import ExecutionQueueStore

    return ExecutionQueueStore()


def _safe_transition(store: Any, item_id: str, target: str) -> bool:
    """Transición best-effort e idempotente. False = ya estaba ahí o inválida."""
    try:
        item = store.get(item_id)
        if item is None:
            return False
        if item["state"] == target:
            return True
        store.transition(item_id, target)
        return True
    except Exception:  # transición inválida o estado intermedio ausente
        return False


def mirror_workbank_prepared(item_id: str, payload: dict | None = None) -> None:
    """Work Bank dejó el ítem ready_to_deliver → QUALIFIED→READY."""
    try:
        store = _get_store()
        if store.get(item_id) is None:
            store.add(item_id, payload or {"source": "workbank"})
        _safe_transition(store, item_id, "qualified")
        _safe_transition(store, item_id, "ready")
    except Exception as e:
        logger.warning("mirror_workbank_prepared(%s) skipped: %s", item_id, e)


def mirror_workbank_packaged(item_id: str) -> None:
    """deliver/prepare generó el paquete → QUEUED (esperando acción humana)."""
    try:
        store = _get_store()
        if store.get(item_id) is not None:
            _safe_transition(store, item_id, "queued")
    except Exception as e:
        logger.warning("mirror_workbank_packaged(%s) skipped: %s", item_id, e)


def mirror_workbank_approved(item_id: str) -> None:
    """Human gate aprobó la entrega (submission salió) → EXECUTING→WAITING_HUMAN→SUBMITTED."""
    try:
        store = _get_store()
        if store.get(item_id) is None:
            # Ítem nunca mirrado (flujo viejo): sembrar y avanzar lo posible.
            store.add(item_id, {"source": "workback-legacy"})
        for state in ("qualified", "ready", "queued", "executing", "waiting_human", "submitted"):
            _safe_transition(store, item_id, state)
    except Exception as e:
        logger.warning("mirror_workbank_approved(%s) skipped: %s", item_id, e)


def mirror_payment_result(item_id: str, *, paid: bool, amount: float = 0.0, currency: str = "USD") -> None:
    """RevenueTracker confirmó el resultado del pago → VERIFICATION→PAID | REJECTED.

    Sin confirmación NO se avanza (honestidad económica): SUBMITTED es estable.
    """
    try:
        store = _get_store()
        if store.get(item_id) is None:
            logger.info("mirror_payment_result(%s): ítem ausente — nada que espejar", item_id)
            return
        _safe_transition(store, item_id, "verification")
        if paid:
            if _safe_transition(store, item_id, "paid"):
                try:
                    from core.execution_queue.driver import _emit_payout_event

                    _emit_payout_event(
                        item_id,
                        {"amount": amount, "currency": currency, "external_id": item_id},
                    )
                except Exception as e:
                    logger.warning("payout event no emitido para %s: %s", item_id, e)
        else:
            # La máquina canónica solo permite VERIFICATION→{PAID, FAILED};
            # FAILED proyecta a Stage.REJECTED ($0) vía stage_from_exec_state.
            _safe_transition(store, item_id, "failed")
    except Exception as e:
        logger.warning("mirror_payment_result(%s) skipped: %s", item_id, e)
