import os
import tempfile

from cores.opportunity_genome.models import OpportunityGenome
from cores.opportunity_genome.sql_repository import SQLiteOpportunityGenomeRepository


def _make_genome(id: str, external_id: str, title: str = "t", platform: str = "p", category: str = "dev_bounty") -> OpportunityGenome:
    return OpportunityGenome(
        id=id,
        external_id=external_id,
        platform=platform,
        title=title,
        category=category,
    )


def test_sqlite_repo_save_and_get(tmp_path):
    dbf = tmp_path / "genomes.db"
    repo = SQLiteOpportunityGenomeRepository(str(dbf))

    g = _make_genome("s1", "se1", title="SqlFirst")
    repo.save(g)

    got = repo.get_by_id("s1")
    assert got is not None
    assert got.title == "SqlFirst"

    got2 = repo.get_by_external_id("se1")
    assert got2 is not None
    assert got2.id == "s1"


def test_sqlite_repo_delete_and_list(tmp_path):
    dbf = tmp_path / "genomes2.db"
    repo = SQLiteOpportunityGenomeRepository(str(dbf))

    g1 = _make_genome("s2", "se2", title="A")
    g2 = _make_genome("s3", "se3", title="B")
    repo.save(g1)
    repo.save(g2)

    all_items = list(repo.list_all())
    assert len(all_items) == 2

    assert repo.delete("s2") is True
    assert repo.get_by_id("s2") is None
