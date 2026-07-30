from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
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

logger = logging.getLogger("ownex.crypto.tron")

TRONGRID_API = "https://api.trongrid.io"

SUN_DECIMALS = 6

TRC20_TOKENS: dict[str, str] = {
    "USDT": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "USDC": "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8",
    "USDD": "TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn",
    "TUSD": "TUpMhErZL2fhh4sVNULAbNKLokS4GjC1F4",
    "WTRX": "TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR",
}


def _tron_api_call(path: str, params: dict[str, str] | None = None) -> dict[str, Any] | None:
    import urllib.request

    url = f"{TRONGRID_API}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.warning("TronGrid API call failed: %s", exc)
        return None


class TronConnector(CryptoConnector):
    def __init__(self, wallet_id: str, address: str = "") -> None:
        self._wallet_id = wallet_id
        self._address = address
        self._status = ConnectionStatus.UNCONFIGURED

        if not self._address:
            vault = get_identity_vault()
            creds = vault.get_credentials("tron")
            self._address = creds.get("address", "")

    @property
    def chain(self) -> ChainType:
        return ChainType.TRON

    @property
    def wallet_id(self) -> str:
        return self._wallet_id

    @property
    def address(self) -> str:
        return self._address

    def connect(self) -> ConnectionStatus:
        if not self._address:
            self._status = ConnectionStatus.UNCONFIGURED
            return self._status
        data = _tron_api_call(f"/v1/accounts/{self._address}")
        if data and "data" in data and len(data["data"]) > 0:
            self._status = ConnectionStatus.CONNECTED
        else:
            self._status = ConnectionStatus.ERROR
        return self._status

    def get_balance(self) -> list[CryptoBalance]:
        balances: list[CryptoBalance] = []
        if not self._address or self._status != ConnectionStatus.CONNECTED:
            return balances

        data = _tron_api_call(f"/v1/accounts/{self._address}")
        if not data or "data" not in data or not data["data"]:
            return balances

        account = data["data"][0]

        sun_balance = account.get("balance", 0)
        trx_balance = sun_balance / (10**SUN_DECIMALS)
        trx_usd = get_usd_price("TRX")
        balances.append(
            CryptoBalance(
                asset="TRX",
                symbol="TRX",
                balance=trx_balance,
                usd_value=trx_balance * trx_usd,
                decimals=SUN_DECIMALS,
                chain="tron",
                last_updated=datetime.now(UTC).isoformat(),
            )
        )

        trc20_list = account.get("trc20", [])
        for trc20_entry in trc20_list:
            for contract_addr, raw_balance in trc20_entry.items():
                symbol = self._get_trc20_symbol(contract_addr)
                try:
                    token_balance = int(raw_balance) / (10**6)
                except (ValueError, TypeError):
                    continue
                if token_balance <= 0:
                    continue
                token_usd = get_usd_price(symbol)
                balances.append(
                    CryptoBalance(
                        asset=symbol,
                        symbol=symbol,
                        balance=token_balance,
                        usd_value=token_balance * token_usd,
                        decimals=6,
                        chain="tron",
                        contract_address=contract_addr,
                        last_updated=datetime.now(UTC).isoformat(),
                    )
                )

        return balances

    def _get_trc20_symbol(self, contract_address: str) -> str:
        for symbol, addr in TRC20_TOKENS.items():
            if addr.lower() == contract_address.lower():
                return symbol
        return contract_address[:8]

    def get_transactions(self, limit: int = 50) -> list[CryptoTransaction]:
        txs: list[CryptoTransaction] = []
        if not self._address:
            return txs

        params = {
            "limit": str(min(limit, 200)),
            "order_by": "block_timestamp,desc",
        }
        data = _tron_api_call(f"/v1/accounts/{self._address}/transactions", params)
        if not data or "data" not in data:
            return txs

        for tx_data in data["data"][:limit]:
            try:
                tx = self._parse_transaction(tx_data)
                if tx:
                    txs.append(tx)
            except Exception as exc:
                logger.warning("Failed to parse Tron tx %s: %s", tx_data.get("txID", "")[:16], exc)

        return txs

    def _parse_transaction(self, tx_data: dict[str, Any]) -> CryptoTransaction | None:
        tx_id = tx_data.get("txID", "")
        if not tx_id:
            return None

        block_timestamp_ms = tx_data.get("block_timestamp", 0)
        timestamp = ""
        if block_timestamp_ms:
            timestamp = datetime.fromtimestamp(block_timestamp_ms / 1000, tz=UTC).isoformat()

        from_addr = tx_data.get("from", "") or tx_data.get("ownerAddress", "")
        to_addr = tx_data.get("to", "")
        value = int(tx_data.get("value", 0))
        fee = int(tx_data.get("fee", 0) or 0)

        raw_data = tx_data.get("raw_data", {})
        contracts = raw_data.get("contract", [])
        if contracts:
            param_value = contracts[0].get("parameter", {}).get("value", {})
            if not from_addr:
                from_addr = param_value.get("owner_address", "")
            if not to_addr:
                to_addr = param_value.get("to_address", "")
            if not value:
                value = int(param_value.get("amount", 0))

        trx_amount = value / (10**SUN_DECIMALS)
        fee_trx = fee / (10**SUN_DECIMALS)

        tx_type = "send" if from_addr.lower() == self._address.lower() else "receive"

        return CryptoTransaction(
            tx_hash=tx_id,
            chain="tron",
            timestamp=timestamp,
            from_address=from_addr,
            to_address=to_addr,
            asset="TRX",
            amount=trx_amount,
            fee=fee_trx,
            fee_asset="TRX",
            status="confirmed",
            tx_type=tx_type,
        )

    def get_withdrawals(self, limit: int = 20) -> list[CryptoWithdrawalInfo]:
        withdrawals: list[CryptoWithdrawalInfo] = []
        if not self._address:
            return withdrawals

        txs = self.get_transactions(limit=limit * 3)
        count = 0
        for tx in txs:
            if tx.from_address.lower() != self._address.lower():
                continue
            if count >= limit:
                break
            wd = CryptoWithdrawalInfo(
                tx_hash=tx.tx_hash,
                chain="tron",
                asset=tx.asset,
                amount=tx.amount,
                destination_address=tx.to_address,
                fee=tx.fee,
                status="confirmed",
                timestamp=tx.timestamp,
            )
            withdrawals.append(wd)
            count += 1

        return withdrawals
