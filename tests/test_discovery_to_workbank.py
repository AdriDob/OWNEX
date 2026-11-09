from __future__ import annotations

import pytest

import cores.direct_work_engine.workbank as workbank_module
from core.opportunity import discovery_to_workbank as bridge
from core.opportunity.source_discovery import SourceCandidate, SourceDiscoveryRegistry, SourceLifecycle
from cores.direct_work_engine.models import EmploymentType, OpportunityCategory, PaymentMethod, WorkPlatform
from cores.direct_work_engine.workbank import WorkBank, WorkItem


@pytest.fixture
def public_hosts(monkeypatch):
    monkeypatch.setattr("core.opportunity.source_discovery._validate_public_url", lambda url: url.rstrip("/"))


def _issue_candidate(*, reward: float | None = 100.0, currency: str | None = "USD", record_type: str = "opportunity") -> SourceCandidate:
    return SourceCandidate(
        id="candidate-1",
        name="Fix parser edge case",
        source_url="https://github.com/org/repo/issues/1",
        discovered_by="github_issue_search",
        record_type=record_type,
        profile={
            "capabilities": ["issue"],
            "evidence": [{"url": "https://github.com/org/repo/issues/1", "type": "github_issue"}],
            "reward_reported": reward,
            "reward_currency": currency,
            "reward_status": "REPORTED" if reward is not None else "UNKNOWN",
            "record_type": record_type,
        },
    )


def test_candidate_to_opportunity_reports_reward_without_claiming_verification():
    opp = bridge.candidate_to_opportunity(_issue_candidate(reward=75.0))

    assert opp.payment == 75.0
    assert opp.currency == "USD"
    assert opp.payment_proven is False
    assert opp.rate_source == "reported"
    assert opp.platform == WorkPlatform.GITHUB
    assert opp.category == OpportunityCategory.DEV_BOUNTY
    assert opp.payment_method == PaymentMethod.OTHER
    assert opp.employment_type == EmploymentType.BOUNTY
    assert "Evidence: https://github.com/org/repo/issues/1" in opp.description


def test_candidate_to_opportunity_keeps_unknown_reward_unknown():
    opp = bridge.candidate_to_opportunity(_issue_candidate(reward=None, currency=None))

    assert opp.payment == 0.0
    assert opp.currency == "USD"
    assert opp.payment_proven is False
    assert opp.rate_source == "unknown"


def test_candidate_to_opportunity_preserves_reported_currency():
    opp = bridge.candidate_to_opportunity(_issue_candidate(reward=100.0, currency="USDC"))

    assert opp.payment == 100.0
    assert opp.currency == "USDC"
    assert opp.payment_proven is False


def test_integrate_meta_discovery_separates_sources_and_skips_unpaid(tmp_path, public_hosts, monkeypatch):
    registry = SourceDiscoveryRegistry(tmp_path / "candidates.json")
    registry.add("Rewarded repo", "https://github.com/org/repo", "github_topic_search")
    paid = registry.add(
        "Paid issue",
        "https://github.com/org/repo/issues/1",
        "github_issue_search",
        record_type="opportunity",
        profile={"reward_reported": 100.0, "reward_currency": "USD", "reward_status": "REPORTED"},
    )
    registry.add(
        "Unknown reward issue",
        "https://github.com/org/repo/issues/2",
        "github_issue_search",
        record_type="opportunity",
        profile={"reward_reported": None, "reward_status": "UNKNOWN"},
    )
    decayed = registry.add(
        "Decayed issue",
        "https://github.com/org/repo/issues/3",
        "github_issue_search",
        record_type="opportunity",
        profile={"reward_reported": 50.0, "reward_currency": "USD", "reward_status": "REPORTED"},
    )
    decayed.lifecycle = SourceLifecycle.DECAY

    bank = WorkBank(tmp_path / "workbank.json")
    monkeypatch.setattr(bridge, "get_workbank", lambda: bank)

    result = bridge.integrate_meta_discovery_into_workbank(registry=registry)

    assert result["total_considered"] == 4
    assert result["opportunity_candidates_considered"] == 2
    assert result["source_candidates_skipped"] == 1
    assert result["skipped_no_reward"] == 1
    assert result["skipped_duplicates"] == 0
    assert result["will_add_to_bank"] == 1
    assert [opp.url for opp in result["new_opportunities"]] == [paid.source_url]


def test_integrate_meta_discovery_deduplicates_existing_workbank_item(tmp_path, public_hosts, monkeypatch):
    registry = SourceDiscoveryRegistry(tmp_path / "candidates.json")
    candidate = registry.add(
        "Paid issue",
        "https://github.com/org/repo/issues/1",
        "github_issue_search",
        record_type="opportunity",
        profile={"reward_reported": 100.0, "reward_currency": "USD", "reward_status": "REPORTED"},
    )
    opp = bridge.candidate_to_opportunity(candidate)
    bank = WorkBank(tmp_path / "workbank.json")
    bank._items[opp.id] = WorkItem(
        id=opp.id,
        title="Existing item",
        platform="github",
        category="dev_bounty",
        reward=100.0,
        barrier_score=80.0,
        employment_type="bounty",
    )
    monkeypatch.setattr(bridge, "get_workbank", lambda: bank)

    result = bridge.integrate_meta_discovery_into_workbank(registry=registry)

    assert result["will_add_to_bank"] == 0
    assert result["skipped_duplicates"] == 1
    assert result["existing_in_bank"] == 1


def test_run_daily_cycle_with_meta_discovery_integration_scores_and_runs_cycle(monkeypatch):
    opp = bridge.candidate_to_opportunity(_issue_candidate(reward=120.0))
    integration = {
        "new_opportunities": [opp],
        "skipped_duplicates": 0,
        "skipped_no_reward": 0,
        "source_candidates_skipped": 0,
        "total_considered": 1,
        "opportunity_candidates_considered": 1,
        "existing_in_bank": 0,
        "will_add_to_bank": 1,
    }
    seen: dict[str, object] = {}

    def fake_integrate(*, limit: int = 200):
        seen["limit"] = limit
        return integration

    def fake_cycle(*, target: int | None = None, opportunities: list | None = None):
        seen["target"] = target
        seen["opportunities"] = opportunities
        return {"status": "ok", "items_prepared": len(opportunities or [])}

    monkeypatch.setattr(bridge, "integrate_meta_discovery_into_workbank", fake_integrate)
    monkeypatch.setattr(workbank_module, "run_daily_cycle", fake_cycle)

    result = bridge.run_daily_cycle_with_meta_discovery_integration(target=5, limit=50)

    assert seen["limit"] == 50
    assert seen["target"] == 5
    scored = seen["opportunities"]
    assert isinstance(scored, list) and scored[0].zero_barrier_score is not None
    assert result["daily_cycle"] == {"status": "ok", "items_prepared": 1}
    assert result["will_add_to_bank"] == 1
