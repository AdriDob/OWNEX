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

logger = logging.getLogger("catseye.crypto.evm")

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]

SUPPORTED_CHAINS: dict[str, dict[str, Any]] = {
    "ethereum": {
        "chain_id": 1,
        "currency": "ETH",
        "decimals": 18,
        "explorer": "https://api.etherscan.io/api",
        "rpc_fallback": "https://eth.llamarpc.com",
    },
    "polygon": {
        "chain_id": 137,
        "currency": "MATIC",
        "decimals": 18,
        "explorer": "https://api.polygonscan.com/api",
        "rpc_fallback": "https://polygon.llamarpc.com",
    },
    "bsc": {
        "chain_id": 56,
        "currency": "BNB",
        "decimals": 18,
        "explorer": "https://api.bscscan.com/api",
        "rpc_fallback": "https://binance.llamarpc.com",
    },
    "arbitrum": {
        "chain_id": 42161,
        "currency": "ETH",
        "decimals": 18,
        "explorer": "https://api.arbiscan.io/api",
        "rpc_fallback": "https://arbitrum.llamarpc.com",
    },
    "optimism": {
        "chain_id": 10,
        "currency": "ETH",
        "decimals": 18,
        "explorer": "https://api-optimistic.etherscan.io/api",
        "rpc_fallback": "https://optimism.llamarpc.com",
    },
}

ERC20_TOKENS: dict[str, dict[str, str]] = {
    "ethereum": {
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
    },
    "polygon": {
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
        "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "LINK": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",
    },
    "bsc": {
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "BNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
        "ETH": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
    },
    "arbitrum": {
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "USDC": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
        "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
    },
    "optimism": {
        "USDT": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
        "USDC": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
        "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "OP": "0x4200000000000000000000000000000000000042",
    },
}


def _rpc_call(rpc_url: str, method: str, params: list[Any]) -> dict[str, Any] | None:
    import urllib.request
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }).encode()
    req = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.warning("RPC call failed %s %s: %s", rpc_url[:40], method, exc)
        return None


def _explorer_api_call(explorer_url: str, params: dict[str, str], api_key: str = "") -> dict[str, Any] | None:
    import urllib.request
    if api_key:
        params["apikey"] = api_key
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{explorer_url}?{qs}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        logger.warning("Explorer API call failed: %s", exc)
        return None


def _parse_hex_amount(hex_str: str, decimals: int) -> float:
    try:
        val = int(hex_str, 16)
        return val / (10 ** decimals)
    except (ValueError, TypeError):
        return 0.0


