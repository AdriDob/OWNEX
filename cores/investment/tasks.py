"""Investment scheduler tasks — real runners for registered jobs.

Each runner is read-only reporting unless explicitly stated: this module NEVER
places orders, moves funds, or touches live capital. Execution (if ever
authorized) lives behind Human Gate + IdentityVault, not in the scheduler.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.investment.tasks")


def _default_snapshot_path() -> Path:
    from cores.platform.system import get_data_dir

    return get_data_dir() / "arbitrage_last_scan.json"


async def run_arbitrage_scan_once(
    adapter: Any = None,
    snapshot_path: Path | str | None = None,
) -> dict[str, Any]:
    """One cross-exchange price-gap scan. Async core (tests inject fakes).

    Read-only: calls scan_opportunities() only. NEVER calls execute_trade(),
    get_balance(), or any method that moves funds. Never raises — offline or
    missing ccxt degrades to an empty/opportunistic result with a note.
    """
    from cores.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

    if adapter is None:
        adapter = GlobalArbitrageAdapter()
        try:
            await adapter.connect()
        except Exception as exc:
            logger.warning("arbitrage connect failed (offline?): %s", exc)

    try:
        opportunities = await adapter.scan_opportunities()
    except Exception as exc:
        logger.warning("arbitrage scan failed (offline?): %s", exc)
        opportunities = []

    summary: dict[str, Any] = {
        "status": "ok",
        "scanned_at": datetime.now(UTC).isoformat(),
        "opportunities": opportunities if isinstance(opportunities, list) else [],
        "count": len(opportunities) if isinstance(opportunities, list) else 0,
        "note": "read-only scan; no orders placed",
    }
    try:
        path = Path(snapshot_path) if snapshot_path is not None else _default_snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, default=str), encoding="utf-8")
        summary["snapshot_path"] = str(path)
    except Exception as exc:
        logger.warning("arbitrage snapshot not persisted: %s", exc)
    return summary


def run_investment_arbitrage_scan() -> dict[str, Any]:
    """Scheduler entrypoint: arbitrage scan, read-only, never raises.

    Runs the async scan on a dedicated thread so it is safe from any caller
    event-loop context. Returns a JSON-serializable summary.
    """
    import threading

    result: dict[str, Any] = {}

    def _target() -> None:
        import asyncio

        try:
            result.update(asyncio.run(run_arbitrage_scan_once()))
        except Exception as exc:  # never break the scheduler
            logger.error("arbitrage scan cycle failed: %s", exc)
            result.update({"status": "error", "error": str(exc), "opportunities": [], "count": 0})

    worker = threading.Thread(target=_target, name="investment-arbitrage", daemon=True)
    worker.start()
    worker.join(timeout=600)
    if worker.is_alive():
        return {"status": "timeout", "opportunities": [], "count": 0}
    result.setdefault("status", "ok")
    return result
