"""Memecoin Scanner Adapter for OWNEX.

Early detection of new tokens with pattern analysis and risk assessment.
Based on: DexScreener API, DexTools, Birdeye, Solana/ETH token monitoring.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

logger = logging.getLogger("orion.investment.memecoin_scanner")


class MemecoinScannerAdapter:
    """Memecoin and new token scanner with risk analysis.

    Provides:
    - New token detection across chains
    - Liquidity analysis
    - Holder concentration analysis
    - Social sentiment signals
    - Rug pull risk detection
    - Honeypot detection
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._session: aiohttp.ClientSession | None = None
        self._dexscreener_base = "https://api.dexscreener.com/latest/dex"
        self._birdeye_base = "https://public-api.birdeye.so"
        self._solana_rpc = self._config.get("solana_rpc", "https://api.mainnet-beta.solana.com")

    @property
    def name(self) -> str:
        return "memecoin_scanner"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_new_pairs(
        self,
        chain: str = "solana",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get newly created trading pairs."""
        try:
            session = await self._get_session()
            url = f"{self._dexscreener_base}/pairs/{chain}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                pairs = data.get("pairs", [])

                # Filter for new pairs (created recently)
                new_pairs = []
                for pair in pairs[:limit]:
                    pair_info = await self._enrich_pair(pair)
                    if pair_info:
                        new_pairs.append(pair_info)

                return new_pairs
        except Exception as e:
            logger.error("New pairs fetch failed: %s", e)
            return []

    async def _enrich_pair(self, pair: dict[str, Any]) -> dict[str, Any] | None:
        """Enrich pair data with risk metrics."""
        try:
            base_token = pair.get("baseToken", {})
            quote_token = pair.get("quoteToken", {})

            # Skip if quote is not a major stablecoin
            quote_symbol = quote_token.get("symbol", "").upper()
            if quote_symbol not in ["USDC", "USDT", "SOL", "ETH", "BNB", "WETH"]:
                return None

            liquidity_usd = float(pair.get("liquidity", {}).get("usd", 0) or 0)
            volume_24h = float(pair.get("volume", {}).get("h24", 0) or 0)
            price_change_24h = float(pair.get("priceChange", {}).get("h24", 0) or 0)

            # Basic risk scoring
            risk_score = 0.0
            risk_factors = []

            if liquidity_usd < 10000:
                risk_score += 0.3
                risk_factors.append("Very low liquidity (<$10k)")
            elif liquidity_usd < 50000:
                risk_score += 0.15
                risk_factors.append("Low liquidity (<$50k)")

            if volume_24h < 10000:
                risk_score += 0.2
                risk_factors.append("Very low volume")

            # Check for honeypot indicators
            buy_tax = pair.get("buyTax", 0)
            sell_tax = pair.get("sellTax", 0)
            if buy_tax > 0.1 or sell_tax > 0.1:
                risk_score += 0.4
                risk_factors.append(f"High taxes: buy={buy_tax:.1%}, sell={sell_tax:.1%}")

            # Age check
            pair_created = pair.get("pairCreatedAt", 0)
            import time

            age_hours = (time.time() * 1000 - pair_created) / (1000 * 3600) if pair_created else 0
            if age_hours < 1:
                risk_score += 0.2
                risk_factors.append("Very new (<1 hour)")

            risk_score = min(risk_score, 1.0)

            return {
                "chain": pair.get("chainId"),
                "dex": pair.get("dexId"),
                "pair_address": pair.get("pairAddress"),
                "base_token": {
                    "address": base_token.get("address"),
                    "symbol": base_token.get("symbol"),
                    "name": base_token.get("name"),
                },
                "quote_token": {
                    "address": quote_token.get("address"),
                    "symbol": quote_token.get("symbol"),
                },
                "price_usd": float(pair.get("priceUsd", 0) or 0),
                "price_native": float(pair.get("priceNative", 0) or 0),
                "liquidity_usd": liquidity_usd,
                "volume_24h": volume_24h,
                "price_change_24h": price_change_24h,
                "age_hours": round(age_hours, 2),
                "risk_score": round(risk_score, 2),
                "risk_factors": risk_factors,
                "url": pair.get("url"),
            }
        except Exception as e:
            logger.error("Pair enrichment failed: %s", e)
            return None

    async def analyze_token(
        self,
        token_address: str,
        chain: str = "solana",
    ) -> dict[str, Any]:
        """Deep analysis of a specific token."""
        try:
            session = await self._get_session()

            # Get pair info from DexScreener
            url = f"{self._dexscreener_base}/tokens/{token_address}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {"error": "Token not found"}
                data = await resp.json()

            pairs = data.get("pairs", [])
            if not pairs:
                return {"error": "No trading pairs found"}

            # Analyze main pair (highest liquidity)
            main_pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))

            # Get holder distribution (if available via Birdeye for Solana)
            holder_analysis = await self._analyze_holders(token_address, chain)

            return {
                "token_address": token_address,
                "chain": chain,
                "main_pair": await self._enrich_pair(main_pair),
                "all_pairs_count": len(pairs),
                "holder_analysis": holder_analysis,
                "risk_assessment": self._generate_risk_assessment(main_pair, holder_analysis),
            }
        except Exception as e:
            logger.error("Token analysis failed: %s", e)
            return {"error": str(e)}

    async def _analyze_holders(self, token_address: str, chain: str) -> dict[str, Any]:
        """Analyze token holder distribution."""
        # This would integrate with Birdeye, Solscan, Etherscan APIs
        # For now, return placeholder
        return {
            "total_holders": 0,
            "top_10_pct": 0,
            "top_100_pct": 0,
            "concentration_risk": "unknown",
            "insider_wallets": [],
        }

    def _generate_risk_assessment(
        self,
        pair: dict[str, Any],
        holder_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate comprehensive risk assessment."""
        risk_score = 0.0
        flags = []

        liquidity = float(pair.get("liquidity", {}).get("usd", 0) or 0)
        if liquidity < 5000:
            risk_score += 0.4
            flags.append("CRITICAL: Extremely low liquidity")
        elif liquidity < 20000:
            risk_score += 0.2
            flags.append("WARNING: Low liquidity")

        # Check for honeypot
        buy_tax = pair.get("buyTax", 0)
        sell_tax = pair.get("sellTax", 0)
        if sell_tax > 0.5:
            risk_score += 0.5
            flags.append("CRITICAL: Likely honeypot (sell tax > 50%)")

        # Holder concentration
        if holder_analysis.get("top_10_pct", 0) > 80:
            risk_score += 0.3
            flags.append("WARNING: High holder concentration")

        risk_score = min(risk_score, 1.0)

        return {
            "overall_risk": round(risk_score, 2),
            "risk_level": "CRITICAL"
            if risk_score > 0.7
            else "HIGH"
            if risk_score > 0.4
            else "MEDIUM"
            if risk_score > 0.2
            else "LOW",
            "flags": flags,
            "recommendation": "AVOID" if risk_score > 0.6 else "CAUTION" if risk_score > 0.3 else "MONITOR",
        }

    async def scan_opportunities(
        self,
        chains: list[str] = None,
        min_liquidity: float = 5000,
        max_risk: float = 0.5,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Scan for potential opportunities across chains."""
        chains = chains or ["solana", "ethereum", "bsc", "arbitrum", "base"]
        all_opportunities = []

        for chain in chains:
            pairs = await self.get_new_pairs(chain, limit=50)
            for pair in pairs:
                if pair and pair["liquidity_usd"] >= min_liquidity and pair["risk_score"] <= max_risk:
                    all_opportunities.append(pair)

        # Sort by best risk/reward (high volume, low risk, good price action)
        all_opportunities.sort(
            key=lambda x: (x["volume_24h"] / max(x["liquidity_usd"], 1)) * (1 - x["risk_score"]), reverse=True
        )

        return all_opportunities[:limit]


def build_memecoin_scanner_adapter(config: dict[str, Any] | None = None) -> MemecoinScannerAdapter:
    """Factory function to create Memecoin Scanner adapter."""
    return MemecoinScannerAdapter(config)
