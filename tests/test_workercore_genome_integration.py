import asyncio

from cores.opportunity_genome.repository import InMemoryOpportunityGenomeRepository
from cores.worker_core.models import WorkGoal
from cores.worker_core.orchestrator import WorkerCore


class DummyOpp:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeDiscovery:
    async def discover_all(self, categories=None, platforms=None):
        # return one opportunity with expected_value_usd_per_hour attribute
        return [
            DummyOpp(
                id="opp-1",
                title="Test Opp",
                description="d",
                platform="hackerone",
                category="bug_bounty",
                reward=100.0,
                expected_value_usd_per_hour=25.0,
                estimated_hours=4.0,
            )
        ]


def test_workercore_discovers_and_persists_genome():
    core = WorkerCore()
    core.set_discovery_engine(FakeDiscovery())
    repo = InMemoryOpportunityGenomeRepository()
    core.set_genome_repository(repo)

    # set an active goal
    goal = WorkGoal()
    goal.active = True
    core.set_goal(goal)

    # run the async discover method
    res = asyncio.run(core._discover_work())
    assert res is not None
    # ensure genome persisted in repo
    # genome should be attached as attribute on work item
    assert hasattr(res, "genome_id")
    g = repo.get_by_id(res.genome_id)
    assert g is not None
    assert g.title == res.title
