"""Financial Sync Scheduler — periodic auto-sync for platforms and crypto wallets.

Provides a singleton background scheduler that runs sync_all() at configurable
intervals and exposes sync history for monitoring.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from cores.identity_vault import get_identity_vault
from cores.platforms import PLATFORM_REGISTRY

logger = logging.getLogger("ownex.financial.scheduler")


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
    def __init__(self, interval_minutes: int = 30, github_token: str | None = None) -> None:
        self.interval_minutes = interval_minutes
        self._github_token = github_token
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
                        platform_id,
                        sync_result.total_earned,
                        sync_result.total_pending,
                    )
                    # Persist earnings into the canonical store so Capital
                    # dashboards grow from real platform data (deduped).
                    try:
                        persisted = self._persist_earnings(platform_id, sync_result)
                        if persisted:
                            logger.info(
                                "[SCHEDULER] %s → %d payout(s) nuevos persistidos (%d duplicados saltados)",
                                platform_id,
                                persisted[0],
                                persisted[1],
                            )
                    except Exception as persist_exc:
                        logger.warning("[SCHEDULER] %s earnings not persisted: %s", platform_id, persist_exc)
                    # Feed real earnings into the RevenueTracker so the Work Bank
                    # feedback loop (build_history_from_revenue_tracker → apply_learning)
                    # learns from verified payouts instead of sitting empty.
                    try:
                        from cores.revenue_tracker.revenue_tracker import (
                            get_revenue_tracker,
                        )

                        tracker = get_revenue_tracker()
                        if sync_result.total_earned > 0:
                            tracker.add_daily_revenue(
                                platform_id,
                                Decimal(str(sync_result.total_earned)),
                                "USD",
                            )
                    except Exception as feed_exc:  # pragma: no cover
                        logger.warning(
                            "[SCHEDULER] %s earnings not fed to RevenueTracker: %s",
                            platform_id,
                            feed_exc,
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

    def _persist_earnings(self, platform_id: str, sync_result: Any) -> tuple[int, int]:
        """Persist earnings from a sync result into PayoutRecord with dedupe.

        Returns (inserted_count, skipped_count).
        """
        from datetime import datetime

        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        db = SessionLocal()
        inserted = 0
        skipped = 0
        try:
            for earning in getattr(sync_result, "earnings", []):
                earning_id = str(earning.get("id", "")).strip()
                if not earning_id:
                    continue
                external_id = f"{platform_id}:{earning_id}"
                exists = (
                    db.query(PayoutRecord)
                    .filter(
                        PayoutRecord.platform == platform_id,
                        PayoutRecord.external_id == external_id,
                    )
                    .first()
                )
                if exists:
                    skipped += 1
                    continue

                amount = float(earning.get("amount", 0))
                currency = earning.get("currency", "USD")
                program = earning.get("program", "")
                paid_at = None
                created_at_str = earning.get("created_at", "")
                if created_at_str:
                    with contextlib.suppress(Exception):
                        paid_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

                payout = PayoutRecord(
                    platform=platform_id,
                    amount=amount,
                    currency=currency,
                    program=program,
                    external_id=external_id,
                    status="confirmed",
                    paid_at=paid_at,
                )
                db.add(payout)
                inserted += 1
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        return inserted, skipped

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
        start = datetime.now(UTC)

        platform_results = self.sync_platforms()
        crypto_results = self.sync_crypto()

        end = datetime.now(UTC)

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
            report.successful_platforms,
            report.total_platforms,
            report.successful_crypto,
            report.total_crypto,
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
        self._task = None
        logger.info("[SCHEDULER] Financial auto-sync stopped")

    # ── Pay-on-Merge Helpers ──────────────────────────────────────────
    def _get_pending_payouts(self) -> list[dict[str, Any]]:
        """Obtener todos los deliverables pendientes de payout.

        Filtra los PayoutRecord que tienen status 'pending' y
        expected_amount > 0, ordenados por fecha de creación (antiguo primero).
        """
        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        db = SessionLocal()
        try:
            query = db.query(PayoutRecord).filter(
                PayoutRecord.status == "pending",
                PayoutRecord.expected_amount > 0,
            )
            # Ordenar por creado ascending (los más antiguos primero)
            pending = query.order_by(PayoutRecord.created_at.asc()).all()
            # Convertir a dicts simples para el procesamiento
            result = []
            for pr in pending:
                result.append(
                    {
                        "id": pr.id,
                        "expected_amount": float(pr.expected_amount or 0),
                        "platform_id": pr.platform or "unknown",
                        "user_id": pr.user_id or "unknown",
                        "status": pr.status,
                        "created_at": pr.created_at.isoformat() if pr.created_at else None,
                        "delivery_confirmed_at": pr.delivery_confirmed_at.isoformat() if pr.delivery_confirmed_at else None,
                        "user_confirmed_delivery": pr.user_confirmed_delivery or False,
                        "status": pr.status,
                    }
                )
            return result
        except Exception as exc:
            logger.error("[SCHEDULER] Error fetching pending payouts: %s", exc)
            return []
        finally:
            db.close()

    def _trigger_instant_payout(self, deliverable: dict[str, Any]) -> bool:
        """Disparar payout instantáneo para un deliverable merged/accepted.

        Looks up the PayoutRecord by deliverable id and updates its status
        to 'processing' with an instant trigger note. In a full implementation,
        this would call the payment gateway (USDC, crypto, etc.).

        Returns True if the payout was triggered successfully, False otherwise.
        """
        from database.db import SessionLocal
        from database.models_economic import PayoutRecord

        db = SessionLocal()
        try:
            # Buscar el PayoutRecord por id (que es el mismo que deliverable["id"])
            pr = db.query(PayoutRecord).filter(PayoutRecord.id == deliverable["id"]).first()
            if pr is None:
                logger.warning("[SCHEDULER] No PayoutRecord found for deliverable id: %s", deliverable["id"])
                return False

            # Actualizar status a 'processing' y agregar metadata de trigger
            pr.status = "processing"
            pr.notes = pr.notes + (pr.notes and "\n" or "") + f"[INSTANT] merged_deliverable triggered at {datetime.utcnow().isoformat()}"
            db.add(pr)
            db.commit()
            db.refresh(pr)

            logger.info(
                "[SCHEDULER] Instant payout triggered for deliverable %s amount %.2f",
                deliverable["id"],
                deliverable["expected_amount"],
            )
            return True

        except Exception as exc:
            db.rollback()
            logger.error("[SCHEDULER] Error triggering instant payout: %s", exc)
            return False
        finally:
            db.close()

    # ── End Pay-on-Merge Helpers ───────────────────────────────────────

    async def _loop(self) -> None:
        while self._running:
            try:
                await asyncio.to_thread(self.sync_all)
            except Exception as exc:
                logger.error("[SCHEDULER] Sync cycle error: %s", exc)
            await asyncio.sleep(self.interval_minutes * 60)

    # ── Query helpers ──────────────────────────────────────────────────

    def get_last_sync(self) -> SyncReport | None:
        return self._last_report

    def get_sync_history(self, limit: int = 10) -> list[SyncReport]:
        return self._history[-limit:]

    # ── Pay-on-Merge Detection (Bountic-inspired) ──────────────────────
    def _check_merged_deliverables(self) -> list[dict[str, Any]]:
        """Detect deliverables that were merge/accepted and trigger instant payouts.

        Inspired by Bountic's pay-on-merge workflow: instead of waiting the
        regular 30min schedule, detect when a user confirms delivery and pay
        immediately.

        Returns list of paid deliverable dicts with:
        - deliverable_id
        - payout_amount
        - trigger: "merged_deliverable"
        - timestamp
        """
        paid: list[dict[str, Any]] = []

        # Obtener todos los deliverables pendientes de pago
        pending = self._get_pending_payouts()

        for deliverable in pending:
            # Verificar si fue aceptado/mergeado recientemente
            recently_merged = self._check_merge_status(deliverable)

            if recently_merged and not deliverable.get("payout_disputed"):
                # Disparar payout inmediato
                result = self._trigger_instant_payout(deliverable)
                if result:
                    paid.append(
                        {
                            "deliverable_id": deliverable["id"],
                            "payout_amount": deliverable["expected_amount"],
                            "trigger": "merged_deliverable",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

        return paid

    def _check_merge_status(self, deliverable: dict) -> bool:
        """Chequear si un deliverable fue mergeado/aceptado recientemente.

        Revisa múltiples señales:
        1. User confirmó entrega en dashboard (delivery_confirmed_at dentro de 48h)
        2. Webhook de PR mergeado (pending: revisar configuración)
        3. Usuario dio /approval en el sistema
        4. Status del deliverable cambió a 'delivered'/'accepted'
        """
        # Señal 1: El user marcó entrega como completada
        if deliverable.get("user_confirmed_delivery"):
            confirmed = deliverable.get("delivery_confirmed_at")
            if confirmed:
                from datetime import datetime, timezone, timedelta

                dt = datetime.fromisoformat(confirmed)
                now = datetime.now(timezone.utc)
                return (now - dt).days < 2

        # Señal 2: Status del deliverable es 'delivered' o 'accepted'
        if deliverable.get("status") in {"delivered", "accepted"}:
            return True

        # Señal 3: approval_given flag
        if deliverable.get("approval_given"):
            return True

        # Señal 4: pending - webhook de PR mergeado (implementación futura)
        # pending: revisar webhooks configurados

        # Señal 5: GitHub PR merge check via API
        # Verifica si el PR fue mergeado recientemente consultando la API
        if deliverable.get("github_pr_number") and deliverable.get("github_repo_owner") and deliverable.get("github_repo_name"):
            import httpx
            from datetime import datetime, timezone

            try:
                headers = {"Accept": "application/vnd.github+json"}
                if self._github_token:
                    headers["Authorization"] = f"token {self._github_token}"
                url = (
                    f"https://api.github.com/repos/{deliverable['github_repo_owner']}/{deliverable['github_repo_name']}/pulls/{deliverable['github_pr_number']}"
                )
                resp = httpx.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    pr_data = resp.json()
                    # Si el PR está cerrado (merged) y fue recientemente mergeado
                    if pr_data.get("merged_at"):
                        merged_at = datetime.fromisoformat(pr_data["merged_at"])
                        now = datetime.now(timezone.utc)
                        # Considerado mergeado reciente si fue en las últimas 48h
                        return (now - merged_at).days < 2
            except Exception as exc:
                logger.warning("[SCHEDULER] GitHub PR merge check failed: %s", exc)

        return False

    # ── End Pay-on-Merge Detection ─────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running


_SCHEDULER: FinancialSyncScheduler | None = None


def get_financial_sync_scheduler() -> FinancialSyncScheduler:
    global _SCHEDULER
    if _SCHEDULER is None:
        _SCHEDULER = FinancialSyncScheduler()
    return _SCHEDULER
