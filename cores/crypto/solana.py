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

logger = logging.getLogger("ownex.crypto.solana")

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
SOL_DECIMALS = 9


def _rpc_call(method: str, params: list[Any]) -> dict[str, Any] | None:
    import urllib.request

    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }).encode()
    req = urllib.request.Request(SOLANA_RPC, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.warning("Solana RPC call failed %s: %s", method, exc)
        return None


class SolanaConnector(CryptoConnector):
    def __init__(self, wallet_id: str, address: str = "") -> None:
        self._wallet_id = wallet_id
        self._address = address
        self._status = ConnectionStatus.UNCONFIGURED

        if not self._address:
            vault = get_identity_vault()
            creds = vault.get_credentials("solana")
            self._address = creds.get("address", "")

    @property
    def chain(self) -> ChainType:
        return ChainType.SOLANA

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
        result = _rpc_call("getRecentBlockhash", [])
        if result and "result" in result:
            self._status = ConnectionStatus.CONNECTED
        else:
            self._status = ConnectionStatus.ERROR
        return self._status

    def get_balance(self) -> list[CryptoBalance]:
        balances: list[CryptoBalance] = []
        if not self._address or self._status != ConnectionStatus.CONNECTED:
            return balances
        result = _rpc_call("getBalance", [self._address])
        if not result or "result" not in result:
            return balances
        lamports = result["result"].get("value", 0)
        balance = lamports / (10**SOL_DECIMALS)
        usd_price = get_usd_price("SOL")
        balances.append(
            CryptoBalance(
                asset="SOL",
                symbol="SOL",
                balance=balance,
                usd_value=balance * usd_price,
                decimals=SOL_DECIMALS,
                chain="solana",
                last_updated=datetime.now(UTC).isoformat(),
            )
        )
        return balances

    def get_transactions(self, limit: int = 50) -> list[CryptoTransaction]:
        txs: list[CryptoTransaction] = []
        if not self._address:
            return txs

        sigs_result = _rpc_call("getSignaturesForAddress", [self._address, {"limit": min(limit, 100)}])
        if not sigs_result or "result" not in sigs_result:
            return txs

        for sig_info in sigs_result["result"]:
            signature = sig_info.get("signature", "")
            if not signature:
                continue

            tx_result = _rpc_call("getTransaction", [signature, {"encoding": "jsonParsed"}])
            if not tx_result or "result" not in tx_result or tx_result["result"] is None:
                continue

            tx_data = tx_result["result"]
            try:
                meta = tx_data.get("meta") or {}
                if meta.get("err") is not None:
                    continue

                block_time = tx_data.get("blockTime", 0)
                account_keys = tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
                keys: list[str] = [k.get("pubkey", k) if isinstance(k, dict) else k for k in account_keys]
                pre_balances = meta.get("preBalances", [])
                post_balances = meta.get("postBalances", [])
                fee_lamports = meta.get("fee", 0)

                if not keys or not pre_balances or not post_balances:
                    continue

                try:
                    addr_idx = keys.index(self._address)
                except ValueError:
                    continue

                change_lamports = post_balances[addr_idx] - pre_balances[addr_idx]
                is_outgoing = change_lamports < 0
                amount_lamports = abs(change_lamports)
                fee_sol = fee_lamports / (10**SOL_DECIMALS)
                amount_sol = amount_lamports / (10**SOL_DECIMALS)

                if addr_idx == 0 and is_outgoing:
                    amount_sol -= fee_sol

                if amount_sol <= 0:
                    continue

                timestamp = ""
                if block_time:
                    timestamp = datetime.fromtimestamp(block_time, tz=UTC).isoformat()

                usd_price = get_usd_price("SOL")
                tx_type = "send" if is_outgoing else "receive"

                if is_outgoing:
                    to_addr = next((key for i, key in enumerate(keys) if i != addr_idx and pre_balances[i] < post_balances[i]), "")
                    from_addr = self._address
                else:
                    from_addr = next((key for i, key in enumerate(keys) if i != addr_idx and pre_balances[i] > post_balances[i]), "")
                    to_addr = self._address

                tx = CryptoTransaction(
                    tx_hash=signature,
                    chain="solana",
                    block_number=tx_data.get("slot", 0),
                    timestamp=timestamp,
                    from_address=from_addr,
                    to_address=to_addr,
                    asset="SOL",
                    amount=amount_sol,
                    usd_value=amount_sol * usd_price,
                    fee=fee_sol,
                    fee_asset="SOL",
                    status="confirmed",
                    tx_type=tx_type,
                )
                txs.append(tx)
            except Exception as exc:
                logger.warning("Failed to parse Solana tx %s: %s", signature[:16], exc)

        txs.sort(key=lambda t: t.timestamp, reverse=True)
        return txs[:limit]

    def get_withdrawals(self, limit: int = 20) -> list[CryptoWithdrawalInfo]:
        withdrawals: list[CryptoWithdrawalInfo] = []
        txs = self.get_transactions(limit=limit * 3)
        for tx in txs:
            if tx.tx_type != "send":
                continue
            wd = CryptoWithdrawalInfo(
                tx_hash=tx.tx_hash,
                chain="solana",
                asset="SOL",
                amount=tx.amount,
                usd_value=tx.usd_value,
                destination_address=tx.to_address,
                fee=tx.fee,
                status=tx.status,
                timestamp=tx.timestamp,
            )
            withdrawals.append(wd)
        return withdrawals[:limit]
