"""Vault Adapter — Wealth/Finance platforms (CoinGecko, Firefly, Binance, DeFi Llama)."""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class VaultBaseAdapter(OpportunityAdapter):
    """Base adapter for Wealth/Finance platforms."""

    platform: str = "vault"
    cycle: str = "vault"


class CoinGeckoAdapter(VaultBaseAdapter):
    """CoinGecko adapter — crypto market data, trending coins, arbitrage signals."""

    platform: str = "coingecko"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("coingecko", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("coingecko", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch trending coins, arbitrage signals, staking yields."""
        try:
            headers = get_auth_headers("coingecko", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.coingecko.com/api/v3/search/trending",
                    headers=headers,
                    timeout=10,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                coins = data.get("coins", [])

                coin_ids = [c["item"]["id"] for c in coins[:10]]
                market_resp = await client.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "ids": ",".join(coin_ids),
                        "order": "market_cap_desc",
                        "sparkline": "false",
                        "price_change_percentage": "24h,7d",
                    },
                    timeout=15,
                )
                if market_resp.status_code != 200:
                    return []

                market_data = market_resp.json()

                raw_opps: list[RawOpportunity] = []
                for coin in market_data:
                    price_change_24h = coin.get("price_change_percentage_24h", 0)
                    price_change_7d = coin.get("price_change_percentage_7d", 0)

                    is_opportunity = (
                        price_change_24h > 5 and price_change_7d < 20 and coin.get("market_cap", 0) > 10_000_000
                    )

                    if is_opportunity:
                        raw_opps.append(
                            RawOpportunity(
                                id=f"coingecko_{coin['id']}",
                                name=f"{coin['symbol'].upper()}/USD — {coin['name']}",
                                description=f"24h: {price_change_24h:+.1f}% | 7d: {price_change_7d:+.1f}% | MCap: ${coin['market_cap']:,.0f}",
                                platform="coingecko",
                                url=f"https://www.coingecko.com/en/coins/{coin['id']}",
                                reward=float(coin.get("current_price", 0)),
                                effort_hours=0.5,
                                tags=["crypto", "trading", "momentum", coin.get("symbol", "").upper()],
                                cycle="vault",
                                source_type="market_signal",
                                source_name="coingecko",
                                metadata={
                                    "price": coin.get("current_price"),
                                    "change_24h": price_change_24h,
                                    "change_7d": price_change_7d,
                                    "market_cap": coin.get("market_cap"),
                                    "volume_24h": coin.get("total_volume"),
                                },
                                created_at="",
                            )
                        )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("CoinGeckoAdapter fetch failed: %s", e)
            return []


class FireflyAdapter(VaultBaseAdapter):
    """Firefly III adapter — personal finance, budget tracking, investment tracking."""

    platform: str = "firefly"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("firefly", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch financial insights from Firefly III."""
        try:
            headers = get_auth_headers("firefly", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.config.get('base_url', 'https://firefly.example.com')}/api/v1/accounts?type=asset",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                accounts = data.get("data", [])

                raw_opps: list[RawOpportunity] = []
                for account in accounts:
                    attrs = account.get("attributes", {})
                    balance = float(attrs.get("current_balance", 0))
                    currency = attrs.get("currency_code", "USD")

                    if balance > 1000:
                        raw_opps.append(
                            RawOpportunity(
                                id=f"firefly_{account.get('id')}",
                                name=f"Reallocate {attrs.get('name', 'Account')}",
                                description=f"Balance: {balance:,.2f} {currency} — Consider rebalancing",
                                platform="firefly",
                                url=f"{self.config.get('base_url', 'https://firefly.example.com')}/accounts/{account.get('id')}",
                                reward=0.0,
                                effort_hours=0.5,
                                tags=["finance", "rebalance", currency.lower()],
                                cycle="vault",
                                source_type="portfolio",
                                source_name="firefly",
                                metadata={"balance": balance, "currency": currency},
                                created_at=attrs.get("created_at", ""),
                            )
                        )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("FireflyAdapter fetch failed: %s", e)
            return []


class BinanceAdapter(VaultBaseAdapter):
    """Binance adapter — spot/futures trading signals, staking yields."""

    platform: str = "binance"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("binance", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("binance", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch staking yields and trading signals from Binance."""
        try:
            headers = get_auth_headers("binance", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.binance.com/sapi/v1/staking/productList",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                products = resp.json().get("data", [])

                raw_opps: list[RawOpportunity] = []
                for product in products[:20]:
                    apy = float(product.get("apy", 0))
                    if apy > 3.0:
                        raw_opps.append(
                            RawOpportunity(
                                id=f"binance_staking_{product.get('asset')}",
                                name=f"Stake {product.get('asset')} — {apy:.1f}% APY",
                                description=f"Locked staking: {product.get('duration', 0)} days | Min: {product.get('minPurchaseAmount', 0)} {product.get('asset')}",
                                platform="binance",
                                url=f"https://www.binance.com/en/staking/{product.get('asset', '').lower()}",
                                reward=apy,
                                effort_hours=0.2,
                                tags=["staking", "passive_income", product.get("asset", "").lower()],
                                cycle="vault",
                                source_type="staking",
                                source_name="binance",
                                metadata={
                                    "asset": product.get("asset"),
                                    "apy": apy,
                                    "duration": product.get("duration"),
                                    "min_amount": product.get("minPurchaseAmount"),
                                },
                                created_at="",
                            )
                        )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("BinanceAdapter fetch failed: %s", e)
            return []


class DefiLlamaAdapter(VaultBaseAdapter):
    """DeFi Llama adapter — DeFi protocol yields, TVL trends."""

    platform: str = "defillama"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("defillama", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch high-yield DeFi pools from DeFi Llama."""
        try:
            headers = get_auth_headers("defillama", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://yields.llama.fi/pools",
                    headers=headers,
                    timeout=20,
                )
                if resp.status_code != 200:
                    return []

                pools = resp.json().get("data", [])

                filtered = [p for p in pools if p.get("apy", 0) > 5.0 and p.get("tvlUsd", 0) > 1_000_000]

                raw_opps: list[RawOpportunity] = []
                for pool in sorted(filtered, key=lambda x: x.get("apy", 0), reverse=True)[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"defillama_{pool.get('pool', '').replace('/', '_')}",
                            name=f"{pool.get('project')} — {pool.get('symbol')} ({pool.get('apy', 0):.1f}% APY)",
                            description=f"TVL: ${pool.get('tvlUsd', 0):,.0f} | Chain: {pool.get('chain')}",
                            platform="defillama",
                            url=f"https://defillama.com/pool/{pool.get('pool', '')}",
                            reward=float(pool.get("apy", 0)),
                            effort_hours=0.5,
                            tags=["defi", "yield_farming", pool.get("chain", "").lower()],
                            cycle="vault",
                            source_type="defi_yield",
                            source_name="defillama",
                            metadata={
                                "apy": pool.get("apy"),
                                "tvl": pool.get("tvlUsd"),
                                "chain": pool.get("chain"),
                                "project": pool.get("project"),
                            },
                            created_at="",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("DeFiLlamaAdapter fetch failed: %s", e)
            return []
