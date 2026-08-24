"""Tests for cores/work_policy.py — category business-priority layer."""

from __future__ import annotations

from cores.direct_work_engine.models import OpportunityCategory
from cores.work_policy import (
    CategoryPriority,
    PolicySource,
    policy_for,
    priority_for,
)


class TestPolicyTotality:
    def test_every_canonical_category_has_a_profile(self) -> None:
        for member in OpportunityCategory:
            profile = policy_for(member)
            assert profile.category is member

    def test_profiles_do_not_mutate_taxonomy(self) -> None:
        # identity and policy stay separate: consuming policy never changes the Enum
        assert len(OpportunityCategory) == 38


class TestEvidenceRules:
    def test_owner_priority_list_is_high(self) -> None:
        for value in ("data_annotation", "prompt_engineering", "dev_bounty", "code_review"):
            profile = policy_for(OpportunityCategory(value))
            assert profile.priority is CategoryPriority.HIGH
            assert profile.source is PolicySource.OWNER_PRIORITY_LIST

    def test_mercenary_extreme_inherits_high(self) -> None:
        # DEVELOPMENT_TASKS=EXTREME -> software_engineering
        profile = policy_for(OpportunityCategory.SOFTWARE_ENGINEERING)
        assert profile.priority is CategoryPriority.HIGH
        assert profile.source is PolicySource.MERCENARY_CURATED

    def test_mercenary_medium_inherits_medium(self) -> None:
        # FUNDED_OPEN_SOURCE=MEDIUM -> oss_bounties
        profile = policy_for(OpportunityCategory.OSS_BOUNTIES)
        assert profile.priority is CategoryPriority.MEDIUM
        assert profile.source is PolicySource.MERCENARY_CURATED

    def test_no_evidence_defaults_low_with_explicit_rationale(self) -> None:
        profile = policy_for(OpportunityCategory.EMBEDDED)
        assert profile.priority is CategoryPriority.LOW
        assert profile.source is PolicySource.DEFAULT_NO_EVIDENCE
        assert "evidence" in profile.rationale.lower()


class TestDeterminism:
    def test_policy_for_is_deterministic(self) -> None:
        member = OpportunityCategory.WEB_SCRAPING
        assert policy_for(member) == policy_for(member)

    def test_priority_convenience_matches_profile(self) -> None:
        assert priority_for(OpportunityCategory.BUG_BOUNTY) is CategoryPriority.HIGH
