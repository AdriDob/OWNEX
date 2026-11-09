"""Source adaptation level contract.

Guards the Command Center metric that separates catalog size from real
adaptation: 176 registered sources must not be reported as 176 operational
integrations.
"""

from __future__ import annotations

from cores.opportunity.source_adaptation import (
    SourceAdaptationLevel,
    adaptation_level_for_source,
    adapter_ready_source_names,
    catalog_adaptation_summary,
    platform_for_source,
)


class TestAdaptationLevels:
    def test_catalog_payout_candidates_are_adapter_ready(self) -> None:
        assert adaptation_level_for_source("Algora") is SourceAdaptationLevel.ADAPTER_READY
        assert adaptation_level_for_source("HackerOne") is SourceAdaptationLevel.ADAPTER_READY

    def test_registered_adapter_sources_are_adapter_ready(self) -> None:
        for name in ("Outlier", "Mindrift", "Remotasks", "Data Annotation Tech"):
            assert adaptation_level_for_source(name) is SourceAdaptationLevel.ADAPTER_READY

    def test_mapped_platform_without_payout_is_not_adapter_ready(self) -> None:
        level = adaptation_level_for_source("GitHub Sponsors / funded issues (public repos)")
        assert level is SourceAdaptationLevel.DISCOVERABLE

    def test_global_only_source_is_catalog_only(self) -> None:
        assert adaptation_level_for_source("Zerocopter") is SourceAdaptationLevel.CATALOG_ONLY
        assert adaptation_level_for_source("Test IO") is SourceAdaptationLevel.CATALOG_ONLY

    def test_verified_levels_stay_empty_without_live_evidence(self) -> None:
        summary = catalog_adaptation_summary()["levels"]
        assert summary["integration_verified"] == 0
        assert summary["argentina_verified"] == 0
        assert summary["production_active"] == 0


class TestCatalogSummary:
    def test_summary_counts_match_curated_union(self) -> None:
        summary = catalog_adaptation_summary()
        assert summary["total_sources"] == 176
        assert summary["levels"]["adapter_ready"] == 17
        assert summary["levels"]["discoverable"] == 33
        assert summary["levels"]["catalog_only"] == 126

    def test_adapter_ready_names_match_programmed_or_payout_ready_sources(self) -> None:
        assert adapter_ready_source_names() == frozenset(
            {
                "Algora",
                "Bugcrowd",
                "Data Annotation Tech",
                "Freelancer (coding)",
                "HackerOne",
                "Immunefi",
                "Intigriti",
                "IssueHunt",
                "LinkedIn (Easy Apply)",
                "Mindrift",
                "Open Collective",
                "Opire",
                "Opyre",
                "Outlier",
                "Remotasks",
                "Superteam Earn",
                "YesWeHack",
            }
        )

    def test_platform_mapping_is_exposed_for_adapter_scaffolding(self) -> None:
        assert platform_for_source("Algora") == "algora"
        assert platform_for_source("Zerocopter") is None
