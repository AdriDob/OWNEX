from __future__ import annotations

import logging
from typing import Any

from cores.crypto.base import (
    ChainType,
    ConnectionStatus,
    CryptoConnector,
    SyncSnapshot,
)
from cores.crypto.btc import BTCConnector
from cores.crypto.evm import EVMConnector
from cores.crypto.exchange import ExchangeConnector
from cores.crypto.solana import SolanaConnector
from cores.crypto.tron import TronConnector
from cores.crypto.wallet_connect import WalletConnectConnector
from cores.financial.events import publish_financial_event
from cores.financial.withdrawal import auto_finalize
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("catseye.crypto.sync_manager")


_SYNC_HISTORY: dict[str, list[SyncSnapshot]] = {}


class CryptoSyncManager:
    def __init__(self) -> None:
        self._connectors: dict[str, CryptoConnector] = {}

    def register_connector(self, connector: CryptoConnector) -> None:
        self._connectors[connector.wallet_id] = connector
        logger.info("Registered crypto connector: %s (%s)", connector.wallet_id, connector.chain.value)

    def discover_wallets(self) -> None:
        vault = get_identity_vault()
        accounts = vault.list_accounts()
        for acct in accounts:
            provider = acct.get("provider_name", "")
            if provider.startswith("evm_"):
                chain = provider.replace("evm_", "")
                wid = f"evm:{chain}"
                if wid not in self._connectors:
                    self._connectors[wid] = EVMConnector(wallet_id=wid, chain_name=chain)
            elif provider.startswith("btc_"):
                wid = f"btc:{provider}"
                if wid not in self._connectors:
                    self._connectors[wid] = BTCConnector(wallet_id=wid)
            elif provider.startswith("exchange_"):
                name = provider.replace("exchange_", "")
                wid = f"exchange:{name}"
                if wid not in self._connectors:
                    self._connectors[wid] = ExchangeConnector(wallet_id=wid, exchange_name=name)
            elif provider.startswith("solana"):
                suffix = provider[len("solana"):].lstrip("_") or "mainnet"
                wid = f"solana:{suffix}"
                if wid not in self._connectors:
                    self._connectors[wid] = SolanaConnector(wallet_id=wid)
            elif provider.startswith("tron"):
                wid = f"tron:{provider}"
                if wid not in self._connectors:
                    self._connectors[wid] = TronConnector(wallet_id=wid)
            elif provider.startswith("wc_"):
                wallet_id = provider[3:]
                wid = f"wc:{wallet_id}"
                if wid not in self._connectors:
                    self._connectors[wid] = WalletConnectConnector(wallet_id=wallet_id)

    @property
    def connectors(self) -> dict[str, CryptoConnector]:
        return dict(self._connectors)

    def sync_wallet(self, wallet_id: str) -> SyncSnapshot | None:
        connector = self._connectors.get(wallet_id)
        if not connector:
            logger.warning("No connector for wallet: %s", wallet_id)
            return None
        snapshot = connector.sync()
        _SYNC_HISTORY.setdefault(wallet_id, []).append(snapshot)
        if snapshot.connection == ConnectionStatus.CONNECTED:
            publish_financial_event(
                "financial:sync_completed",
                amount=snapshot.total_usd,
                currency="USD",
                platform=wallet_id,
                description=f"Crypto sync: {wallet_id} — ${snapshot.total_usd:.2f}",
                metadata={"wallet_id": wallet_id, "balance_count": len(snapshot.balances)},
            )
            finalized = auto_finalize(wallet_id)
            if finalized:
                logger.info(
                    "Auto‑finalized %d withdrawal(s) for %s: %s",
                    len(finalized), wallet_id, finalized,
                )
            logger.info("Crypto sync OK: %s — %.2f USD (%d balances)", wallet_id, snapshot.total_usd, len(snapshot.balances))
        else:
            publish_financial_event(
                "financial:sync_failed",
                platform=wallet_id,
                description=f"Crypto sync failed: {wallet_id} — {snapshot.error}",
                metadata={"wallet_id": wallet_id, "error": snapshot.error},
            )
            logger.warning("Crypto sync FAILED: %s — %s", wallet_id, snapshot.error)
        return snapshot

    def sync_all(self) -> dict[str, SyncSnapshot]:
        results: dict[str, SyncSnapshot] = {}
        for wid in list(self._connectors.keys()):
            snap = self.sync_wallet(wid)
            if snap:
                results[wid] = snap
        return results

    def get_snapshot(self, wallet_id: str) -> SyncSnapshot | None:
        history = _SYNC_HISTORY.get(wallet_id, [])
        return history[-1] if history else None

    def get_history(self, wallet_id: str, limit: int = 10) -> list[SyncSnapshot]:
        return _SYNC_HISTORY.get(wallet_id, [])[-limit:]

    def get_all_snapshots(self) -> dict[str, SyncSnapshot]:
        results: dict[str, SyncSnapshot] = {}
        for wid in self._connectors:
            snap = self.get_snapshot(wid)
            if snap:
                results[wid] = snap
        return results

    def get_summary(self) -> dict[str, Any]:
        snapshots = self.get_all_snapshots()
        total_usd = sum(s.total_usd for s in snapshots.values())
        connected = sum(1 for s in snapshots.values() if s.connection == ConnectionStatus.CONNECTED)
        return {
            "total_wallets": len(self._connectors),
            "connected_wallets": connected,
            "total_usd": round(total_usd, 2),
            "by_chain": {
                chain.value: {
                    "count": sum(1 for s in snapshots.values() if s.chain == chain),
                    "usd_value": round(sum(s.total_usd for s in snapshots.values() if s.chain == chain), 2),
                }
                for chain in ChainType
            },
            "last_sync": max(
                (s.synced_at for s in snapshots.values()),
                default="",
            ),
        }


_MANAGER: CryptoSyncManager | None = None


def get_crypto_sync_manager() -> CryptoSyncManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = CryptoSyncManager()
        _MANAGER.discover_wallets()
    return _MANAGER
