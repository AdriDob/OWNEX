from cores.opportunity_genome.models import OpportunityGenome
from cores.opportunity_genome.repository import InMemoryOpportunityGenomeRepository


def _make_genome(id: str, external_id: str, title: str = "t", platform: str = "p", category: str = "dev_bounty") -> OpportunityGenome:
    return OpportunityGenome(
        id=id,
        external_id=external_id,
        platform=platform,
        title=title,
        category=category,
    )


def test_save_and_get_by_id_and_external():
    repo = InMemoryOpportunityGenomeRepository()
    g = _make_genome("g1", "e1", title="First")
    repo.save(g)

    got = repo.get_by_id("g1")
    assert got is not None
    assert got.title == "First"

    got2 = repo.get_by_external_id("e1")
    assert got2 is not None
    assert got2.id == "g1"


def test_upsert_by_external_id_replaces_previous():
    repo = InMemoryOpportunityGenomeRepository()
    g1 = _make_genome("g1", "ext-A", title="Old")
    repo.save(g1)

    g2 = _make_genome("g2", "ext-A", title="New")
    repo.save(g2)

    # external lookup should return the latest saved object
    found = repo.get_by_external_id("ext-A")
    assert found is not None
    assert found.id == "g2"
    assert found.title == "New"

    # old id should no longer exist
    assert repo.get_by_id("g1") is None


def test_delete_cleans_external_mapping():
    repo = InMemoryOpportunityGenomeRepository()
    g = _make_genome("gdel", "ext-del", title="X")
    repo.save(g)
    assert repo.get_by_external_id("ext-del") is not None

    assert repo.delete("gdel") is True
    assert repo.get_by_external_id("ext-del") is None
