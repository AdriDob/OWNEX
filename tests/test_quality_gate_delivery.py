import asyncio

from cores.worker_core.models import WorkGoal
from cores.worker_core.orchestrator import WorkerCore


class FakeDiscovery:
    async def discover_all(self, categories=None, platforms=None):
        class O:
            id = "opp-qg"
            title = "QG Opp"
            reward = 10.0
            expected_value_usd_per_hour = 2.0
            estimated_hours = 5.0
            platform = "hackerone"
            category = "bug_bounty"

        return [O]


class EvalPass:
    def evaluate(self, work_item, profile=None):
        return {"quality_gate_result": {"passed": True}}


class EvalFail:
    def evaluate(self, work_item, profile=None):
        return {"quality_gate_result": {"passed": False, "reason": "bad_quality"}}


def test_validate_blocks_delivery_when_quality_gate_fails():
    core = WorkerCore()
    core.set_discovery_engine(FakeDiscovery())
    core.set_evaluation_engine(EvalFail())

    goal = WorkGoal()
    goal.active = True
    goal.target_monthly_usd = 1000.0
    core.set_goal(goal)

    work_item = asyncio.run(core._discover_work())
    assert work_item is not None

    # Validation should fail
    ok = asyncio.run(core._validate_work(work_item))
    assert ok is False

    # Delivery should be blocked
    delivered = asyncio.run(core._deliver_work(work_item))
    assert delivered is False
    assert "Quality Gate" in (work_item.error or "") or "Blocked" in (work_item.error or "")


def test_validate_allows_delivery_when_quality_gate_passes():
    core = WorkerCore()
    core.set_discovery_engine(FakeDiscovery())
    core.set_evaluation_engine(EvalPass())

    # Disable human approval to allow auto-deliver path
    core.config.human_approval_required = False

    goal = WorkGoal()
    goal.active = True
    goal.target_monthly_usd = 1000.0
    core.set_goal(goal)

    work_item = asyncio.run(core._discover_work())
    assert work_item is not None

    ok = asyncio.run(core._validate_work(work_item))
    assert ok is True

    delivered = asyncio.run(core._deliver_work(work_item))
    # Since no delivery engine, deliver() adds a basic delivered checkpoint and returns True
    assert delivered is True
