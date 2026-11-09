"""Level-2 source families for the OWNEX catalog.

Canonical ``OpportunityCategory`` stays the level-1 taxonomy (38 values).
This module adds source *families* — the paid-work surfaces that feed those
canonical categories — without multiplying the canonical enum.

A family is assigned conservatively: explicit ``SourceDefinition.source_family``
first, then keyword match over name+description only (tags are ignored because
platform tags like ``api`` are too noisy for family detection).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from cores.direct_work_engine.models import OpportunityCategory
from cores.opportunity.global_sources import SourceDefinition, get_sources
from cores.opportunity.own_work_sources import CRYPTO_DEV_SOURCES, WEB_DEV_SOURCES
from cores.opportunity.own_work_sources_extensions import (
    build_fifth_wave_dev_extension,
    build_fourth_wave_bounty_extension,
    build_fourth_wave_dev_extension,
    build_second_wave_extension,
    build_sixth_wave_dev_extension,
    build_sixth_wave_security_extension,
    build_third_wave_extension,
)


class SourceFamily(StrEnum):
    """Priority source families agreed for the next catalog expansion."""

    AI_CODING_EVALUATION = "ai_coding_evaluation"
    QA_TESTING_SERVICES = "qa_testing_services"
    FUNDED_OSS_GRANTS = "funded_oss_grants"
    API_SDK_INTEGRATION = "api_sdk_integration"
    DEVOPS_CLOUD_TASKS = "devops_cloud_tasks"
    DATA_ENGINEERING_TASKS = "data_engineering_tasks"
    BROWSER_AUTOMATION_GIGS = "browser_automation_gigs"


SOURCE_FAMILY_TO_CANONICAL: dict[SourceFamily, OpportunityCategory] = {
    SourceFamily.AI_CODING_EVALUATION: OpportunityCategory.AI_EVALUATION,
    SourceFamily.QA_TESTING_SERVICES: OpportunityCategory.QA_AUTOMATION,
    SourceFamily.FUNDED_OSS_GRANTS: OpportunityCategory.OSS_BOUNTIES,
    SourceFamily.API_SDK_INTEGRATION: OpportunityCategory.API_DEVELOPMENT,
    SourceFamily.DEVOPS_CLOUD_TASKS: OpportunityCategory.DEVOPS,
    SourceFamily.DATA_ENGINEERING_TASKS: OpportunityCategory.DATA_ENGINEERING,
    SourceFamily.BROWSER_AUTOMATION_GIGS: OpportunityCategory.BROWSER_AUTOMATION,
}

# Research leads per family. These are candidates to verify, not catalogued
# sources and not claims of availability or payout.
SOURCE_FAMILY_CANDIDATES: dict[SourceFamily, tuple[str, ...]] = {
    SourceFamily.AI_CODING_EVALUATION: (
        "Mercor",
        "Alignerr",
        "Mindrift",
        "OneForma",
        "Outlier Coding",
    ),
    SourceFamily.QA_TESTING_SERVICES: ("uTest", "Test IO", "Testbirds", "BugFinders", "Applause"),
    SourceFamily.FUNDED_OSS_GRANTS: (
        "Gitcoin",
        "OnlyDust",
        "Polar",
        "Open Collective",
        "Algora",
        "Opire",
        "IssueHunt",
        "Opyre",
        "Bountysource",
    ),
    SourceFamily.API_SDK_INTEGRATION: ("RapidAPI", "Postman", "Zapier", "Make", "n8n"),
    SourceFamily.DEVOPS_CLOUD_TASKS: ("Kubernetes community tasks", "Terraform registry bounties", "Cloud migration gigs"),
    SourceFamily.DATA_ENGINEERING_TASKS: ("Kaggle", "DrivenData", "Zindi", "AIcrowd", "data pipeline bounties"),
    SourceFamily.BROWSER_AUTOMATION_GIGS: ("Playwright automation gigs", "Selenium automation gigs", "BrowserFlow", "Steel.dev"),
}

_FAMILY_KEYWORDS: dict[SourceFamily, tuple[str, ...]] = {
    SourceFamily.AI_CODING_EVALUATION: (
        "outlier",
        "mindrift",
        "mercor",
        "alignerr",
        "codeforai",
        "ai training",
        "ai evaluation",
        "llm eval",
        "coding eval",
    ),
    SourceFamily.QA_TESTING_SERVICES: (
        "test io",
        "utest",
        "testbird",
        "bugfinder",
        "applause",
        "userlytics",
        "usertesting",
        "quality assurance",
        "functional testing",
        "test case",
    ),
    SourceFamily.FUNDED_OSS_GRANTS: (
        "issuehunt",
        "algora",
        "opire",
        "opyre",
        "opencollective",
        "github sponsors",
        "funded issues",
        "bounty labels",
        "gitcoin",
        "codefund",
        "onlydust",
        "polar",
        "bountysource",
        "huntr",
        "oss bounties",
        "open source bounty",
    ),
    SourceFamily.API_SDK_INTEGRATION: (
        "api sdk",
        "sdk integration",
        "api integration",
        "zapier",
        "postman",
        "rapidapi",
        "workato",
        "make.com",
        "n8n",
    ),
    SourceFamily.DEVOPS_CLOUD_TASKS: (
        "devops",
        "cloud migration",
        "kubernetes",
        "docker",
        "ci/cd",
        "terraform",
        "site reliability",
        "infrastructure as code",
    ),
    SourceFamily.DATA_ENGINEERING_TASKS: (
        "data engineering",
        "etl pipeline",
        "data pipeline",
        "web scraping",
        "kaggle",
        "drivendata",
        "zindi",
        "aicrowd",
    ),
    SourceFamily.BROWSER_AUTOMATION_GIGS: (
        "browser automation",
        "playwright",
        "selenium",
        "browserflow",
        "steel.dev",
        "web automation",
        "ui automation",
        "rpa",
    ),
}


def source_family_for(source: SourceDefinition) -> SourceFamily | None:
    """Return the level-2 family for a catalog source, if classifiable."""
    explicit = (source.source_family or "").strip()
    if explicit:
        try:
            return SourceFamily(explicit)
        except ValueError:
            return None
    text = f"{source.name} {source.description}".lower()
    for family in SourceFamily:
        if any(keyword in text for keyword in _FAMILY_KEYWORDS[family]):
            return family
    return None


def _catalog_sources_by_name() -> dict[str, SourceDefinition]:
    """Deduplicated union of global catalog + OwnWork block by source name."""
    sources = {source.name: source for source in get_sources()}
    own_work = list(WEB_DEV_SOURCES + CRYPTO_DEV_SOURCES)
    for builder in (
        build_second_wave_extension,
        build_third_wave_extension,
        build_fourth_wave_bounty_extension,
        build_fourth_wave_dev_extension,
        build_fifth_wave_dev_extension,
        build_sixth_wave_security_extension,
        build_sixth_wave_dev_extension,
    ):
        own_work.extend(builder().sources)
    for source in own_work:
        sources[source.name] = source
    return sources


def catalog_family_summary() -> dict[str, Any]:
    """Count deduplicated catalog sources per level-2 family."""
    counts = {family.value: 0 for family in SourceFamily}
    sources_by_family: dict[str, list[str]] = {family.value: [] for family in SourceFamily}
    unclassified = 0
    sources = _catalog_sources_by_name()
    for source in sources.values():
        family = source_family_for(source)
        if family is None:
            unclassified += 1
        else:
            counts[family.value] += 1
            sources_by_family[family.value].append(source.name)
    for names in sources_by_family.values():
        names.sort()
    return {
        "total_catalog_entries": len(sources),
        "family_counts": counts,
        "sources_by_family": sources_by_family,
        "unclassified": unclassified,
        "candidate_counts": {family.value: len(names) for family, names in SOURCE_FAMILY_CANDIDATES.items()},
    }


def canonical_for_family(family: SourceFamily) -> OpportunityCategory:
    """Return the canonical level-1 category for a source family."""
    return SOURCE_FAMILY_TO_CANONICAL[family]
