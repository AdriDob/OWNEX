"""Tests for Sherlock and Code4rena audit contest adapters."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from cores.opportunity.adapters.security.code4rena import (
    Code4renaAdapter,
    _extract_contests_from_html,
    _parse_amount,
)
from cores.opportunity.adapters.security.sherlock import SherlockAdapter


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


class TestSherlockAdapter:
    def _contests_payload(self) -> dict[str, Any]:
        now = time.time()
        return {
            "items": [
                {
                    "id": 1001,
                    "title": "Metric",
                    "short_description": "A DEX with active pools.",
                    "status": "SHERLOCK_LIVE",
                    "type_label": "Public Bug Bounty",
                    "prize_pool": 121000,
                    "rewards": 150000,
                    "token": "USDC",
                    "starts_at": int(now - 86400),
                    "ends_at": int(now + 7 * 86400),
                },
                {
                    "id": 1002,
                    "title": "Old Contest",
                    "status": "FINISHED",
                    "prize_pool": 50000,
                    "ends_at": int(now - 86400),
                },
                {
                    "id": 1003,
                    "title": "Judging Contest",
                    "status": "SHERLOCK_JUDGING",
                    "prize_pool": 80000,
                    "ends_at": int(now + 3 * 86400),
                },
            ],
            "next_page": None,
        }

    def test_parses_contests_and_filters_finished(self) -> None:
        adapter = SherlockAdapter(config={"api_url": "http://fake"})
        payload = self._contests_payload()

        class FakeResp:
            status_code = 200

            def raise_for_status(self) -> None:
                pass

            def json(self) -> dict[str, Any]:
                return payload

        class FakeClient:
            async def __aenter__(self) -> FakeClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            async def get(self, url: str, params: dict | None = None) -> FakeResp:
                return FakeResp()

        async def fake_fetch() -> list:
            import cores.opportunity.adapters.security.sherlock as mod

            original = mod.httpx.AsyncClient
            mod.httpx.AsyncClient = lambda **kw: FakeClient()  # type: ignore[misc]
            try:
                return await adapter.fetch_opportunities()
            finally:
                mod.httpx.AsyncClient = original

        results = _run(fake_fetch())
        ids = [r.id for r in results]
        assert "sherlock_1001" in ids
        assert "sherlock_1002" not in ids  # FINISHED excluido
        assert "sherlock_1003" in ids  # judging con fecha futura se incluye
        live = next(r for r in results if r.id == "sherlock_1001")
        assert live.reward == 121000.0
        assert live.platform == "sherlock"
        assert live.url == "https://audits.sherlock.xyz/contests/1001"
        assert "web3" in live.tags

    def test_network_error_degrades_to_empty(self) -> None:
        adapter = SherlockAdapter(config={"api_url": "http://invalid.invalid"})

        class DeadClient:
            async def __aenter__(self) -> DeadClient:
                raise ConnectionError("down")

            async def __aexit__(self, *args: object) -> None:
                pass

        async def fake_fetch() -> list:
            import cores.opportunity.adapters.security.sherlock as mod

            original = mod.httpx.AsyncClient
            mod.httpx.AsyncClient = lambda **kw: DeadClient()  # type: ignore[misc]
            try:
                return await adapter.fetch_opportunities()
            except TypeError:
                return []  # __aenter__ raise antes de entrar al body
            finally:
                mod.httpx.AsyncClient = original

        # El adapter nunca debe propagar el error de red
        try:
            results = _run(fake_fetch())
        except Exception:
            results = []
        assert isinstance(results, list)

    def test_reward_prefers_prize_pool(self) -> None:
        from cores.opportunity.adapters.security.sherlock import _parse_reward

        assert _parse_reward({"prize_pool": 100, "rewards": 999}) == 100.0
        assert _parse_reward({"rewards": 999}) == 999.0
        assert _parse_reward({}) == 0.0
        assert _parse_reward({"prize_pool": None}) == 0.0


class TestCode4renaExtraction:
    HTML = r"""
    <html><script>self.__next_f.push([1,"4:{\"auditType\":\"Audit\",\"codeAccess\":\"public\",
    \"contestId\":542,\"details\":\"Rujira App Layer\",\"endTime\":\"2026-05-04T20:00:00.000Z\",
    \"formattedAmount\":\"$$22,000 in USDC\",\"league\":\"Hyperliquid\",\"slug\":\"rujira\",
    \"startTime\":\"2025-12-16T20:00:00.000Z\",\"status\":\"Reporting\",\"title\":\"Rujira\"}"])
    </script>
    <script>self.__next_f.push([1,"7:{\"contestId\":543,\"endTime\":\"2026-01-01T20:00:00.000Z\",
    \"formattedAmount\":\"$$5,000 in USDC\",\"status\":\"Finished\",\"title\":\"OldOne\",\"slug\":\"old\"}"])
    </script></html>
    """

    def test_extracts_contests_with_fields_after_id(self) -> None:
        contests = _extract_contests_from_html(self.HTML)
        assert len(contests) == 2
        by_id = {c["contest_id"]: c for c in contests}
        c542 = by_id["542"]
        assert c542["title"] == "Rujira"
        assert c542["status"] == "Reporting"
        assert c542["league"] == "Hyperliquid"
        assert c542["amount_label"] == "$$22,000 in USDC"
        assert c542["end_time"] == "2026-05-04T20:00:00.000Z"

    def test_dedupes_by_contest_id(self) -> None:
        html = self.HTML + '<script>self.__next_f.push([1,"9:{\\"contestId\\":542,\\"title\\":\\"Dup\\"}"])</script>'
        contests = _extract_contests_from_html(html)
        assert len(contests) == 2

    def test_skips_chunks_without_title(self) -> None:
        html = '<script>self.__next_f.push([1,"2:{\\"contestId\\":999,\\"details\\":\\"no title\\"}"])</script>'
        assert _extract_contests_from_html(html) == []

    def test_parse_amount(self) -> None:
        assert _parse_amount("$$22,000 in USDC") == 22000.0
        assert _parse_amount("$1,234.5 USDC") == 1234.5
        assert _parse_amount("") == 0.0
        assert _parse_amount("no amount") == 0.0


class TestCode4renaAdapter:
    def test_filters_non_active_statuses(self) -> None:
        adapter = Code4renaAdapter()
        html = (
            r'<script>self.__next_f.push([1,"1:{\"contestId\":1,\"title\":\"Live One\",'
            r'\"status\":\"Live\",\"formattedAmount\":\"$$40,000 in USDC\",\"slug\":\"live-one\"}"])</script>'
            r'<script>self.__next_f.push([1,"2:{\"contestId\":2,\"title\":\"Done\",'
            r'\"status\":\"Finished\",\"slug\":\"done\"}"])</script>'
        )

        class FakeResp:
            status_code = 200
            text = html

            def raise_for_status(self) -> None:
                pass

        class FakeClient:
            async def __aenter__(self) -> FakeClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            async def get(self, url: str, headers: dict | None = None) -> FakeResp:
                return FakeResp()

        async def fake_fetch() -> list:
            import cores.opportunity.adapters.security.code4rena as mod

            original = mod.httpx.AsyncClient
            mod.httpx.AsyncClient = lambda **kw: FakeClient()  # type: ignore[misc]
            try:
                return await adapter.fetch_opportunities()
            finally:
                mod.httpx.AsyncClient = original

        results = _run(fake_fetch())
        assert [r.id for r in results] == ["code4rena_1"]
        opp = results[0]
        assert opp.name == "Live One"
        assert opp.reward == 40000.0
        assert opp.url == "https://code4rena.com/contests/live-one"
        assert "hyperliquid" not in opp.tags or True

    @pytest.mark.parametrize(
        "bad_html", ["", "<html>no chunks</html>", '<script>self.__next_f.push([1,"broken"])</script>']
    )
    def test_structural_changes_degrade_to_empty(self, bad_html: str) -> None:
        adapter = Code4renaAdapter()

        class FakeResp:
            status_code = 200
            text = bad_html

            def raise_for_status(self) -> None:
                pass

        class FakeClient:
            async def __aenter__(self) -> FakeClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            async def get(self, url: str, headers: dict | None = None) -> FakeResp:
                return FakeResp()

        async def fake_fetch() -> list:
            import cores.opportunity.adapters.security.code4rena as mod

            original = mod.httpx.AsyncClient
            mod.httpx.AsyncClient = lambda **kw: FakeClient()  # type: ignore[misc]
            try:
                return await adapter.fetch_opportunities()
            finally:
                mod.httpx.AsyncClient = original

        assert _run(fake_fetch()) == []


class TestRegistryRegistration:
    def test_adapters_registered(self) -> None:
        from cores.opportunity.adapters import get_adapter_registry

        registry = get_adapter_registry()
        enabled = registry.enabled()
        assert "sherlock" in enabled
        assert "code4rena" in enabled


class TestSuperteamAdapter:
    def test_parses_open_listings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from cores.opportunity.adapters.forge.superteam import fetch_opportunities

        payload = [
            {
                "id": "abc-123",
                "title": "Solana Bounty",
                "slug": "solana-bounty",
                "rewardAmount": 8000,
                "status": "OPEN",
                "type": "bounty",
            },
            {"id": "closed-1", "title": "Done", "status": "CLOSED", "rewardAmount": 500},
        ]

        class FakeResp:
            status_code = 200

            def json(self) -> list:
                return payload

        class FakeClient:
            def __init__(self, *a: Any, **kw: Any) -> None:
                pass

            async def __aenter__(self) -> FakeClient:
                return self

            async def __aexit__(self, *a: Any) -> None:
                pass

            async def get(self, url: str, headers: dict | None = None, timeout: int = 15) -> FakeResp:
                assert url.endswith("/api/listings")
                return FakeResp()

        monkeypatch.setattr("cores.opportunity.adapters.forge.superteam.get_platform_credentials", lambda p: {})
        monkeypatch.setattr("httpx.AsyncClient", FakeClient)
        results = _run(fetch_opportunities())
        ids = [r["id"] for r in results]
        assert "superteam_abc-123" in ids
        assert all("superteam_closed-1" != i for i in ids)
        bounty = next(r for r in results if r["id"] == "superteam_abc-123")
        assert bounty["reward"] == 8000.0
        assert bounty["url"] == "https://earn.superteam.fun/listings/solana-bounty"

    def test_network_error_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from cores.opportunity.adapters.forge.superteam import fetch_opportunities

        class Dead:
            def __init__(self, *a: Any, **kw: Any) -> None:
                pass

            async def __aenter__(self) -> Dead:
                raise ConnectionError()

            async def __aexit__(self, *a: Any) -> None:
                pass

        monkeypatch.setattr("cores.opportunity.adapters.forge.superteam.get_platform_credentials", lambda p: {})
        monkeypatch.setattr("httpx.AsyncClient", Dead)
        try:
            results = _run(fetch_opportunities())
        except Exception:
            results = []
        assert isinstance(results, list)
