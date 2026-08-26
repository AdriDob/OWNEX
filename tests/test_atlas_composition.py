"""Tests for the Atlas portfolio composition root + financial dashboard Atlas leg.

Regression guards:
- PortfolioEngine must expose aggregate() (the phantom get_portfolio() bug made
  the Atlas leg of patrimonio_total silently $0 — see DECISIONS 2026-08-26).
- Routers and dashboard must use a configured engine (connectors registered).
"""

from __future__ import annotations

import asyncio
from typing import Any

from apps.atlas.connectors import create_connector, get_connector_ids
from apps.atlas.engines.portfolio import PortfolioEngine, get_configured_engine
from core.normalizer.base import NormalizedPortfolio


class _FakeConnector:
    connector_id = "fake"

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        return NormalizedPortfolio(total_value=125.5, positions=[], provider="fake")

    async def get_transactions(self, since_days: int = 30) -> list[Any]:
        return []

    async def get_quote(self, symbol: str) -> None:
        return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []


class _FailingConnector:
    connector_id = "failing"

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        raise RuntimeError("network down")

    async def get_transactions(self, since_days: int = 30) -> list[Any]:
        return []

    async def get_quote(self, symbol: str) -> None:
        return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []


class TestCompositionRoot:
    def test_engine_has_aggregate_not_get_portfolio(self) -> None:
        engine = PortfolioEngine()
        assert hasattr(engine, "aggregate")
        assert not hasattr(engine, "get_portfolio")

    def test_configured_engine_registers_all_connectors(self) -> None:
        engine = get_configured_engine()
        assert len(engine._connectors) >= len(get_connector_ids()) > 0

    def test_singleton_returns_same_instance(self) -> None:
        assert get_configured_engine() is get_configured_engine()

    def test_registry_can_instantiate_every_id(self) -> None:
        for cid in get_connector_ids():
            assert create_connector(cid) is not None, f"connector {cid} failed to instantiate"


class TestAggregate:
    def test_aggregates_fake_connector_value(self) -> None:
        engine = PortfolioEngine()
        engine.register_connector(_FakeConnector())
        portfolio = asyncio.run(engine.aggregate())
        assert round(portfolio.total_value, 2) == 125.5

    def test_failing_connector_does_not_break_aggregate(self) -> None:
        engine = PortfolioEngine()
        engine.register_connector(_FailingConnector())
        engine.register_connector(_FakeConnector())
        portfolio = asyncio.run(engine.aggregate())
        assert round(portfolio.total_value, 2) == 125.5

    def test_empty_engine_returns_zero_portfolio(self) -> None:
        portfolio = asyncio.run(PortfolioEngine().aggregate())
        assert portfolio.total_value == 0.0
        assert portfolio.positions == []


class TestDashboardAtlasLeg:
    def test_atlas_total_is_float_and_never_raises(self) -> None:
        from cores.financial.dashboard import _get_atlas_total

        value = _get_atlas_total()
        assert isinstance(value, float)
        assert value >= 0.0

    def test_routers_importable(self) -> None:
        from apps.atlas.api.routers import router  # noqa: F401
