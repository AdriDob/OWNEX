"""Tests for CoinGecko price feed."""

from __future__ import annotations

from cores.crypto.coingecko import COINGECKO_IDS, CoinGeckoFeed, get_coingecko_feed


class TestCoinGeckoIDs:
    def test_common_assets_have_ids(self):
        assert COINGECKO_IDS["BTC"] == "bitcoin"
        assert COINGECKO_IDS["ETH"] == "ethereum"
        assert COINGECKO_IDS["USDC"] == "usd-coin"
        assert COINGECKO_IDS["SOL"] == "solana"
        assert COINGECKO_IDS["TRX"] == "tron"

    def test_all_ids_are_strings(self):
        for symbol, cid in COINGECKO_IDS.items():
            assert isinstance(symbol, str)
            assert isinstance(cid, str)
            assert len(symbol) > 0


class TestCoinGeckoFeed:
    def test_health_returns_dict(self):
        feed = CoinGeckoFeed()
        health = feed.health()
        assert "available" in health
        assert "cached_symbols" in health

    def test_cache_ttl_default(self):
        feed = CoinGeckoFeed()
        assert feed._cache_ttl == 60

    def test_unknown_symbol_returns_zero(self):
        feed = CoinGeckoFeed()
        price = feed.get_price("NONEXISTENT_COIN_12345")
        assert price == 0.0

    def test_get_prices_returns_dict(self):
        feed = CoinGeckoFeed()
        prices = feed.get_prices(["BTC", "ETH"])
        assert isinstance(prices, dict)
        for symbol, price in prices.items():
            assert isinstance(symbol, str)
            assert isinstance(price, (int, float))

    def test_singleton(self):
        feed1 = get_coingecko_feed()
        feed2 = get_coingecko_feed()
        assert feed1 is feed2

    def test_get_24h_change_returns_none_for_unknown(self):
        feed = CoinGeckoFeed()
        change = feed.get_24h_change("NONEXISTENT")
        assert change is None
