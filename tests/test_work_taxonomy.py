"""Regression tests: every engine taxonomy maps exhaustively onto the canonical set.

Guards the One Source of Truth contract declared in cores/work_taxonomy.py:
adding a member to any local OpportunityCategory enum without registering its
canonical equivalent must fail here.
"""

from __future__ import annotations

import pytest

from core.opportunity.mercenary_filter import (
    OpportunityCategory as MercenaryCategory,
)
from cores.direct_work_engine.models import OpportunityCategory
from cores.opportunity.engine import OpportunityCategory as EngineOpportunityCategory
from cores.opportunity.global_sources import OpportunityCategory as GlobalSourceCategory
from cores.work_taxonomy import (
    ENGINE_TO_CANONICAL,
    GLOBAL_SOURCE_TO_CANONICAL,
    MERCENARY_TO_CANONICAL,
    to_canonical,
)


class TestExhaustiveMappings:
    def test_engine_mapping_covers_every_member(self) -> None:
        missing = set(EngineOpportunityCategory) - set(ENGINE_TO_CANONICAL)
        assert not missing, f"Unmapped engine categories: {sorted(missing)}"

    def test_global_source_mapping_covers_every_member(self) -> None:
        missing = set(GlobalSourceCategory) - set(GLOBAL_SOURCE_TO_CANONICAL)
        assert not missing, f"Unmapped global-source categories: {sorted(missing)}"

    def test_mercenary_mapping_covers_every_member(self) -> None:
        missing = set(MercenaryCategory) - set(MERCENARY_TO_CANONICAL)
        assert not missing, f"Unmapped mercenary categories: {sorted(missing)}"

    def test_all_targets_are_canonical_members(self) -> None:
        for mapping in (ENGINE_TO_CANONICAL, GLOBAL_SOURCE_TO_CANONICAL, MERCENARY_TO_CANONICAL):
            for target in mapping.values():
                assert isinstance(target, OpportunityCategory)
                assert target in set(OpportunityCategory)

    def test_no_stale_mapping_keys(self) -> None:
        extra = set(ENGINE_TO_CANONICAL) - set(EngineOpportunityCategory)
        assert not extra, f"Mapping keys no longer in source enum: {sorted(extra)}"


class TestExactMatches:
    @pytest.mark.parametrize(
        "source,target",
        [
            (EngineOpportunityCategory.BUG_BOUNTY, OpportunityCategory.BUG_BOUNTY),
            (EngineOpportunityCategory.DEV_BOUNTY, OpportunityCategory.DEV_BOUNTY),
            (EngineOpportunityCategory.OPEN_SOURCE, OpportunityCategory.OPEN_SOURCE),
            (EngineOpportunityCategory.AI_EVALUATION, OpportunityCategory.AI_EVALUATION),
            (GlobalSourceCategory.bug_bounty, OpportunityCategory.BUG_BOUNTY),
            (MercenaryCategory.GAME_PROGRAMMING, OpportunityCategory.GAME_DEVELOPMENT),
            (MercenaryCategory.HACKATHONS, OpportunityCategory.COMPETITIONS),
            (MercenaryCategory.FUNDED_OPEN_SOURCE, OpportunityCategory.OSS_BOUNTIES),
        ],
    )
    def test_to_canonical(
        self,
        source: EngineOpportunityCategory | GlobalSourceCategory | MercenaryCategory | OpportunityCategory,
        target: OpportunityCategory,
    ) -> None:
        assert to_canonical(source) is target

    def test_canonical_is_identity(self) -> None:
        assert to_canonical(OpportunityCategory.WEB_SCRAPING) is OpportunityCategory.WEB_SCRAPING


class TestContract:
    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown opportunity category type"):
            to_canonical("bug_bounty")  # type: ignore[arg-type,unused-ignore]

    def test_mappings_are_total_and_nonempty(self) -> None:
        assert len(ENGINE_TO_CANONICAL) == len(EngineOpportunityCategory) == 11
        # 2026-08-25: ai_evaluation family added to the curated catalog.
        assert len(GLOBAL_SOURCE_TO_CANONICAL) == len(GlobalSourceCategory) == 4
        assert len(MERCENARY_TO_CANONICAL) == len(MercenaryCategory) == 11


class TestOpenSourceMappings:
    def test_opensource_mapping_covers_every_member(self) -> None:
        from cores.opensource.categories import OpenSourceCategory
        from cores.work_taxonomy import OPEN_SOURCE_TO_CANONICAL

        missing = set(OpenSourceCategory) - set(OPEN_SOURCE_TO_CANONICAL)
        assert not missing, f"Unmapped opensource categories: {sorted(missing)}"

    def test_opensource_exact_matches(self) -> None:
        from cores.direct_work_engine.models import OpportunityCategory as Canonical
        from cores.opensource.categories import OpenSourceCategory as OpenSourceCat
        from cores.work_taxonomy import to_canonical

        assert to_canonical(OpenSourceCat.BUG_BOUNTY) is Canonical.BUG_BOUNTY
        assert to_canonical(OpenSourceCat.CODE_REVIEW) is Canonical.CODE_REVIEW
        assert to_canonical(OpenSourceCat.DOCUMENTATION) is Canonical.DOCUMENTATION
        assert to_canonical(OpenSourceCat.INFRASTRUCTURE) is Canonical.INFRASTRUCTURE
        assert to_canonical(OpenSourceCat.TESTING) is Canonical.QA_AUTOMATION

    def test_opensource_totality(self) -> None:
        from cores.opensource.categories import OpenSourceCategory
        from cores.work_taxonomy import OPEN_SOURCE_TO_CANONICAL

        assert len(OPEN_SOURCE_TO_CANONICAL) == len(OpenSourceCategory) == 10
