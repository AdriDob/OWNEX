"""Memecoin adapter — real-API mapping with fixtures (no network)."""

from __future__ import annotations

import pytest

from cores.investment.adapters.memecoin_adapter import MemecoinAdapter

MINT_A = "MintA111111111111111111111111111111111111111"
MINT_B = "MintB111111111111111111111111111111111111111"


class FakeResp:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeAsyncClient:
    """Minimal httpx.AsyncClient double routing by URL."""

    routes: dict = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None, **kwargs):
        for prefix, resp in type(self).routes.items():
            if url.startswith(prefix):
                return resp
        return FakeResp(404, {})

    async def post(self, url, **kwargs):
        return FakeResp(404, {})


@pytest.fixture()
def fake_http(monkeypatch):
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.routes = {}
    return FakeAsyncClient


def profiles_payload():
    return [
        {"chainId": "solana", "tokenAddress": MINT_A},
        {"chainId": "solana", "tokenAddress": MINT_B},
        {"chainId": "ethereum", "tokenAddress": "0xabc"},
        {"chainId": "solana", "tokenAddress": None},
    ]


def tokens_payload():
    return [
        {
            "baseToken": {"address": MINT_A, "symbol": "AAA", "name": "Aaa"},
            "liquidity": {"usd": 25000},
            "marketCap": 90000,
            "fdv": 100000,
            "volume": {"h24": 50000},
            "priceUsd": "0.0001",
            "priceChange": {"h24": 12.5},
            "pairCreatedAt": 1757000000000,
            "dexId": "raydium",
            "boosts": {"active": 2},
            "url": "https://dexscreener.com/solana/xxx",
        },
        {
            "baseToken": {"address": MINT_B, "symbol": "BBB", "name": "Bbb"},
            "liquidity": {"usd": 100},  # below default floor
            "marketCap": 1000,
            "volume": {"h24": 10},
            "priceUsd": "0.000001",
            "dexId": "pumpfun",
            "url": "",
        },
        "garbage-entry",
    ]


class TestScan:
    async def test_parses_and_filters_liquidity(self, fake_http):
        fake_http.routes = {
            "https://api.dexscreener.com/token-profiles": FakeResp(200, profiles_payload()),
            "https://api.dexscreener.com/tokens/v1/solana/": FakeResp(200, tokens_payload()),
        }
        adapter = MemecoinAdapter()
        tokens = await adapter.scan_new_tokens()
        assert len(tokens) == 1
        t = tokens[0]
        assert t["mint"] == MINT_A
        assert t["symbol"] == "AAA"
        assert t["liquidity_usd"] == 25000
        assert t["boosts_active"] == 2
        assert t["dex"] == "raydium"

    async def test_http_error_returns_empty(self, fake_http):
        fake_http.routes = {
            "https://api.dexscreener.com/token-profiles": FakeResp(500, {}),
        }
        assert await MemecoinAdapter().scan_new_tokens() == []

    async def test_registry_entrypoint(self, fake_http):
        fake_http.routes = {
            "https://api.dexscreener.com/token-profiles": FakeResp(200, profiles_payload()),
            "https://api.dexscreener.com/tokens/v1/solana/": FakeResp(200, tokens_payload()),
        }
        tokens = await MemecoinAdapter().scan_opportunities(min_liquidity_usd=1000.0)
        assert len(tokens) == 1


class FakeQuote:
    out_amount = 123456
    price_impact_pct = 0.4
    slippage_bps = 500


class FakeJupiter:
    def __init__(self):
        self.quotes = []

    def quote(self, in_mint, out_mint, amount, slippage=500, **kwargs):
        self.quotes.append((in_mint, out_mint, amount, slippage))
        return FakeQuote()


class TestQuotesAndDryRun:
    async def test_quote_buy_delegates_to_jupiter(self):
        adapter = MemecoinAdapter()
        adapter._jupiter = FakeJupiter()
        q = await adapter.quote_buy(MINT_A, 0.5)
        assert q is not None
        assert q["out_amount"] == 123456
        assert q["in_sol"] == 0.5

    async def test_buy_dry_run_simulates_no_live(self):
        adapter = MemecoinAdapter()  # dry-run by default
        assert adapter.is_dry_run is True
        adapter._jupiter = FakeJupiter()
        res = await adapter.buy(MINT_A, 0.5)
        assert res["status"] == "simulated"
        assert res["dry_run"] is True
        assert "txid" not in res

    async def test_buy_no_route_fails(self):
        from typing import Any

        class NoRoute(FakeJupiter):
            def quote(self, *a, **k) -> Any:
                return None

        adapter = MemecoinAdapter()
        adapter._jupiter = NoRoute()
        res = await adapter.buy(MINT_A, 0.5)
        assert res["status"] == "failed"


class TestRugcheck:
    async def test_parses_report(self, fake_http):
        fake_http.routes = {
            "https://api.rugcheck.xyz/v1/tokens/": FakeResp(
                200,
                {
                    "holderCount": 120,
                    "top10HolderPercent": 35.5,
                    "liquidityLocked": True,
                    "mintDisabled": True,
                    "freezeDisabled": False,
                    "score": 42,
                    "risks": [{"name": "high ownership"}],
                },
            )
        }
        m = await MemecoinAdapter().get_token_metrics(MINT_A)
        assert m["holder_count"] == 120
        assert m["liquidity_locked"] is True
        assert m["score"] == 42

    async def test_missing_token_reports_error(self, fake_http):
        fake_http.routes = {}
        m = await MemecoinAdapter().get_token_metrics("unknown")
        assert "error" in m


class TestRegistry:
    async def test_default_registry_initializes_memecoin(self):
        from cores.investment.adapters.registry import build_default_registry

        reg = build_default_registry({})
        results = await reg.initialize_all()
        assert results.get("memecoin") is True
        assert reg.get_adapter("memecoin") is not None
        assert "memecoin_scanner" not in [a["name"] for a in reg.list_adapters()]
