from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.crypto.base")


class ChainType(str, Enum):
    EVM = "evm"
    BITCOIN = "bitcoin"
    SOLANA = "solana"
    TRON = "tron"
    COSMOS = "cosmos"
    EXCHANGE = "exchange"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    UNCONFIGURED = "unconfigured"


class WalletType(str, Enum):
    HOT = "hot"
    EXCHANGE = "exchange"
    LEDGER = "ledger"
    MULTISIG = "multisig"
    CONTRACT = "contract"


@dataclass
class CryptoBalance:
    asset: str
    symbol: str
    balance: float
    usd_value: float = 0.0
    decimals: int = 18
    chain: str = ""
    contract_address: str = ""
    last_updated: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "symbol": self.symbol,
            "balance": self.balance,
            "usd_value": round(self.usd_value, 2),
            "decimals": self.decimals,
            "chain": self.chain,
            "contract_address": self.contract_address,
            "last_updated": self.last_updated,
            "confidence": self.confidence,
        }


@dataclass
class CryptoTransaction:
    tx_hash: str
    chain: str
    block_number: int = 0
    timestamp: str = ""
    from_address: str = ""
    to_address: str = ""
    asset: str = ""
    amount: float = 0.0
    usd_value: float = 0.0
    fee: float = 0.0
    fee_asset: str = "ETH"
    status: str = "confirmed"
    tx_type: str = "transfer"
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tx_hash": self.tx_hash,
            "chain": self.chain,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "from": self.from_address,
            "to": self.to_address,
            "asset": self.asset,
            "amount": self.amount,
            "usd_value": round(self.usd_value, 2),
            "fee": self.fee,
            "fee_asset": self.fee_asset,
            "status": self.status,
            "tx_type": self.tx_type,
        }


@dataclass
class CryptoWithdrawalInfo:
    tx_hash: str
    chain: str
    asset: str
    amount: float
    usd_value: float = 0.0
    destination_address: str = ""
    fee: float = 0.0
    status: str = "pending"
    confirmations: int = 0
    confirmations_required: int = 12
    timestamp: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def is_finalized(self) -> bool:
        return self.confirmations >= self.confirmations_required

    def to_dict(self) -> dict[str, Any]:
        return {
            "tx_hash": self.tx_hash,
            "chain": self.chain,
            "asset": self.asset,
            "amount": self.amount,
            "usd_value": round(self.usd_value, 2),
            "destination": self.destination_address,
            "fee": self.fee,
            "status": self.status,
            "confirmations": self.confirmations,
            "confirmations_required": self.confirmations_required,
            "timestamp": self.timestamp,
            "finalized": self.is_finalized(),
        }


@dataclass
class SyncSnapshot:
    wallet_id: str
    chain: ChainType
    address: str = ""
    balances: list[CryptoBalance] = field(default_factory=list)
    transactions: list[CryptoTransaction] = field(default_factory=list)
    withdrawals: list[CryptoWithdrawalInfo] = field(default_factory=list)
    total_usd: float = 0.0
    connection: ConnectionStatus = ConnectionStatus.UNCONFIGURED
    error: str = ""
    synced_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "wallet_id": self.wallet_id,
            "chain": self.chain.value,
            "address": self.address,
            "balances": [b.to_dict() for b in self.balances],
            "transactions": [t.to_dict() for t in self.transactions],
            "withdrawals": [w.to_dict() for w in self.withdrawals],
            "total_usd": round(self.total_usd, 2),
            "connection": self.connection.value,
            "error": self.error,
            "synced_at": self.synced_at,
        }


class CryptoConnector(ABC):
    @property
    @abstractmethod
    def chain(self) -> ChainType: ...

    @property
    @abstractmethod
    def wallet_id(self) -> str: ...

    @abstractmethod
    def connect(self) -> ConnectionStatus: ...

    @abstractmethod
    def get_balance(self) -> list[CryptoBalance]: ...

    @abstractmethod
    def get_transactions(self, limit: int = 50) -> list[CryptoTransaction]: ...

    @abstractmethod
    def get_withdrawals(self, limit: int = 20) -> list[CryptoWithdrawalInfo]: ...

    def sync(self) -> SyncSnapshot:
        now = datetime.now(UTC).isoformat()
        try:
            status = self.connect()
            if status != ConnectionStatus.CONNECTED:
                return SyncSnapshot(
                    wallet_id=self.wallet_id,
                    chain=self.chain,
                    connection=status,
                    error=f"Connection failed: {status.value}",
                    synced_at=now,
                )
            balances = self.get_balance()
            transactions = self.get_transactions()
            withdrawals = self.get_withdrawals()
            total_usd = sum(b.usd_value for b in balances)
            return SyncSnapshot(
                wallet_id=self.wallet_id,
                chain=self.chain,
                balances=balances,
                transactions=transactions,
                withdrawals=withdrawals,
                total_usd=total_usd,
                connection=ConnectionStatus.CONNECTED,
                synced_at=now,
            )
        except Exception as exc:
            logger.error("Crypto sync failed for %s: %s", self.wallet_id, exc)
            return SyncSnapshot(
                wallet_id=self.wallet_id,
                chain=self.chain,
                connection=ConnectionStatus.ERROR,
                error=str(exc),
                synced_at=datetime.now(UTC).isoformat(),
            )


_PRICE_CACHE: dict[str, tuple[float, float]] = {}


def get_usd_price(symbol: str, max_age_seconds: int = 300) -> float:
    now = datetime.now(UTC).timestamp()
    cached = _PRICE_CACHE.get(symbol)
    if cached and (now - cached[1]) < max_age_seconds:
        return cached[0]
    return 0.0


def cache_usd_price(symbol: str, price: float) -> None:
    _PRICE_CACHE[symbol] = (price, datetime.now(UTC).timestamp())
