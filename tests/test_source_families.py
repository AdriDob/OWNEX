"""Level-2 source family contract.

Families expand the catalog without adding canonical OpportunityCategory
values: canonical stays the 38-value level-1 taxonomy.
"""

from __future__ import annotations

from cores.direct_work_engine.models import OpportunityCategory
from cores.opportunity.global_sources import OpportunityCategory as CatalogCategory
from cores.opportunity.global_sources import SourceDefinition, get_sources
from cores.opportunity.source_families import (
    SOURCE_FAMILY_TO_CANONICAL,
    SourceFamily,
    canonical_for_family,
    catalog_family_summary,
    source_family_for,
)


def _source(name: str, description: str = "", **kwargs: object) -> SourceDefinition:
    defaults: dict[str, object] = {
        "name": name,
        "url": "https://example.com",
        "category": CatalogCategory.dev_bounty,
        "description": description,
        "type": "platform",
        "apply_method": "profile_only",
    }
    defaults.update(kwargs)
    return SourceDefinition(**defaults)  # type: ignore[arg-type]


class TestSourceFamilies:
    def test_seven_priority_families_exist(self) -> None:
        assert len(SourceFamily) == 7

    def test_family_targets_are_canonical_categories(self) -> None:
        for family, target in SOURCE_FAMILY_TO_CANONICAL.items():
            assert target in set(OpportunityCategory)
            assert canonical_for_family(family) is target

    def test_keyword_classification_examples(self) -> None:
        by_name = {source.name: source for source in get_sources()}
        assert source_family_for(by_name["Outlier"]) is SourceFamily.AI_CODING_EVALUATION
        assert source_family_for(by_name["Test IO"]) is SourceFamily.QA_TESTING_SERVICES
        assert source_family_for(by_name["Algora"]) is SourceFamily.FUNDED_OSS_GRANTS
        assert source_family_for(by_name["Immunefi"]) is None

    def test_explicit_source_family_wins(self) -> None:
        source = _source("Custom", source_family=SourceFamily.QA_TESTING_SERVICES.value)
        assert source_family_for(source) is SourceFamily.QA_TESTING_SERVICES

    def test_summary_counts_match_current_catalog(self) -> None:
        summary = catalog_family_summary()
        # 2026-11-10: catalog expanded past the 1000-source cap; the summary
        # unions the capped catalog with own_work_sources extensions, so
        # totals track the live catalog — assert consistency, not literals.
        classified = sum(summary["family_counts"].values())
        assert summary["unclassified"] == summary["total_catalog_entries"] - classified
        assert summary["total_catalog_entries"] >= 1000
        assert summary["family_counts"]["ai_coding_evaluation"] == 12
        assert summary["family_counts"]["qa_testing_services"] == 6
        assert summary["family_counts"]["funded_oss_grants"] == 16
        assert summary["family_counts"]["api_sdk_integration"] == 0
        assert summary["family_counts"]["devops_cloud_tasks"] == 0
        assert summary["family_counts"]["data_engineering_tasks"] == 0
        assert summary["family_counts"]["browser_automation_gigs"] == 0
        by_family = summary["sources_by_family"]
        assert "Algora" in by_family["funded_oss_grants"]
        assert "Test IO" in by_family["qa_testing_services"]
        assert "uTest" in by_family["qa_testing_services"]
        assert "Outlier" in by_family["ai_coding_evaluation"]
        assert by_family["api_sdk_integration"] == []
