from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("orion.investment.memecoin")

DEXSCREENER_BASE = "https://api.dexscreener.com"
RUGCHECK_REPORT = "https://api.rugcheck.xyz/v1/tokens/{mint}/report"
SOL_MINT = "So11111111111111111111111111111111111111112"


class MemecoinAdapter:
    """Solana memecoin adapter built on real, keyless APIs.

    - Discovery: DexScreener (no key, 60 req/min).
    - Risk: RugCheck report (no key).
    - Quotes/routing: canonical ``cores.trading.dex.jupiter.JupiterClient``.
    - Execution defaults to DRY-RUN (simulated fills from real quotes).
      Live swaps require explicit ``allow_live=True`` + private key, sign
      locally with solders, and never log the key.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._private_key = self._config.get("private_key", "")
        self._rpc_url = self._config.get("rpc_url", "https://api.mainnet-beta.solana.com")
        self._max_slippage = int(self._config.get("max_slippage_bps", 500))
        self._min_liquidity_usd = float(self._config.get("min_liquidity_usd", 5000.0))
        self._allow_live = bool(self._config.get("allow_live", False))
        self._dry_run = not (self._allow_live and self._private_key)
        self._connected = False
        self._jupiter: Any = None

    @property
    def name(self) -> str:
        return "memecoin"

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_dry_run(self) -> bool:
        return self._dry_run

    def _jupiter_client(self) -> Any:
        if self._jupiter is None:
            from cores.trading.dex.jupiter import JupiterClient

            self._jupiter = JupiterClient(rpc_url=self._rpc_url)
        return self._jupiter

    async def connect(self) -> bool:
        """Verify Solana RPC reachability (raw JSON-RPC, no solana-py needed)."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._rpc_url,
                    json={"jsonrpc": "2.0", "id": 1, "method": "getHealth"},
                )
                ok = resp.status_code == 200 and resp.json().get("result") == "ok"
        except Exception as exc:
            logger.error("Solana RPC unreachable: %s", exc)
            self._connected = False
            return False
        self._connected = bool(ok)
        if self._dry_run:
            logger.info("Memecoin adapter connected (RPC ok) in DRY-RUN mode")
        return self._connected

    # ── Discovery (DexScreener, keyless) ──

    async def scan_new_tokens(self, min_liquidity_usd: float | None = None) -> list[dict[str, Any]]:
        """Latest Solana token profiles enriched with pair stats.

        Returns normalized dicts; [] on any failure (never mocks).
        """
        import httpx

        min_liq = min_liquidity_usd if min_liquidity_usd is not None else self._min_liquidity_usd
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                prof = await client.get(f"{DEXSCREENER_BASE}/token-profiles/latest/v1")
                if prof.status_code != 200:
                    logger.warning("DexScreener profiles HTTP %s", prof.status_code)
                    return []
                addrs = [
                    str(p.get("tokenAddress"))
                    for p in prof.json()
                    if isinstance(p, dict) and p.get("chainId") == "solana" and p.get("tokenAddress")
                ][:30]
                if not addrs:
                    return []
                det = await client.get(f"{DEXSCREENER_BASE}/tokens/v1/solana/{','.join(addrs)}")
                if det.status_code != 200:
                    logger.warning("DexScreener tokens HTTP %s", det.status_code)
                    return []
                out = []
                for pair in det.json():
                    if not isinstance(pair, dict):
                        continue
                    liq = ((pair.get("liquidity") or {}).get("usd")) or 0
                    if liq < min_liq:
                        continue
                    base = pair.get("baseToken") or {}
                    out.append(
                        {
                            "mint": base.get("address", ""),
                            "symbol": base.get("symbol", ""),
                            "name": base.get("name", ""),
                            "liquidity_usd": liq,
                            "market_cap_usd": pair.get("marketCap"),
                            "fdv_usd": pair.get("fdv"),
                            "volume_h24": (pair.get("volume") or {}).get("h24"),
                            "price_usd": pair.get("priceUsd"),
                            "price_change_h24": (pair.get("priceChange") or {}).get("h24"),
                            "pair_created_at": pair.get("pairCreatedAt"),
                            "dex": pair.get("dexId"),
                            "boosts_active": ((pair.get("boosts") or {}).get("active")) or 0,
                            "url": pair.get("url", ""),
                        }
                    )
                return out
        except Exception as exc:
            logger.error("DexScreener scan failed: %s", exc)
            return []

    async def scan_opportunities(self, min_liquidity_usd: float | None = None, **_: Any) -> list[dict[str, Any]]:
        """Registry-compatible scan entrypoint (see InvestmentAdapterRegistry)."""
        return await self.scan_new_tokens(min_liquidity_usd)

    # ── Risk (RugCheck, keyless) ──

    async def get_token_metrics(self, mint: str) -> dict[str, Any]:
        """Holder distribution + risk flags from RugCheck."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(RUGCHECK_REPORT.format(mint=mint))
                if resp.status_code != 200:
                    return {"error": "not found", "mint": mint}
                data = resp.json()
                return {
                    "holder_count": data.get("holderCount", 0),
                    "top_10_pct": data.get("top10HolderPercent", 0),
                    "liquidity_locked": data.get("liquidityLocked", False),
                    "mint_disabled": data.get("mintDisabled", False),
                    "freeze_disabled": data.get("freezeDisabled", False),
                    "score": data.get("score", 0),
                    "risks": data.get("risks", []),
                }
        except Exception as exc:
            return {"error": str(exc), "mint": mint}

    # ── Quotes (canonical Jupiter client) ──

    async def quote_buy(self, mint: str, amount_sol: float, slippage_bps: int | None = None) -> dict[str, Any] | None:
        """Real Jupiter quote for SOL -> mint (no funds move)."""
        client = self._jupiter_client()
        quote = await asyncio.to_thread(
            client.quote,
            SOL_MINT,
            mint,
            int(amount_sol * 1_000_000_000),
            slippage_bps or self._max_slippage,
        )
        if quote is None:
            return None
        return {
            "in_sol": amount_sol,
            "out_amount": quote.out_amount,
            "price_impact_pct": quote.price_impact_pct,
            "slippage_bps": quote.slippage_bps,
        }

    async def quote_sell(
        self, mint: str, amount_base_units: int, slippage_bps: int | None = None
    ) -> dict[str, Any] | None:
        """Real Jupiter quote for mint -> SOL (no funds move)."""
        client = self._jupiter_client()
        quote = await asyncio.to_thread(
            client.quote, mint, SOL_MINT, int(amount_base_units), slippage_bps or self._max_slippage
        )
        if quote is None:
            return None
        return {
            "in_base_units": int(amount_base_units),
            "out_lamports": quote.out_amount,
            "price_impact_pct": quote.price_impact_pct,
            "slippage_bps": quote.slippage_bps,
        }

    # ── Execution ──

    async def buy(self, mint: str, amount_sol: float, slippage_bps: int | None = None) -> dict[str, Any]:
        """Buy mint with SOL. Dry-run (default) simulates the fill from a real quote."""
        quote = await self.quote_buy(mint, amount_sol, slippage_bps)
        if quote is None:
            return {"status": "failed", "error": "no Jupiter route", "dry_run": self._dry_run}
        if self._dry_run:
            return {"status": "simulated", "dry_run": True, "mint": mint, **quote}
        return await self._live_swap(SOL_MINT, mint, int(amount_sol * 1_000_000_000), slippage_bps)

    async def sell(self, mint: str, amount_pct: float = 100.0) -> dict[str, Any]:
        """Sell amount_pct of the wallet's mint balance. Dry-run simulates."""
        try:
            client = self._jupiter_client()
            balance = await asyncio.to_thread(client.get_token_balance, self._wallet_address(), mint)
        except Exception as exc:
            return {"status": "error", "error": str(exc), "dry_run": self._dry_run}
        amount = int(balance * max(0.0, min(100.0, amount_pct)) / 100.0)
        quote = await self.quote_sell(mint, amount)
        if quote is None:
            return {"status": "failed", "error": "no Jupiter route", "dry_run": self._dry_run}
        if self._dry_run:
            return {"status": "simulated", "dry_run": True, "mint": mint, **quote}
        return await self._live_swap(mint, SOL_MINT, amount, None)

    def _wallet_address(self) -> str:
        from solders.keypair import Keypair

        return str(Keypair.from_base58_string(self._private_key).pubkey())

    async def _live_swap(
        self, input_mint: str, output_mint: str, amount: int, slippage_bps: int | None
    ) -> dict[str, Any]:
        """Build, locally sign (solders) and send a Jupiter swap. Live funds."""
        from solders.keypair import Keypair
        from solders.transaction import VersionedTransaction

        try:
            client = self._jupiter_client()
            wallet = self._wallet_address()
            quote = await asyncio.to_thread(
                client.quote, input_mint, output_mint, amount, slippage_bps or self._max_slippage
            )
            if quote is None:
                return {"status": "failed", "error": "no Jupiter route", "dry_run": False}
            swap_b64 = await asyncio.to_thread(client.build_swap_tx, quote, wallet)
            if not swap_b64:
                return {"status": "failed", "error": "swap build failed", "dry_run": False}
            import base64

            raw = base64.b64decode(swap_b64)
            tx = VersionedTransaction.from_bytes(raw)
            keypair = Keypair.from_base58_string(self._private_key)
            signed = VersionedTransaction(tx.message, [keypair])
            sig = await asyncio.to_thread(client.send_transaction, base64.b64encode(bytes(signed)).decode())
            if not sig:
                return {"status": "failed", "error": "send failed", "dry_run": False}
            return {"status": "executed", "txid": sig, "dry_run": False}
        except Exception as exc:
            logger.error("Live swap failed: %s", exc)
            return {"status": "error", "error": str(exc), "dry_run": False}
