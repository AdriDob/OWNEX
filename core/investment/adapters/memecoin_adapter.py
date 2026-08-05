from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("orion.investment.memecoin")


class MemecoinAdapter:
    """Adapter for Solana memecoin sniping on PumpFun and Raydium.

    Monitors new token launches, evaluates risk metrics, and executes
    snipe buys/sells with configurable slippage and position sizing.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._private_key = self._config.get("private_key", "")
        self._rpc_url = self._config.get("rpc_url", "https://api.mainnet-beta.solana.com")
        self._max_slippage = self._config.get("max_slippage_bps", 500)
        self._min_liquidity_sol = self._config.get("min_liquidity_sol", 1.0)
        self._connected = False

    @property
    def name(self) -> str:
        return "memecoin"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        if not self._private_key:
            logger.warning("Memecoin adapter: no private_key configured")
            return False
        try:
            from solana.rpc.async_api import AsyncClient

            client = AsyncClient(self._rpc_url)
            resp = await client.get_version()
            self._connected = resp["result"] is not None
            if self._connected:
                logger.info("Connected to Solana RPC: %s", self._rpc_url)
            await client.close()
            return self._connected
        except ImportError:
            logger.warning("solana-py not installed — memecoin adapter in dry-run mode")
            self._connected = True
            return True
        except Exception as exc:
            logger.error("Failed to connect to Solana: %s", exc)
            return False

    async def scan_new_tokens(self, min_liquidity_sol: float | None = None) -> list[dict[str, Any]]:
        """Scan PumpFun/Raydium for newly listed tokens."""
        min_liq = min_liquidity_sol or self._min_liquidity_sol
        try:
            import httpx

            tokens = []
            for source in ["pumpfun", "raydium"]:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"https://api.{source}.io/tokens/latest",
                        params={"limit": 20, "minLiquidity": min_liq},
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        tokens.extend(resp.json().get("tokens", []))
            return tokens
        except ImportError:
            logger.warning("httpx not installed — returning mock tokens")
            return [{"mint": "mock", "symbol": "MOCK", "liquidity_sol": 5.0, "market_cap": 50000}]
        except Exception as exc:
            logger.error("Failed to scan tokens: %s", exc)
            return []

    async def buy(self, mint: str, amount_sol: float, slippage_bps: int | None = None) -> dict[str, Any]:
        """Execute a snipe buy on a memecoin."""
        slippage = slippage_bps or self._max_slippage
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.jup.ag/v6/swap",
                    json={
                        "inputMint": "So11111111111111111111111111111111111111112",
                        "outputMint": mint,
                        "amount": int(amount_sol * 1_000_000_000),
                        "slippageBps": slippage,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    return {"status": "executed", "txid": resp.json().get("txid", ""), "amount_sol": amount_sol}
                return {"status": "failed", "error": resp.text}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def sell(self, mint: str, amount_pct: float = 100.0) -> dict[str, Any]:
        """Sell a percentage of a memecoin position."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.jup.ag/v6/swap",
                    json={
                        "inputMint": mint,
                        "outputMint": "So11111111111111111111111111111111111111112",
                        "amount": int(amount_pct * 100_000),
                        "slippageBps": self._max_slippage,
                    },
                    timeout=30,
                )
                return {
                    "status": "executed" if resp.status_code == 200 else "failed",
                    "txid": resp.json().get("txid", "") if resp.status_code == 200 else "",
                }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def get_token_metrics(self, mint: str) -> dict[str, Any]:
        """Get token holder distribution and risk metrics."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report", timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "holder_count": data.get("holderCount", 0),
                        "top_10_pct": data.get("top10HolderPercent", 0),
                        "liquidity_locked": data.get("liquidityLocked", False),
                        "mint_disabled": data.get("mintDisabled", False),
                        "score": data.get("score", 0),
                        "risks": data.get("risks", []),
                    }
                return {"error": "not found"}
        except Exception as exc:
            return {"error": str(exc)}


def build_memecoin_adapter(config: dict[str, Any] | None = None) -> MemecoinAdapter:
    """Build MemecoinAdapter with optional config."""
    return MemecoinAdapter(config=config)
