import asyncio

from cores.worker_core.orchestrator import WorkerCore
from cores.worker_core.models import WorkGoal
from cores.worker_core.simple_evaluation import SimpleEvaluationEngine


class DummyOpp:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeDiscovery:
    async def discover_all(self, categories=None, platforms=None):
        return [
            DummyOpp(id="opp-2", title="Eval Opp", reward=200.0, expected_value_usd_per_hour=50.0, estimated_hours=2.0, platform="hackerone", category="bug_bounty")
        ]


def test_evaluate_and_select_moves_phase():
    core = WorkerCore()
    core.set_discovery_engine(FakeDiscovery())
    core.set_evaluation_engine(SimpleEvaluationEngine())

    goal = WorkGoal()
    goal.active = True
    # Lower target so the discovered opportunity passes EV/hr threshold in tests
    goal.target_monthly_usd = 2000.0
    core.set_goal(goal)

    work_item = asyncio.run(core._discover_work())
    assert work_item is not None

    res = asyncio.run(core._evaluate_work(work_item))
    assert res is True
    # evaluation should have added an evaluate checkpoint
    assert any(cp.get("phase") == "evaluate" for cp in work_item.checkpoints)
