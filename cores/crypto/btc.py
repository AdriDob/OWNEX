from __future__ import annotations

import json
import logging
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

logger = logging.getLogger("catseye.crypto.btc")

BLOCKSTREAM_BASE = "https://blockstream.info/api"


def _api_get(url: str) -> str | None:
    import urllib.request
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode()
    except Exception as exc:
        logger.warning("BTC API call failed: %s", exc)
        return None


def _api_get_json(url: str) -> Any:
    data = _api_get(url)
    if data is None:
        return None
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("BTC API JSON parse failed: %s", exc)
        return None


def _get_tip_height() -> int:
    data = _api_get(f"{BLOCKSTREAM_BASE}/blocks/tip/height")
    if data and data.strip().isdigit():
        return int(data.strip())
    return 0


class BTCConnector(CryptoConnector):
    def __init__(self, wallet_id: str, address: str = "") -> None:
        self._wallet_id = wallet_id
        self._address = address
        self._status = ConnectionStatus.UNCONFIGURED

        if not self._address:
            vault = get_identity_vault()
            creds = vault.get_credentials("btc")
            self._address = creds.get("address", "")

    @property
    def chain(self) -> ChainType:
        return ChainType.BITCOIN

    @property
    def wallet_id(self) -> str:
        return self._wallet_id

    @property
    def address(self) -> str:
        return self._address

    def connect(self) -> ConnectionStatus:
        data = _api_get(f"{BLOCKSTREAM_BASE}/blocks/tip/height")
        if data is not None and data.strip().isdigit():
            self._status = ConnectionStatus.CONNECTED
        else:
            self._status = ConnectionStatus.ERROR
        return self._status

    def get_balance(self) -> list[CryptoBalance]:
        balances: list[CryptoBalance] = []
        if not self._address or self._status != ConnectionStatus.CONNECTED:
            return balances

        data = _api_get_json(f"{BLOCKSTREAM_BASE}/address/{self._address}")
        if not data or "chain_stats" not in data:
            return balances

        funded = data["chain_stats"].get("funded_txo_sum", 0)
        spent = data["chain_stats"].get("spent_txo_sum", 0)
        balance_sat = funded - spent
        balance_btc = balance_sat / 1e8

        usd_price = get_usd_price("BTC")
        balances.append(CryptoBalance(
            asset="BTC",
            symbol="BTC",
            balance=balance_btc,
            usd_value=balance_btc * usd_price,
            decimals=8,
            chain="bitcoin",
            last_updated=datetime.now(timezone.utc).isoformat(),
        ))
        return balances

    def get_transactions(self, limit: int = 50) -> list[CryptoTransaction]:
        txs: list[CryptoTransaction] = []
        if not self._address:
            return txs

        data = _api_get_json(f"{BLOCKSTREAM_BASE}/address/{self._address}/txs")
        if not data or not isinstance(data, list):
            return txs

        for tx_data in data[:limit]:
            try:
                parsed = self._parse_tx(tx_data)
                if parsed:
                    txs.append(parsed)
            except Exception as exc:
                logger.warning("Failed to parse BTC tx %s: %s", tx_data.get("txid", "")[:16], exc)

        return txs

    def _parse_tx(self, tx_data: dict[str, Any]) -> CryptoTransaction | None:
        txid = tx_data.get("txid", "")
        status = tx_data.get("status", {})
        block_time = status.get("block_time", 0)
        timestamp = datetime.fromtimestamp(block_time, tz=timezone.utc).isoformat() if block_time else ""

        our_vin_sum = 0
        our_vout_sum = 0
        our_address = self._address

        for vin in tx_data.get("vin", []):
            prevout = vin.get("prevout") or {}
            if prevout.get("scriptpubkey_address") == our_address:
                our_vin_sum += prevout.get("value", 0)

        for vout in tx_data.get("vout", []):
            if vout.get("scriptpubkey_address") == our_address:
                our_vout_sum += vout.get("value", 0)

        if our_vin_sum == 0 and our_vout_sum == 0:
            return None

        if our_vin_sum > 0:
            amount_sat = our_vin_sum - our_vout_sum
            tx_type = "send"
            from_addr = our_address
            to_addr = ""
            for vout in tx_data.get("vout", []):
                addr = vout.get("scriptpubkey_address", "")
                if addr and addr != our_address:
                    to_addr = addr
                    break
        else:
            amount_sat = our_vout_sum
            tx_type = "receive"
            from_addr = ""
            to_addr = our_address
            for vin in tx_data.get("vin", []):
                prevout = vin.get("prevout") or {}
                addr = prevout.get("scriptpubkey_address", "")
                if addr:
                    from_addr = addr
                    break

        amount_btc = amount_sat / 1e8
        usd_price = get_usd_price("BTC")

        return CryptoTransaction(
            tx_hash=txid,
            chain="bitcoin",
            block_number=status.get("block_height", 0),
            timestamp=timestamp,
            from_address=from_addr,
            to_address=to_addr,
            asset="BTC",
            amount=amount_btc,
            usd_value=amount_btc * usd_price,
            fee=0.0,
            fee_asset="BTC",
            status="confirmed" if status.get("confirmed", False) else "pending",
            tx_type=tx_type,
            raw_payload={"txid": txid},
        )

    def get_withdrawals(self, limit: int = 20) -> list[CryptoWithdrawalInfo]:
        withdrawals: list[CryptoWithdrawalInfo] = []
        if not self._address:
            return withdrawals

        data = _api_get_json(f"{BLOCKSTREAM_BASE}/address/{self._address}/txs")
        if not data or not isinstance(data, list):
            return withdrawals

        tip_height = _get_tip_height()

        for tx_data in data:
            try:
                our_vin_sum = 0
                our_vout_sum = 0
                our_address = self._address

                for vin in tx_data.get("vin", []):
                    prevout = vin.get("prevout") or {}
                    if prevout.get("scriptpubkey_address") == our_address:
                        our_vin_sum += prevout.get("value", 0)

                for vout in tx_data.get("vout", []):
                    if vout.get("scriptpubkey_address") == our_address:
                        our_vout_sum += vout.get("value", 0)

                if our_vin_sum == 0:
                    continue

                amount_sat = our_vin_sum - our_vout_sum
                amount_btc = amount_sat / 1e8
                txid = tx_data.get("txid", "")
                status = tx_data.get("status", {})
                block_time = status.get("block_time", 0)
                timestamp = datetime.fromtimestamp(block_time, tz=timezone.utc).isoformat() if block_time else ""
                block_height = status.get("block_height", 0)
                confirmations = tip_height - block_height + 1 if block_height > 0 else 0

                dest = ""
                for vout in tx_data.get("vout", []):
                    addr = vout.get("scriptpubkey_address", "")
                    if addr and addr != our_address:
                        dest = addr
                        break

                usd_price = get_usd_price("BTC")
                wd = CryptoWithdrawalInfo(
                    tx_hash=txid,
                    chain="bitcoin",
                    asset="BTC",
                    amount=amount_btc,
                    usd_value=amount_btc * usd_price,
                    destination_address=dest,
                    fee=0.0,
                    status="confirmed" if status.get("confirmed", False) else "pending",
                    confirmations=max(0, confirmations),
                    confirmations_required=6,
                    timestamp=timestamp,
                    raw_payload={"txid": txid},
                )
                withdrawals.append(wd)
            except Exception as exc:
                logger.warning("Failed to parse BTC withdrawal tx %s: %s", tx_data.get("txid", "")[:16], exc)

        return sorted(withdrawals, key=lambda w: w.timestamp, reverse=True)[:limit]
