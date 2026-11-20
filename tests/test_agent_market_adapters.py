"""Contratos de los adapters de mercados agent-native (Taskmarket, Agent Hansa).

Regresión del bug potencial: adapters que devuelven ``[]`` en silencio o
inventan rewards. Deben:
  1. pegarle a los endpoints públicos verificados
  2. filtrar por status abierto real (no expired/completed)
  3. convertir rewards honestamente (Taskmarket: base units → USD, raw en metadata)
  4. marcar registration_blocked_on_user (claim/submit requiere autorización humana)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


TASKMARKET_PAYLOAD = {
    "tasks": [
        {
            "id": "0xabc",
            "referenceCode": "TSK-TEST1",
            "description": "Design 5 brand identities\nDetails here",
            "reward": "100000",
            "chainId": 8453,
            "createdAt": "2026-11-20T18:39:03Z",
            "expiryTime": "2026-11-27T18:39:02Z",
            "status": "open",
            "tags": ["branding"],
            "mode": "bounty",
            "submissionCount": 3,
        },
        {
            "id": "0xdef",
            "referenceCode": "TSK-TEST2",
            "description": "Completed task",
            "reward": "500000",
            "status": "completed",
            "tags": [],
        },
        {
            "id": "0xghi",
            "referenceCode": "TSK-TEST3",
            "description": "Task with bad reward",
            "reward": "not-a-number",
            "status": "open",
            "tags": [],
        },
    ]
}

HANSA_PAYLOAD = [
    {
        "id": "t1",
        "title": "Open quest",
        "description": "Do the thing",
        "goal": "Goal text",
        "reward_amount": 50.0,
        "currency": "USD",
        "status": "open",
        "category": "dev",
        "tags": ["code"],
        "participant_count": 4,
    },
    {
        "id": "t2",
        "title": "Expired quest",
        "description": "Old",
        "reward_amount": 100.0,
        "status": "expired",
        "tags": [],
    },
    {
        "id": "t3",
        "title": "In progress quest",
        "description": "Live",
        "reward_amount": 25.0,
        "status": "in_progress",
        "category": "marketing",
        "tags": [],
    },
]


def _fake_httpx(monkeypatch: pytest.MonkeyPatch, payload: Any, seen: list[str]) -> None:
    class FakeResp:
        status_code = 200

        def json(self) -> Any:
            return payload

    class FakeClient:
        def __init__(self, *a: Any, **kw: Any) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *a: Any) -> None:
            pass

        async def get(self, url: str, timeout: int = 15, **kw: Any) -> FakeResp:
            seen.append(url)
            return FakeResp()

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)


def test_taskmarket_filters_open_and_converts_reward(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.opportunity.adapters.agent_markets import TaskmarketAdapter

    seen: list[str] = []
    _fake_httpx(monkeypatch, TASKMARKET_PAYLOAD, seen)

    opps = _run(TaskmarketAdapter({}).fetch_opportunities())

    assert seen == ["https://api.taskmarket.dev/api/tasks"]
    assert len(opps) == 2  # completed filtrado
    assert opps[0].id == "taskmarket_TSK-TEST1"
    assert opps[0].reward == pytest.approx(0.1)  # 100000 base units / 1e6
    assert opps[0].metadata["reward_raw"] == "100000"
    assert opps[0].metadata["chain_id"] == 8453
    assert opps[0].metadata["registration_blocked_on_user"] is True
    # reward no parseable → 0.0, nunca inventado
    assert opps[1].reward == 0.0


def test_agenthansa_filters_non_open(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.opportunity.adapters.agent_markets import AgentHansaAdapter

    seen: list[str] = []
    _fake_httpx(monkeypatch, HANSA_PAYLOAD, seen)

    opps = _run(AgentHansaAdapter({}).fetch_opportunities())

    assert seen == ["https://www.agenthansa.com/api/community/tasks"]
    assert len(opps) == 2  # expired filtrado, in_progress incluido
    assert {o.id for o in opps} == {"agenthansa_t1", "agenthansa_t3"}
    assert opps[0].reward == 50.0
    assert opps[0].metadata["registration_blocked_on_user"] is True


AGENTICS_PAYLOAD = {
    "fetchedAt": "2026-11-20T19:16:09Z",
    "total": 266,
    "count": 3,
    "sources": [{"id": "taskmarket"}],
    "jobs": [
        {
            "id": "tm-abc",
            "title": "Build a CLI tool",
            "description": "Do the thing",
            "amount": "25",
            "currency": "USDC",
            "payModel": "bounty",
            "payRail": "base",
            "source": "taskmarket",
            "sourceName": "TaskMarket",
            "url": "https://taskmarket.dev",
            "postedAt": "2026-11-19T00:00:00Z",
        },
        {
            "id": "rb-def",
            "title": "Credits-only gig",
            "description": "Internal credits",
            "amount": "500",
            "currency": "Credits",
            "payModel": "credits",
            "source": "openwork",
            "sourceName": "OpenWork",
            "url": "https://openwork.example",
        },
        {
            "id": "x-ghi",
            "title": "EUR bounty",
            "description": "Euro",
            "amount": "notanum",
            "currency": "EUR",
            "source": "cantina",
            "url": "https://cantina.example",
        },
    ],
}


def test_agentics_aggregates_and_converts_usd_stables(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.opportunity.adapters.agent_markets import AgenticsAdapter

    seen: list[str] = []
    _fake_httpx(monkeypatch, AGENTICS_PAYLOAD, seen)

    opps = _run(AgenticsAdapter({}).fetch_opportunities())

    assert seen == ["https://agentics.page/api/jobs"]
    assert len(opps) == 3
    # USDC → USD-equivalent reward
    assert opps[0].reward == 25.0
    assert opps[0].source_name == "TaskMarket"
    assert opps[0].metadata["origin_source"] == "taskmarket"
    assert opps[0].metadata["pay_rail"] == "base"
    # Credits → reward 0.0, currency preserved (never invent conversion)
    assert opps[1].reward == 0.0
    assert opps[1].metadata["currency"] == "CREDITS"
    # EUR + unparseable amount → 0.0
    assert opps[2].reward == 0.0
    assert all(o.metadata["registration_blocked_on_user"] for o in opps)


def test_adapters_registered_in_core_registry() -> None:
    from core.opportunity.adapters import get_adapter_registry

    registry = get_adapter_registry()
    assert "taskmarket" in registry.all()
    assert "agent_hansa" in registry.all()
    assert "agentics" in registry.all()


def test_fetch_failure_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.opportunity.adapters.agent_markets import TaskmarketAdapter

    class FailingClient:
        def __init__(self, *a: Any, **kw: Any) -> None:
            pass

        async def __aenter__(self) -> FailingClient:
            return self

        async def __aexit__(self, *a: Any) -> None:
            pass

        async def get(self, *a: Any, **kw: Any) -> Any:
            raise RuntimeError("network down")

    monkeypatch.setattr("httpx.AsyncClient", FailingClient)
    assert _run(TaskmarketAdapter({}).fetch_opportunities()) == []
