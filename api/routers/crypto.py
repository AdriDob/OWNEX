from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.crypto.base import ConnectionStatus
from cores.crypto.btc import BTCConnector
from cores.crypto.evm import EVMConnector
from cores.crypto.exchange import ExchangeConnector
from cores.crypto.solana import SolanaConnector
from cores.crypto.sync_manager import get_crypto_sync_manager
from cores.crypto.tron import TronConnector
from cores.crypto.wallet_connect import WalletConnectConnector
from cores.financial.events import publish_financial_event
from cores.ledger import LedgerEvent, record_event

logger = logging.getLogger("ownex.api.crypto")

router = APIRouter(prefix="/api/crypto", tags=["crypto"])


class WalletConfig(BaseModel):
    wallet_id: str
    chain: str
    address: str = ""
    rpc_url: str = ""
    exchange_name: str = ""


class RecordCryptoEvent(BaseModel):
    event_type: str
    amount: float
    asset: str = "USD"
    platform: str = "crypto"
    description: str = ""
    tx_hash: str = ""


class WalletConnectPairRequest(BaseModel):
    wallet_id: str
    chain: str = "ethereum"


class WalletConnectConnectRequest(BaseModel):
    wallet_id: str
    uri: str
    address: str = ""
    chain: str = "ethereum"


@router.get("/wallets")
def list_wallets() -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    snapshots = mgr.get_all_snapshots()
    return {
        "wallets": [
            {
                "id": wid,
                "chain": s.chain.value,
                "total_usd": s.total_usd,
                "connection": s.connection.value,
                "balance_count": len(s.balances),
                "last_sync": s.synced_at,
                "error": s.error,
            }
            for wid, s in snapshots.items()
        ],
        "total_wallets": len(mgr.connectors),
        "summary": mgr.get_summary(),
    }


@router.get("/wallets/{wallet_id}")
def get_wallet(wallet_id: str) -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    snap = mgr.get_snapshot(wallet_id)
    if not snap:
        connector = mgr.connectors.get(wallet_id)
        if not connector:
            raise HTTPException(404, f"Wallet {wallet_id} not found")
        snap = connector.sync()
    return snap.to_dict()


@router.post("/wallets/{wallet_id}/sync")
def sync_wallet(wallet_id: str) -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    snap = mgr.sync_wallet(wallet_id)
    if not snap:
        raise HTTPException(404, f"Wallet {wallet_id} not found")
    return snap.to_dict()


@router.post("/wallets/{wallet_id}/register")
def register_wallet(wallet_id: str, config: WalletConfig) -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    if wallet_id in mgr.connectors:
        raise HTTPException(409, f"Wallet {wallet_id} already registered")
    chain_lower = config.chain.lower()
    if chain_lower in ("ethereum", "polygon", "bsc", "arbitrum", "optimism"):
        connector = EVMConnector(
            wallet_id=wallet_id,
            chain_name=chain_lower,
            address=config.address,
            rpc_url=config.rpc_url,
        )
    elif chain_lower == "bitcoin":
        connector = BTCConnector(
            wallet_id=wallet_id,
            address=config.address,
        )
    elif chain_lower == "exchange":
        connector = ExchangeConnector(
            wallet_id=wallet_id,
            exchange_name=config.exchange_name,
        )
    elif chain_lower == "tron":
        connector = TronConnector(
            wallet_id=wallet_id,
            address=config.address,
        )
    elif chain_lower == "solana":
        connector = SolanaConnector(
            wallet_id=wallet_id,
            address=config.address,
        )
    elif chain_lower == "walletconnect":
        connector = WalletConnectConnector(
            wallet_id=wallet_id,
            chain_name=config.chain,
        )
    else:
        raise HTTPException(400, f"Unsupported chain: {config.chain}")
    mgr.register_connector(connector)
    return {"registered": True, "wallet_id": wallet_id, "chain": chain_lower}


@router.post("/wallets/walletconnect/pair")
def walletconnect_pair(req: WalletConnectPairRequest) -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    wid = f"wc:{req.wallet_id}"
    connector: WalletConnectConnector | None = mgr.connectors.get(wid)
    if not connector:
        connector = WalletConnectConnector(
            wallet_id=req.wallet_id,
            chain_name=req.chain,
        )
        mgr.register_connector(connector)
    uri = connector.generate_pairing_uri()
    return {"uri": uri, "wallet_id": req.wallet_id}


@router.post("/wallets/walletconnect/connect")
def walletconnect_connect(req: WalletConnectConnectRequest) -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    wid = f"wc:{req.wallet_id}"
    connector: WalletConnectConnector | None = mgr.connectors.get(wid)
    if not connector:
        connector = WalletConnectConnector(
            wallet_id=req.wallet_id,
            chain_name=req.chain,
        )
        mgr.register_connector(connector)
    status = connector.pair(req.uri, address=req.address)
    return {
        "paired": status == ConnectionStatus.CONNECTED,
        "status": status.value,
        "wallet_id": req.wallet_id,
    }


@router.post("/wallets/{wallet_id}/disconnect")
def disconnect_wallet(wallet_id: str) -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    connector = mgr.connectors.get(wallet_id)
    if not connector:
        raise HTTPException(404, f"Wallet {wallet_id} not found")
    if isinstance(connector, WalletConnectConnector):
        connector.disconnect()
    else:
        connector._status = ConnectionStatus.DISCONNECTED
    return {"disconnected": True, "wallet_id": wallet_id}


@router.post("/sync-all")
def sync_all_wallets() -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    results = mgr.sync_all()
    return {
        "synced": len(results),
        "total_usd": round(sum(s.total_usd for s in results.values()), 2),
        "wallets": {
            wid: {
                "connection": s.connection.value,
                "total_usd": s.total_usd,
                "balances": len(s.balances),
                "error": s.error,
            }
            for wid, s in results.items()
        },
    }


@router.get("/summary")
def crypto_summary() -> dict[str, Any]:
    mgr = get_crypto_sync_manager()
    return mgr.get_summary()


@router.post("/record")
def record_crypto_event(req: RecordCryptoEvent) -> dict[str, Any]:
    event_map = {
        "deposit": LedgerEvent.CRYPTO_DEPOSIT,
        "withdrawal": LedgerEvent.CRYPTO_WITHDRAWAL,
        "stake": LedgerEvent.CRYPTO_STAKING_REWARD,
        "yield": LedgerEvent.CRYPTO_DEFI_YIELD,
        "swap": LedgerEvent.CRYPTO_SWAP,
        "gas": LedgerEvent.CRYPTO_GAS_FEE,
        "airdrop": LedgerEvent.CRYPTO_AIRDROP,
        "trade": LedgerEvent.EXCHANGE_TRADE,
        "fee": LedgerEvent.EXCHANGE_FEE,
    }
    event = event_map.get(req.event_type)
    if not event:
        raise HTTPException(400, f"Unknown event type: {req.event_type}")
    entry = record_event(
        event=event,
        amount=req.amount,
        currency=req.asset,
        description=req.description or f"Crypto {req.event_type}",
        source=f"crypto:{req.platform}",
        source_id=req.tx_hash,
        platform=req.platform,
        metadata={"tx_hash": req.tx_hash},
    )
    publish_financial_event(
        f"financial:crypto_{req.event_type}_detected" if req.event_type in ("deposit", "withdrawal") else "financial:sync_completed",
        amount=req.amount,
        currency=req.asset,
        platform=req.platform,
        description=req.description,
        metadata={"tx_hash": req.tx_hash, "event_type": req.event_type},
    )
    return {"entry_id": entry.entry_id, "event": req.event_type, "amount": req.amount}
