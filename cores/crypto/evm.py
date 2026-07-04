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
        "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "CRV": "0xD533a949740bb3306d119CC777fa900bA034cd52",
        "SNX": "0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F",
        "MKR": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
        "COMP": "0xc00e94Cb662C3520282E6f5717214004A7f26888",
        "ATOM": "0x8D983cb9388EaC77af0474fA441C4815500Cb7BB",
        "MATIC": "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0",
        "SHIB": "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",
        "LDO": "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",
        "GRT": "0xc944E90C64B2c07662A292be6244BDf05Cda44a7",
        "FRAX": "0x853d955aCEf822Db058eb8505911ED77F175b99e",
        "APE": "0x4d224452801ACEd8B2F0aebE155379bb5D594381",
        "CRO": "0xA0b73E1Ff0B80914AB6fe0444E65848C4C34450b",
        "STETH": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
    },
    "polygon": {
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
        "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "LINK": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",
        "UNI": "0xb33EaAd8d922B1083446DC23f610c2567fB5180f",
        "AAVE": "0xD6DF932A45C0f255f85145f286eA0b292B21C90B",
        "CRV": "0x172370d5Cd63279eFa6d502DAB29171933a610AF",
        "SUSHI": "0x0b3F868E0BE5597D5DB7fEB59E1CadBb0fdDa50a",
        "QUICK": "0xB5C064F955D8e7F38fE0460C556a72987494eE17",
        "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
        "WBTC": "0x1bfd67037b42cf73acF2047067bd4F2C47D9BfD6",
        "GHST": "0x385Eeac5cB85A38A9a07A70c73e0a3271CfB54A7",
        "BAL": "0x9a71012B13CA4d3D0Cdc72A177DF3ef03b0E76A3",
        "TEL": "0xdf7837DE1F2Fa4631D716CF2502f8b230F1dcc32",
        "FISH": "0x3a3Df212b7AA91Aa0402B9039D2b2B4D8d42B4Cf",
        "GRT": "0x5fe2B58c013d7601147DcdD68C143A77499f5531",
        "COMP": "0x8505b9d2254A7Ae468c0E9dd10Ccea3A837aef5c",
        "CEL": "0xe1b8a677f183B7BC479634dc95444a3bCbC25358",
    },
    "bsc": {
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "BNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
        "ETH": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
        "DOT": "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402",
        "ADA": "0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47",
        "XRP": "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBE",
        "LINK": "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",
        "UNI": "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1",
        "DOGE": "0xbA2aE424d960c26247Dd6c32edC70B295c744C43",
        "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
        "XTZ": "0x16939ef78684453bfDFb47825F8a5F714f12623a",
        "ATOM": "0x0Eb3a705fc54725037CC9e008bDede697f62F335",
        "BAND": "0xAD6cAEb32CD2c308980a548bD0Bc5AA4306c6c18",
        "NEAR": "0x1Fa4a73a3F0133f0025378af00236f3aBDEE5F63",
        "AVAX": "0x1CE0c2827e2eF14D5C4f29a091d735A204794041",
        "SOL": "0x570A5D26f7765Ecb712C0924E4De545B89fD43dF",
        "TRX": "0x85EAC5Ac2F758618dFA09bDbe0cf174e7d574D5B",
    },
    "arbitrum": {
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "USDC": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
        "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
        "UNI": "0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0",
        "LINK": "0xf97f4df75117a78c1A5a0DBb814Ab92458339FBb",
        "MIM": "0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A",
        "GMX": "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a",
        "MAGIC": "0x539bdE0d7Dbd336b79148AA742883198bbF60342",
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
        "SUSHI": "0xd4d42F0b6DEF4CE0383636770eF773390d85c61A",
        "BAL": "0x040d1EdC9569d4Bab2D15287Dc5A4F10F56a56B8",
        "LDO": "0x13Ad51ed4F1B7e9Dc168d8a00cB3f4dDD85EfA7",
        "AAVE": "0xba5DdD1f9d7F570dc94a51479a000E3BCE967196F",
        "CRV": "0x11cDb42B0EB46D95f990BeDD4695A6E3fA034978",
        "FRAX": "0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F",
        "DPX": "0x6C2C06790b3E3E3c38e12Ee22F8183b37a13EE55",
        "rDPX": "0x32Eb7902D4134bf98A28b963D26de779AF92A212",
    },
    "optimism": {
        "USDT": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
        "USDC": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
        "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "OP": "0x4200000000000000000000000000000000000042",
        "UNI": "0x6fd9d7AD17242c41f7131d257212c44A0eA2d7B2",
        "LINK": "0x350a791Bfc2C21F9Ed5d10980Dad2e2638ffa7f6",
        "SNX": "0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4",
        "LDO": "0xFdb794692724153d1488CcDBE0C56c252596735F",
        "AAVE": "0x76FB31fb4af56892A25e32cFC43De717950c9278",
        "SUSHI": "0x3eaEb77b03dBEC0F2b5A1cC0294B0E6B6a5A6b0F",
        "PERP": "0x9e1028F5F1D5eDE59748FFceE5532503e364C2b6",
        "ALICE": "0x7A1dC0a7b0f9e6B0d4bE9e5A3E1B9c8D4f7A2E0C",
        "WBTC": "0x68f180fcCe6836688e9084f035309E29Bf0A2095",
        "BAL": "0xFE8B128bA8C78aabC59d4c64cEE7fF28e9379921",
        "LYRA": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        "THALES": "0x217D47011b23BB961eB6D93cA9945B7501a5BB11",
        "VELO": "0x3c8B2d1807d2c8c5E1C6E6D7E8F9A0B1C2D3E4F5",
        "KWENTA": "0x920Cf626a271321C151D027030D5d08aF699456b",
        "MAI": "0xdFA46478F9e5EA86d57387849598dbFB2e964b02",
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
