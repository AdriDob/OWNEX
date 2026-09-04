from datetime import datetime, timedelta, timezone

from cores.opportunity_genome import mapper as gmapper
from cores.opportunity_genome.models import GenomeSource


class Dummy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_map_dwe_opportunity_to_genome_minimal():
    dwe = Dummy(id="dwe-1", title="Do a thing", payment=123.45, currency="USD", expected_value=12.3, acceptance_probability=0.2, technology_tags=["python", "api"], platform="hackerone")
    genome = gmapper.map_dwe_opportunity_to_genome(dwe)

    assert genome.id == "dwe-1"
    assert genome.reward == 123.45
    assert genome.expected_value == 12.3
    assert "python" in genome.technology_tags
    assert genome.source == GenomeSource.DIRECT_WORK


def test_map_legacy_opportunity_to_genome_with_score():
    score = Dummy(overall=0.8, expected_value=50.0, acceptance_probability=0.4)
    legacy = Dummy(id="legacy-1", name="Old Opp", public_url="https://x", score=score, confidence=0.7)
    genome = gmapper.map_legacy_opportunity_to_genome(legacy)

    assert genome.source == GenomeSource.LEGACY_INTEL
    assert genome.external_id == "legacy-1"
    assert genome.expected_value == 50.0
    assert genome.acceptance_probability == 0.4


def test_map_finding_to_genome_and_time_to_payout():
    now = datetime.now(timezone.utc)
    finding = Dummy(id=77, title="XSS", description="desc", vulnerability_type="xss", created_at=now - timedelta(days=3), severity="high", status="open")
    report = Dummy(id=11, confirmed_reward=500.0, currency="USD", created_at=now)
    target = Dummy(id=5, name="Example Target", domain="example.com")

    genome = gmapper.map_finding_to_genome(finding, target=target, report=report)

    assert genome.source == GenomeSource.DATABASE
    assert genome.reward == 500.0
    assert genome.metadata.get("db_finding_id") == 77
    assert genome.metadata.get("db_target_id") == 5
    assert genome.time_to_payout_days == 3.0


def test_map_work_item_to_genome_fallback_and_opportunity():
    # case: work_item has attached opportunity
    dwe = Dummy(id="dwe-2", title="Task", payment=10.0, currency="USD", expected_value=1.0)
    work_item = Dummy(id="w1", opportunity=dwe)
    genome = gmapper.map_work_item_to_genome(work_item)
    assert genome.external_id == "dwe-2" or genome.id == "dwe-2"

    # case: work_item without opportunity
    wi2 = Dummy(id="w2", title="Solo work", platform="opire", reward=5.0, category="dev_bounty")
    g2 = gmapper.map_work_item_to_genome(wi2)
    assert g2.metadata.get("work_item_id") == "w2"
