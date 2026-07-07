from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any

from cores.crypto.base import (
    ChainType,
    ConnectionStatus,
    CryptoBalance,
    CryptoConnector,
    CryptoTransaction,
    CryptoWithdrawalInfo,
    get_usd_price,
)
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("cateye.crypto.exchange")


SUPPORTED_EXCHANGES: dict[str, dict[str, str]] = {
    "binance": {"name": "Binance", "base_url": "https://api.binance.com"},
    "coinbase": {"name": "Coinbase", "base_url": "https://api.coinbase.com"},
    "kraken": {"name": "Kraken", "base_url": "https://api.kraken.com"},
    "bybit": {"name": "Bybit", "base_url": "https://api.bybit.com"},
}


class ExchangeConnector(CryptoConnector):
    def __init__(self, wallet_id: str, exchange_name: str = "") -> None:
        self._wallet_id = wallet_id
        self._exchange_name = exchange_name.lower()
        self._status = ConnectionStatus.UNCONFIGURED
        self._api_key: str = ""
        self._api_secret: str = ""

        vault = get_identity_vault()
        creds = vault.get_credentials(f"exchange_{exchange_name}")
        self._api_key = creds.get("api_key", "")
        self._api_secret = creds.get("api_secret", "")
        self._passphrase = creds.get("passphrase", "")

    @property
    def chain(self) -> ChainType:
        return ChainType.EXCHANGE

    @property
    def wallet_id(self) -> str:
        return self._wallet_id

    @property
    def exchange_name(self) -> str:
        return self._exchange_name

    @property
    def base_url(self) -> str:
        info = SUPPORTED_EXCHANGES.get(self._exchange_name, {})
        return info.get("base_url", "")

    def connect(self) -> ConnectionStatus:
        if not self._api_key or not self._api_secret:
            self._status = ConnectionStatus.UNCONFIGURED
            return self._status

        try:
            result = self._signed_get("/api/v3/account" if self._exchange_name == "binance" else "/v2/accounts")
            if result is not None:
                self._status = ConnectionStatus.CONNECTED
            else:
                self._status = ConnectionStatus.ERROR
        except Exception as exc:
            logger.warning("Exchange connection failed for %s: %s", self._exchange_name, exc)
            self._status = ConnectionStatus.ERROR
        return self._status

    def get_balance(self) -> list[CryptoBalance]:
        if self._status != ConnectionStatus.CONNECTED:
            return []

        account_data = self._signed_get("/api/v3/account" if self._exchange_name == "binance" else "/v2/accounts")
        if not account_data:
            return []

        balances: list[CryptoBalance] = []
        raw_balances = (account_data.get("balances", [])
                        if self._exchange_name == "binance"
                        else account_data.get("wallet_balances", account_data.get("accounts", [])))

        for item in raw_balances:
            if isinstance(item, dict):
                asset = item.get("asset") or item.get("currency") or item.get("balance", {}).get("currency", "")
                free = float(item.get("free", 0) or item.get("available", 0) or item.get("balance", {}).get("amount", 0))
                locked = float(item.get("locked", 0) or item.get("hold", 0) or 0)
                total = free + locked
                if total <= 0:
                    continue
                usd_price = get_usd_price(asset)
                balances.append(CryptoBalance(
                    asset=asset,
                    symbol=asset,
                    balance=total,
                    usd_value=total * usd_price,
                    chain=f"exchange:{self._exchange_name}",
                    last_updated=datetime.now(timezone.utc).isoformat(),
                ))
        return balances

    def get_transactions(self, limit: int = 50) -> list[CryptoTransaction]:
        txs: list[CryptoTransaction] = []
        if self._status != ConnectionStatus.CONNECTED:
            return txs

        trade_history = self._signed_get(
            "/api/v3/myTrades" if self._exchange_name == "binance" else "/v2/trades",
            {"limit": min(limit, 50)},
        )
        if trade_history and isinstance(trade_history, list):
            for t in trade_history[:limit]:
                txs.append(CryptoTransaction(
                    tx_hash=t.get("id", str(t.get("trade_id", ""))),
                    chain=f"exchange:{self._exchange_name}",
                    timestamp=datetime.fromtimestamp(
                        t.get("time", t.get("created_at", 0)) / 1000
                        if isinstance(t.get("time"), (int, float)) and t.get("time", 0) > 1e10
                        else t.get("time", t.get("created_at", 0)),
                        tz=timezone.utc,
                    ).isoformat(),
                    asset=t.get("symbol", t.get("product_id", "")),
                    amount=float(t.get("qty", t.get("size", 0))),
                    usd_value=float(t.get("quoteQty", t.get("total", 0))),
                    fee=float(t.get("commission", t.get("fee", 0))),
                    status="confirmed",
                    tx_type=t.get("isBuyer", t.get("side", "buy")) == "buy" and "buy" or "sell",
                ))

        deposit_history = self._signed_get(
            "/sapi/v1/capital/deposit/hisrec" if self._exchange_name == "binance" else "/v2/deposits",
            {"limit": min(limit, 20)},
        )
        if deposit_history and isinstance(deposit_history, list):
            for d in deposit_history[:limit]:
                txs.append(CryptoTransaction(
                    tx_hash=d.get("txId", d.get("txn_hash", "")),
                    chain=f"exchange:{self._exchange_name}",
                    timestamp=datetime.fromtimestamp(
                        d.get("insertTime", d.get("created_at", 0)) / 1000
                        if isinstance(d.get("insertTime"), (int, float)) and d.get("insertTime", 0) > 1e10
                        else d.get("insertTime", d.get("created_at", 0)),
                        tz=timezone.utc,
                    ).isoformat(),
                    asset=d.get("coin", d.get("currency", "")),
                    amount=float(d.get("amount", 0)),
                    status=d.get("status", "confirmed"),
                    tx_type="deposit",
                ))

        return sorted(txs, key=lambda t: t.timestamp, reverse=True)[:limit]

    def get_withdrawals(self, limit: int = 20) -> list[CryptoWithdrawalInfo]:
        withdrawals: list[CryptoWithdrawalInfo] = []
        if self._status != ConnectionStatus.CONNECTED:
            return withdrawals

        wd_data = self._signed_get(
            "/sapi/v1/capital/withdraw/history" if self._exchange_name == "binance" else "/v2/withdrawals",
            {"limit": min(limit, 20)},
        )
        if wd_data and isinstance(wd_data, list):
            for w in wd_data[:limit]:
                status_str = w.get("status", "")
                status = "confirmed" if status_str in (1, "1", "Completed") else \
                         "pending" if status_str in (0, "0", "Pending", "processing") else \
                         "failed"
                withdrawals.append(CryptoWithdrawalInfo(
                    tx_hash=w.get("txId", w.get("txn_hash", "")),
                    chain=f"exchange:{self._exchange_name}",
                    asset=w.get("coin", w.get("currency", "")),
                    amount=float(w.get("amount", 0)),
                    destination_address=w.get("address", w.get("destination", "")),
                    fee=float(w.get("transactionFee", w.get("fee", 0))),
                    status=status,
                    confirmations=int(w.get("confirmTimes", w.get("confirmations", 0))),
                    timestamp=datetime.fromtimestamp(
                        w.get("applyTime", w.get("created_at", 0)) / 1000
                        if isinstance(w.get("applyTime"), (int, float)) and w.get("applyTime", 0) > 1e10
                        else w.get("applyTime", w.get("created_at", 0)),
                        tz=timezone.utc,
                    ).isoformat(),
                ))

        return sorted(withdrawals, key=lambda w: w.timestamp, reverse=True)[:limit]

    def _signed_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.base_url:
            return None
        if self._exchange_name == "binance":
            return self._binance_request(path, params or {})
        return self._generic_exchange_request(path, params)

    def _binance_request(self, path: str, params: dict[str, Any]) -> Any:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        signature = hmac.new(
            self._api_secret.encode("ascii"),
            query.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        url = f"{self.base_url}{path}?{query}&signature={signature}"
        req = urllib.request.Request(url, headers={"X-MBX-APIKEY": self._api_key})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            logger.warning("Binance API error %s: %s", path, exc)
            return None

    def _generic_exchange_request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{qs}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            logger.warning("Exchange API error %s %s: %s", self._exchange_name, path, exc)
            return None
