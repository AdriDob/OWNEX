"""FASE 2 remediation — OpportunityOrchestrator.execute_cycle integrity.

Historical regression: ``_process_opportunity`` was lost during the
core-tree restore churn (v5.0.0 implementation existed at commit 46ca139b),
leaving the scheduler-registered handler crashing with AttributeError as
soon as discovery produced candidates.

Contract after D1 remediation (Option B): the cycle runs the live stages
(discover → prioritize) and returns an honest RANKING — autonomous claim/
resolve/deliver stays disabled until executors are credentialed. Output
items are recommendations marked ``action_required="human_review"``;
they must never pretend execution happened.
"""

from __future__ import annotations

from typing import Any

import pytest

from core.opportunity.engine import OpportunityOrchestrator


class _FakeAdapter:
    def __init__(self, platform: str, items: list[dict[str, Any]]) -> None:
        self.platform = platform
        self._items = items

    async def fetch_opportunities(self) -> list[dict[str, Any]]:
        return self._items


def _orchestrator_class(monkeypatch: pytest.MonkeyPatch, raw_items: list[dict[str, Any]]):
    """Patch __init__ so the PUBLIC classmethod path (scheduler handler) runs
    against deterministic adapters instead of live-network ones."""
    from core.opportunity.engine import OpportunityOrchestrator

    async def _fake_prioritize(opps: list[dict[str, Any]], cycle: str) -> list[dict[str, Any]]:
        return sorted(
            ({**o, "priority_score": o.get("priority_score", 0.0)} for o in opps),
            key=lambda o: -float(o["priority_score"]),
        )

    monkeypatch.setattr("core.opportunity.tasks.prioritize_targets", _fake_prioritize)

    original_init = OpportunityOrchestrator.__init__

    def _patched_init(self):  # type: ignore[no-untyped-def]
        original_init(self)
        self.forge_adapters = [_FakeAdapter("opire", raw_items)]
        self.pulse_adapters = []

    monkeypatch.setattr(OpportunityOrchestrator, "__init__", _patched_init)
    return OpportunityOrchestrator


class TestExecuteCycleIntegrity:
    @pytest.mark.asyncio
    async def test_cycle_completes_without_attribute_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The scheduler handler must not crash when discovery yields candidates."""
        _orchestrator_class(
            monkeypatch,
            [
                {"platform": "opire", "reward": 500, "title": "Fix bug", "priority_score": 0.9},
                {"platform": "algora", "reward": 200, "title": "Add feature", "priority_score": 0.7},
            ],
        )
        results = await OpportunityOrchestrator.execute_cycle(cycle="forge", limit=10)
        assert isinstance(results, list)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_output_is_honest_ranking_not_fake_execution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _orchestrator_class(
            monkeypatch,
            [{"platform": "opire", "reward": 2000, "title": "Task", "priority_score": 0.95}],
        )
        results = await OpportunityOrchestrator.execute_cycle(cycle="forge", limit=5)
        top = results[0]
        assert top["action_required"] == "human_review"
        assert top["rank"] == 1
        assert "claimed" not in top and "submitted" not in top
        assert "execution_disabled_reason" in top

    @pytest.mark.asyncio
    async def test_respects_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _orchestrator_class(
            monkeypatch,
            [{"platform": f"p{i}", "reward": 100 * i, "title": f"T{i}", "priority_score": i / 10} for i in range(8)],
        )
        results = await OpportunityOrchestrator.execute_cycle(cycle="forge", limit=3)
        assert len(results) == 3
        assert [r["rank"] for r in results] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_empty_discovery_returns_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _orchestrator_class(monkeypatch, [])
        results = await OpportunityOrchestrator.execute_cycle(cycle="forge", limit=10)
        assert results == []
