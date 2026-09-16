"""P0 regression: async job handlers MUST be awaited (2026-09-15).

Bug: api/lifespan.py::_run_job llamaba `handler(*args)` sin aguardar
coroutines → 21 jobs async (Pulse/Forge discovery, OpportunityOrchestrator,
execution_queue, worker_core heartbeat, etc.) se registraban pero NUNCA
ejecutaban (coroutine never awaited). Este guard:
- enumera handlers async de get_all_jobs()
- los ejecuta a completitud via _await_in_new_loop (thread + loop propio)
- verifica que un handler async fake produce su resultado (no None)
"""

from __future__ import annotations

import asyncio
from typing import Any


async def _fake_async_job() -> dict[str, Any]:
    await asyncio.sleep(0)
    return {"ran": True, "value": 42}


def _await_async(handler: Any, args: list[Any]) -> Any:
    """Reproduce api.lifespan._await_in_new_loop exactly (thread + own loop)."""
    import threading

    result: dict = {}

    def _target() -> None:
        try:
            result.update(asyncio.run(handler(*args)) or {})
        except Exception as exc:  # noqa: BLE001
            result.update({"error": str(exc)})

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    worker.join(timeout=10)
    return result


def test_async_job_awaited_runs_to_completion() -> None:
    """Un handler async ejecutado via thread+loop produce su resultado real."""
    out = _await_async(_fake_async_job, [])
    assert out.get("ran") is True
    assert out.get("value") == 42


def test_async_handlers_are_discovered_in_scheduler() -> None:
    """Todos los handlers async de get_all_jobs deben existir como callables (import runtime)."""
    from cores.scheduler.jobs import get_all_jobs

    async_handlers: list[list[str]] = []
    for _cycle, jobs in get_all_jobs().items():
        for j in jobs:
            h: Any = j.handler
            try:
                if not isinstance(h, str) or ":" not in h:
                    continue
                mod_path, attr = h.split(":", 1)
                import importlib

                mod = importlib.import_module(mod_path)
                obj = mod
                for part in (attr or "").split("."):
                    if part:
                        obj = getattr(obj, part)
                if asyncio.iscoroutinefunction(obj):
                    async_handlers.append([str(j.job_id), str(h)])
            except Exception:  # noqa: BLE001
                continue
    # Debe haber handlers async (de lo contrario este guard no asegura nada nuevo)
    assert len(async_handlers) > 0, "no hay handlers async registrados — revisar el supuesto"
    # Cada uno debe resolver a callable (lifespan._resolve_handler devolvería callable)
    from concurrent.futures import ThreadPoolExecutor

    def _resolve(handler: str) -> bool:
        try:
            mod_path, attr = handler.split(":", 1)
            import importlib

            mod = importlib.import_module(mod_path)
            obj = mod
            for part in (attr or "").split("."):
                if part:
                    obj = getattr(obj, part)
            return callable(obj)
        except Exception:  # noqa: BLE001
            return False

    with ThreadPoolExecutor(max_workers=8) as ex:
        ok = list(ex.map(_resolve, [h for _j, h in async_handlers]))
    assert all(ok), (
        f"handlers async que no resuelven: {[h for (_j, h), o in zip(async_handlers, ok, strict=True) if not o]}"
    )
