"""Financial Sync Scheduler — periodic auto-sync for platforms and crypto wallets.

Provides a singleton background scheduler that runs sync_all() at configurable
intervals and exposes sync history for monitoring.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cores.identity_vault import get_identity_vault
from cores.platforms import PLATFORM_REGISTRY

logger = logging.getLogger("catseye.financial.scheduler")


@dataclass
class SyncReport:
    start_time: str
    end_time: str
    platforms: dict[str, dict[str, Any]] = field(default_factory=dict)
    crypto: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def total_platforms(self) -> int:
        return len(self.platforms)

    @property
    def successful_platforms(self) -> int:
        return sum(1 for p in self.platforms.values() if p.get("success"))

    @property
    def total_crypto(self) -> int:
        return len(self.crypto)

    @property
    def successful_crypto(self) -> int:
        return sum(1 for c in self.crypto.values() if c.get("success"))


class FinancialSyncScheduler:
    def __init__(self, interval_minutes: int = 30) -> None:
        self.interval_minutes = interval_minutes
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_report: SyncReport | None = None
        self._history: list[SyncReport] = []

    # ── Public API ─────────────────────────────────────────────────────

    def sync_platforms(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        vault = get_identity_vault()

        for platform_id, platform_cls in PLATFORM_REGISTRY.items():
            try:
                acct = vault.get_account(platform_id)
                if not acct or not acct.get("has_credentials"):
                    logger.debug("[SCHEDULER] No credentials for %s, skipping", platform_id)
                    continue

                creds = vault.get_credentials(platform_id)
                api_key = creds.get("token") or creds.get("password", "")
                if not api_key:
                    logger.debug("[SCHEDULER] Empty api_key for %s, skipping", platform_id)
                    continue

                platform = platform_cls()
                sync_result = platform.sync_earnings(api_key)
                results[platform_id] = {
                    "success": sync_result.success,
                    "total_earned": sync_result.total_earned,
                    "total_pending": sync_result.total_pending,
                    "earnings_count": len(sync_result.earnings),
                    "payouts_count": len(sync_result.payouts),
                    "programs_count": len(sync_result.programs),
                    "error": sync_result.error,
                }

                if sync_result.success:
                    logger.info(
                        "[SCHEDULER] %s sync OK — earned=%.2f pending=%.2f",
                        platform_id, sync_result.total_earned, sync_result.total_pending,
                    )
                else:
                    logger.warning("[SCHEDULER] %s sync failed: %s", platform_id, sync_result.error)
            except Exception as exc:
                logger.error("[SCHEDULER] %s sync error: %s", platform_id, exc)
                results[platform_id] = {
                    "success": False,
                    "error": str(exc),
                }

        return results

    def sync_crypto(self) -> dict[str, dict[str, Any]]:
        from cores.crypto.sync_manager import get_crypto_sync_manager

        mgr = get_crypto_sync_manager()
        crypto_results = mgr.sync_all()
        results: dict[str, dict[str, Any]] = {}

        for wid, snap in crypto_results.items():
            results[wid] = {
                "success": snap.connection.value == "connected",
                "chain": snap.chain.value,
                "total_usd": snap.total_usd,
                "balance_count": len(snap.balances),
                "error": snap.error,
            }

        logger.info("[SCHEDULER] Crypto sync: %d/%d wallets OK", sum(1 for r in results.values() if r["success"]), len(results))
        return results

    def sync_all(self) -> SyncReport:
        start = datetime.now(timezone.utc)

        platform_results = self.sync_platforms()
        crypto_results = self.sync_crypto()

        end = datetime.now(timezone.utc)

        report = SyncReport(
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            platforms=platform_results,
            crypto=crypto_results,
        )

        self._last_report = report
        self._history.append(report)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        logger.info(
            "[SCHEDULER] Sync complete: %d/%d platforms OK, %d/%d crypto OK",
            report.successful_platforms, report.total_platforms,
            report.successful_crypto, report.total_crypto,
        )
        return report

    # ── Background loop ────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[SCHEDULER] Financial auto-sync started (interval=%dmin)", self.interval_minutes)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("[SCHEDULER] Financial auto-sync stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                self.sync_all()
            except Exception as exc:
                logger.error("[SCHEDULER] Sync cycle error: %s", exc)
            await asyncio.sleep(self.interval_minutes * 60)

    # ── Query helpers ──────────────────────────────────────────────────

    def get_last_sync(self) -> SyncReport | None:
        return self._last_report

    def get_sync_history(self, limit: int = 10) -> list[SyncReport]:
        return self._history[-limit:]

    @property
    def is_running(self) -> bool:
        return self._running


_SCHEDULER: FinancialSyncScheduler | None = None


def get_financial_sync_scheduler() -> FinancialSyncScheduler:
    global _SCHEDULER
    if _SCHEDULER is None:
        _SCHEDULER = FinancialSyncScheduler()
    return _SCHEDULER