class EVMConnector(CryptoConnector):
    def __init__(
        self,
        wallet_id: str,
        chain_name: str = "ethereum",
        address: str = "",
        rpc_url: str = "",
        explorer_api_key: str = "",
    ) -> None:
        self._wallet_id = wallet_id
        self._chain_name = chain_name.lower()
        self._address = address
        self._rpc_url = rpc_url
        self._explorer_api_key = explorer_api_key
        chain_info = SUPPORTED_CHAINS.get(self._chain_name, SUPPORTED_CHAINS["ethereum"])
        self._chain_info = chain_info
        self._status = ConnectionStatus.UNCONFIGURED

        if not self._rpc_url:
            vault = get_identity_vault()
            creds = vault.get_credentials(f"evm_{chain_name}")
            self._rpc_url = creds.get("rpc_url", "") or chain_info["rpc_fallback"]
            self._explorer_api_key = creds.get("explorer_api_key", "")
            self._address = self._address or creds.get("address", "")

    @property
    def chain(self) -> ChainType:
        return ChainType.EVM

    @property
    def wallet_id(self) -> str:
        return self._wallet_id

    @property
    def chain_name(self) -> str:
        return self._chain_name

    @property
    def address(self) -> str:
        return self._address

    def connect(self) -> ConnectionStatus:
        if not self._rpc_url:
            self._status = ConnectionStatus.UNCONFIGURED
            return self._status
        result = _rpc_call(self._rpc_url, "eth_blockNumber", [])
        if result and "result" in result:
            self._status = ConnectionStatus.CONNECTED
        else:
            self._status = ConnectionStatus.ERROR
        return self._status

    def get_balance(self) -> list[CryptoBalance]:
        balances: list[CryptoBalance] = []
        if not self._address or self._status != ConnectionStatus.CONNECTED:
            return balances

        native_balance = self._get_native_balance()
        if native_balance:
            balances.append(native_balance)

        tokens = ERC20_TOKENS.get(self._chain_name, {})
        for symbol, contract_addr in tokens.items():
            bal = self._get_erc20_balance(contract_addr, symbol)
            if bal and bal.balance > 0:
                balances.append(bal)

        return balances

    def _get_native_balance(self) -> CryptoBalance | None:
        result = _rpc_call(self._rpc_url, "eth_getBalance", [self._address, "latest"])
        if not result or "result" not in result:
            return None
        currency = self._chain_info["currency"]
        decimals = self._chain_info["decimals"]
        balance = _parse_hex_amount(result["result"], decimals)
        usd_price = get_usd_price(currency)
        return CryptoBalance(
            asset=currency,
            symbol=currency,
            balance=balance,
            usd_value=balance * usd_price,
            decimals=decimals,
            chain=self._chain_name,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    def _get_erc20_balance(self, contract_address: str, symbol: str) -> CryptoBalance | None:
        data = "0x70a08231" + self._address[2:].zfill(64)
        result = _rpc_call(self._rpc_url, "eth_call", [{
            "to": contract_address,
            "data": data,
        }, "latest"])
        if not result or "result" not in result:
            return None
        balance = _parse_hex_amount(result["result"], 18)
        if balance <= 0:
            return None
        usd_price = get_usd_price(symbol)
        return CryptoBalance(
            asset=symbol,
            symbol=symbol,
            balance=balance,
            usd_value=balance * usd_price,
            decimals=18,
            chain=self._chain_name,
            contract_address=contract_address,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    def get_transactions(self, limit: int = 50) -> list[CryptoTransaction]:
        txs: list[CryptoTransaction] = []
        if not self._address:
            return txs

        explorer = self._chain_info["explorer"]
        params: dict[str, str] = {
            "module": "account",
            "action": "txlist",
            "address": self._address,
            "startblock": "0",
            "endblock": "99999999",
            "page": "1",
            "offset": str(min(limit, 100)),
            "sort": "desc",
        }
        data = _explorer_api_call(explorer, params, self._explorer_api_key)
        if data and data.get("status") == "1" and "result" in data:
            for tx_data in data["result"][:limit]:
                try:
                    tx = CryptoTransaction(
                        tx_hash=tx_data.get("hash", ""),
                        chain=self._chain_name,
                        block_number=int(tx_data.get("blockNumber", "0"), 16) if tx_data.get("blockNumber", "0").startswith("0x") else int(tx_data.get("blockNumber", 0)),
                        timestamp=datetime.fromtimestamp(int(tx_data.get("timeStamp", "0"), 16) if tx_data.get("timeStamp", "0").startswith("0x") else int(tx_data.get("timeStamp", 0)), tz=timezone.utc).isoformat(),
                        from_address=tx_data.get("from", ""),
                        to_address=tx_data.get("to", ""),
                        asset=self._chain_info["currency"],
                        amount=_parse_hex_amount(tx_data.get("value", "0x0"), self._chain_info["decimals"]),
                        fee=_parse_hex_amount(tx_data.get("gasPrice", "0x0"), 9) * int(tx_data.get("gasUsed", "0"), 16) / 1e9 if tx_data.get("gasUsed", "0").startswith("0x") else 0,
                        fee_asset=self._chain_info["currency"],
                        status="confirmed" if tx_data.get("isError") == "0" else "failed",
                        tx_type="send" if tx_data.get("from", "").lower() == self._address.lower() else "receive",
                    )
                    txs.append(tx)
                except Exception as exc:
                    logger.warning("Failed to parse tx %s: %s", tx_data.get("hash", "")[:16], exc)

        erc20_params = {**params, "action": "tokentx"}
        erc20_data = _explorer_api_call(explorer, erc20_params, self._explorer_api_key)
        if erc20_data and erc20_data.get("status") == "1" and "result" in erc20_data:
            for tx_data in erc20_data["result"][:limit]:
                try:
                    tx = CryptoTransaction(
                        tx_hash=tx_data.get("hash", ""),
                        chain=self._chain_name,
                        block_number=int(tx_data.get("blockNumber", "0")),
                        timestamp=datetime.fromtimestamp(int(tx_data.get("timeStamp", "0")), tz=timezone.utc).isoformat(),
                        from_address=tx_data.get("from", ""),
                        to_address=tx_data.get("to", ""),
                        asset=tx_data.get("tokenSymbol", "UNKNOWN"),
                        amount=int(tx_data.get("value", "0")) / (10 ** int(tx_data.get("tokenDecimal", "18"))),
                        fee=0,
                        fee_asset=self._chain_info["currency"],
                        status="confirmed",
                        tx_type="send" if tx_data.get("from", "").lower() == self._address.lower() else "receive",
                    )
                    txs.append(tx)
                except Exception as exc:
                    logger.warning("Failed to parse ERC20 tx %s: %s", tx_data.get("hash", "")[:16], exc)

        txs.sort(key=lambda t: t.timestamp, reverse=True)
        return txs[:limit]

    def get_withdrawals(self, limit: int = 20) -> list[CryptoWithdrawalInfo]:
        withdrawals: list[CryptoWithdrawalInfo] = []
        if not self._address:
            return withdrawals
        explorer = self._chain_info["explorer"]
        params: dict[str, str] = {
            "module": "account",
            "action": "txlist",
            "address": self._address,
            "startblock": "0",
            "endblock": "99999999",
            "page": "1",
            "offset": str(min(limit * 3, 100)),
            "sort": "desc",
        }
        data = _explorer_api_call(explorer, params, self._explorer_api_key)
        if data and data.get("status") == "1" and "result" in data:
            for tx_data in data["result"]:
                if tx_data.get("from", "").lower() != self._address.lower():
                    continue
                try:
                    wd = CryptoWithdrawalInfo(
                        tx_hash=tx_data.get("hash", ""),
                        chain=self._chain_name,
                        asset=self._chain_info["currency"],
                        amount=_parse_hex_amount(tx_data.get("value", "0x0"), self._chain_info["decimals"]),
                        destination_address=tx_data.get("to", ""),
                        fee=_parse_hex_amount(tx_data.get("gasPrice", "0x0"), 9) * int(tx_data.get("gasUsed", "0"), 16) / 1e9 if tx_data.get("gasUsed", "0").startswith("0x") else 0,
                        status="confirmed" if tx_data.get("isError") == "0" else "failed",
                        confirmations=int(tx_data.get("confirmations", "0")),
                        confirmations_required=12,
                        timestamp=datetime.fromtimestamp(int(tx_data.get("timeStamp", "0"), 16) if tx_data.get("timeStamp", "0").startswith("0x") else int(tx_data.get("timeStamp", 0)), tz=timezone.utc).isoformat(),
                    )
                    withdrawals.append(wd)
                except Exception as exc:
                    logger.warning("Failed to parse withdrawal tx %s: %s", tx_data.get("hash", "")[:16], exc)

        return sorted(withdrawals, key=lambda w: w.timestamp, reverse=True)[:limit]
