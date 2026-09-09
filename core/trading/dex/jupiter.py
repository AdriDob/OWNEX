from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger("orion.trading.jupiter")

JUPITER_QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_URL = "https://quote-api.jup.ag/v6/swap"
JUPITER_PRICE_URL = "https://api.jup.ag/price/v2"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


@dataclass
class JupiterQuote:
    input_mint: str
    output_mint: str
    in_amount: int
    out_amount: int
    other_amount_threshold: int
    price_impact_pct: float
    route_plan: list[dict[str, Any]]
    slippage_bps: int
    swap_mode: str = "ExactIn"
    platform_fee: dict[str, Any] | None = None


@dataclass
class SwapResult:
    tx_id: str
    input_amount: int
    output_amount: int
    fee: int
    price_impact_pct: float


@dataclass
class TokenPrice:
    mint: str
    price_usd: Decimal
    price_change_24h: float = 0.0


class JupiterClient:
    def __init__(
        self,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        jupiter_api_url: str = "https://quote-api.jup.ag/v6",
        helius_api_key: str = "",
    ) -> None:
        self._rpc_url = rpc_url
        self._jupiter_url = jupiter_api_url.rstrip("/")
        self._helius_api_key = helius_api_key
        self._http = httpx.Client(timeout=30)

    def quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 100,
        swap_mode: str = "ExactIn",
        only_direct_routes: bool = False,
    ) -> JupiterQuote | None:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps),
            "swapMode": swap_mode,
        }
        if only_direct_routes:
            params["onlyDirectRoutes"] = "true"

        try:
            resp = self._http.get(f"{self._jupiter_url}/quote", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Jupiter quote failed: %s", e)
            return None

        error = data.get("error")
        if error:
            logger.warning("Jupiter quote error: %s", error)
            return None

        return JupiterQuote(
            input_mint=data.get("inputMint", input_mint),
            output_mint=data.get("outputMint", output_mint),
            in_amount=int(data.get("inAmount", 0)),
            out_amount=int(data.get("outAmount", 0)),
            other_amount_threshold=int(data.get("otherAmountThreshold", 0)),
            price_impact_pct=float(data.get("priceImpactPct", 0)),
            route_plan=data.get("routePlan", []),
            slippage_bps=slippage_bps,
            swap_mode=data.get("swapMode", "ExactIn"),
            platform_fee=data.get("platformFee"),
        )

    def build_swap_tx(
        self,
        quote: JupiterQuote,
        wallet_address: str,
        user_public_key: str | None = None,
        wrap_and_unwrap_sol: bool = True,
        dynamic_compute_unit_limit: bool = True,
        prioritization_fee_lamports: int | None = None,
    ) -> str | None:
        payload: dict[str, Any] = {
            "quoteResponse": {
                "inputMint": quote.input_mint,
                "outputMint": quote.output_mint,
                "inAmount": str(quote.in_amount),
                "outAmount": str(quote.out_amount),
                "otherAmountThreshold": str(quote.other_amount_threshold),
                "priceImpactPct": str(quote.price_impact_pct),
                "routePlan": quote.route_plan,
                "slippageBps": quote.slippage_bps,
                "swapMode": quote.swap_mode,
            },
            "userPublicKey": wallet_address,
            "wrapAndUnwrapSol": wrap_and_unwrap_sol,
            "dynamicComputeUnitLimit": dynamic_compute_unit_limit,
        }
        if user_public_key:
            payload["userPublicKey"] = user_public_key
        if prioritization_fee_lamports is not None:
            payload["prioritizationFeeLamports"] = prioritization_fee_lamports
        if quote.platform_fee:
            payload["quoteResponse"]["platformFee"] = quote.platform_fee

        try:
            resp = self._http.post(f"{self._jupiter_url}/swap", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Jupiter swap tx build failed: %s", e)
            return None

        tx = data.get("swapTransaction")
        if not tx:
            logger.error("Jupiter response missing swapTransaction")
            return None

        return tx

    def send_transaction(self, signed_tx_b64: str, skip_preflight: bool = True) -> str | None:
        tx_bytes = base64.b64decode(signed_tx_b64)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [
                base64.b64encode(tx_bytes).decode(),
                {
                    "encoding": "base64",
                    "skipPreflight": skip_preflight,
                    "preflightCommitment": "processed",
                },
            ],
        }
        try:
            resp = self._http.post(self._rpc_url, json=payload)
            resp.raise_for_status()
            result = resp.json()
        except httpx.HTTPError as e:
            logger.error("sendTransaction RPC failed: %s", e)
            return None

        err = result.get("error")
        if err:
            logger.error("sendTransaction RPC error: %s", err)
            return None

        sig = result.get("result")
        if sig:
            logger.info("Transaction sent: %s", sig)
        return sig

    def get_token_prices(self, mints: list[str]) -> dict[str, TokenPrice]:
        if not mints:
            return {}
        try:
            resp = self._http.get(
                JUPITER_PRICE_URL,
                params={"ids": ",".join(mints)},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Jupiter price fetch failed: %s", e)
            return {}

        prices: dict[str, TokenPrice] = {}
        for mint, info in data.get("data", {}).items():
            prices[mint] = TokenPrice(
                mint=mint,
                price_usd=Decimal(str(info.get("price", "0"))),
                price_change_24h=float(info.get("change24h", 0)),
            )
        return prices

    def get_token_balance(self, wallet_address: str, mint: str) -> int:
        if mint == SOL_MINT:
            return self._get_sol_balance(wallet_address)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"mint": mint},
                {"encoding": "jsonParsed"},
            ],
        }
        try:
            resp = self._http.post(self._rpc_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("getTokenAccountsByOwner failed: %s", e)
            return 0

        accounts = data.get("result", {}).get("value", [])
        if not accounts:
            return 0
        return int(
            accounts[0]
            .get("account", {})
            .get("data", {})
            .get("parsed", {})
            .get("info", {})
            .get("tokenAmount", {})
            .get("amount", 0)
        )

    def _get_sol_balance(self, wallet_address: str) -> int:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address],
        }
        try:
            resp = self._http.post(self._rpc_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("getBalance failed: %s", e)
            return 0
        return data.get("result", {}).get("value", 0)

    def close(self) -> None:
        self._http.close()
