"""Tests for the OWNEX-owned OwnWork extension registry.

Tests the extension layer in ``cores.opportunity.own_work_sources_extensions``
without touching the SSOT catalog in ``cores.opportunity.global_sources`` and
without duplicating the base 18-source registry in ``cores.opportunity.own_work_sources``.
"""

from __future__ import annotations

from typing import Any

import pytest

from cores.opportunity.global_sources import OpportunityCategory, SourceDefinition
from cores.opportunity.own_work_sources_extensions import (
    OwnWorkExtension,
    OwnWorkExtensionCatalog,
    build_crypto_dev_extension,
    build_example_extension,
    build_multi_extension,
    build_non_pagable_extension,
)


@pytest.fixture
def catalog() -> OwnWorkExtensionCatalog:
    return OwnWorkExtensionCatalog()


def test_empty_catalog_count(catalog: OwnWorkExtensionCatalog) -> None:
    assert catalog.count() == 0
    assert catalog.source_count() == 0


def test_register_example_extension(catalog: OwnWorkExtensionCatalog) -> None:
    ext = build_example_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 1


def test_register_multi_extension(catalog: OwnWorkExtensionCatalog) -> None:
    ext = build_multi_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 2


def test_register_non_pagable_extension(catalog: OwnWorkExtensionCatalog) -> None:
    ext = build_non_pagable_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 1
    assert not ext.payment_documented


def test_register_crypto_dev_extension(catalog: OwnWorkExtensionCatalog) -> None:
    ext = build_crypto_dev_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 1
    assert ext.payment_documented


def test_register_duplicate_extension_name(catalog: OwnWorkExtensionCatalog) -> None:
    ext = build_example_extension()
    catalog.register(ext)
    with pytest.raises(ValueError, match="already registered"):
        catalog.register(ext)


def test_register_duplicate_source_name(catalog: OwnWorkExtensionCatalog) -> None:
    a = OwnWorkExtension(
        name="ext_with_example_source_a",
        sources=[build_example_extension().sources[0]],
        payment_method="crypto",
        payment_documented=True,
        payment_note="a",
        category=OpportunityCategory.dev_bounty,
    )
    b = OwnWorkExtension(
        name="ext_with_example_source_b",
        sources=[build_example_extension().sources[0]],
        payment_method="paypal",
        payment_documented=True,
        payment_note="b",
        category=OpportunityCategory.dev_bounty,
    )
    catalog.register(a)
    with pytest.raises(ValueError, match="Source already registered by name"):
        catalog.register(b)


def test_unregister(catalog: OwnWorkExtensionCatalog) -> None:
    ext = build_example_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    catalog.unregister("example_dev_extension")
    assert catalog.count() == 0
    assert catalog.source_count() == 0


def test_find_by_category(catalog: OwnWorkExtensionCatalog) -> None:
    catalog.register(build_example_extension())
    catalog.register(build_crypto_dev_extension())
    dev = catalog.find_by_category(OpportunityCategory.dev_bounty)
    crypto = catalog.find_by_category(OpportunityCategory.bug_bounty)
    assert len(dev) == 1
    assert len(crypto) == 1


def test_find_by_source_name(catalog: OwnWorkExtensionCatalog) -> None:
    catalog.register(build_example_extension())
    src = catalog.find_by_source_name("Example Dev Extension Source")
    assert src is not None
    assert src.name == "Example Dev Extension Source"
    assert catalog.find_by_source_name("no-such-source") is None


def test_sources_by_category(catalog: OwnWorkExtensionCatalog) -> None:
    catalog.register(build_example_extension())
    catalog.register(build_multi_extension())
    dev_sources = catalog.sources_by_category(OpportunityCategory.dev_bounty)
    assert len(dev_sources) == 3


def test_documented_payment_methods(catalog: OwnWorkExtensionCatalog) -> None:
    catalog.register(build_example_extension())
    catalog.register(build_multi_extension())
    catalog.register(build_crypto_dev_extension())
    catalog.register(build_non_pagable_extension())
    methods = catalog.documented_payment_methods()
    assert "crypto" in methods
    assert "paypal" in methods
    assert len(methods) == 3


def test_documented_payment_count(catalog: OwnWorkExtensionCatalog) -> None:
    catalog.register(build_example_extension())
    catalog.register(build_multi_extension())
    catalog.register(build_non_pagable_extension())
    assert catalog.documented_payment_count() == 2


def test_documented_payment_for(catalog: OwnWorkExtensionCatalog) -> None:
    catalog.register(build_example_extension())
    assert catalog.documented_payment_for("example_dev_extension") == "crypto"
    assert catalog.documented_payment_for("missing") is None


def test_documented_payment_note_for(catalog: OwnWorkExtensionCatalog) -> None:
    catalog.register(build_example_extension())
    note = catalog.documented_payment_note_for("example_dev_extension")
    assert note == "Example payment note."
    assert catalog.documented_payment_note_for("missing") is None


def test_documented_payment_methods_for_source_name(catalog: OwnWorkExtensionCatalog) -> None:
    catalog.register(build_example_extension())
    methods = catalog.documented_payment_methods_for_source_name("Example Dev Extension Source")
    assert "crypto" in methods


def test_extension_category_of_first(catalog: OwnWorkExtensionCatalog) -> None:
    ext = build_example_extension()
    catalog.register(ext)
    assert ext.category_of_first() == OpportunityCategory.dev_bounty


def test_extension_category_override(
    catalog: OwnWorkExtensionCatalog,
) -> None:
    ext = OwnWorkExtension(
        name="override_category_extension",
        sources=[
            _source(
                name="Override Category Source",
                url="https://example.dev/override",
                category=OpportunityCategory.dev_bounty,
            ),
        ],
        category=OpportunityCategory.bug_bounty,
    )
    catalog.register(ext)
    assert ext.category_of_first() == OpportunityCategory.bug_bounty


# Third-wave extension tests


def test_register_third_wave_extension(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_third_wave_extension,
    )

    ext = build_third_wave_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 5
    assert ext.payment_documented
    assert ext.payment_method == "crypto"


def test_third_wave_extension_sources(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_third_wave_extension,
    )

    ext = build_third_wave_extension()
    catalog.register(ext)
    sources = ext.sources
    assert len(sources) == 5
    names = {s.name for s in sources}
    assert names == {
        "Gitcoin Bounties",
        "Bounties Network",
        "ETHGlobal Bounties",
        "CodeTriage Bounties",
        "Polywork Bounties",
    }


def test_third_wave_extension_payment_docs(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_payment_doc_third_wave,
        build_third_wave_extension,
    )

    ext = build_third_wave_extension()
    catalog.register(ext)
    docs = build_payment_doc_third_wave()
    assert len(docs) == 5
    assert "Gitcoin Bounties" in docs
    assert docs["Gitcoin Bounties"]["methods"] == ["crypto", "stablecoin"]
    assert "CodeTriage Bounties" in docs
    assert docs["CodeTriage Bounties"]["methods"] == ["not_published"]


def test_third_wave_sources_by_category_bug_bounty(
    catalog: OwnWorkExtensionCatalog,
) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_third_wave_extension,
    )

    ext = build_third_wave_extension()
    catalog.register(ext)
    crypto_sources = catalog.sources_by_category(
        OpportunityCategory.bug_bounty,
    )
    # All five third-wave sources are bug_bounty category
    assert len(crypto_sources) == 5


def test_third_wave_sources_by_category_dev_bounty(
    catalog: OwnWorkExtensionCatalog,
) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_third_wave_extension,
    )

    ext = build_third_wave_extension()
    catalog.register(ext)
    dev_sources = catalog.sources_by_category(
        OpportunityCategory.dev_bounty,
    )
    # Third wave has no dev_bounty sources (all are bug_bounty)
    assert len(dev_sources) == 0


def _source(
    name: str,
    url: str,
    category: OpportunityCategory,
    **kwargs: Any,
) -> SourceDefinition:
    defaults: dict[str, Any] = {
        "name": name,
        "url": url,
        "category": category,
        "description": "",
        "type": "platform",
        "apply_method": "profile_only",
        "quality_score": 0.5,
        "requires_account": True,
        "requires_portfolio": False,
        "requires_interview": False,
        "requires_experience": False,
        "language": "en",
        "region": "global",
        "estimated_payout_range": "varies",
        "tags": [],
        "last_verified": "2026-07-30",
        "priority": 0,
        "requires_assessment": False,
        "typical_hourly_rate_usd": None,
        "time_to_first_work_hours": None,
        "payout_cadence_days": None,
    }
    defaults.update(kwargs)
    return SourceDefinition(**defaults)


# Fourth-wave extension tests


def test_register_fourth_wave_bounty_extension(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fourth_wave_bounty_extension,
    )

    ext = build_fourth_wave_bounty_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 4
    assert ext.payment_documented
    assert ext.payment_method == "paypal"
    assert ext.category_of_first() == OpportunityCategory.bug_bounty


def test_register_fourth_wave_dev_extension(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fourth_wave_dev_extension,
    )

    ext = build_fourth_wave_dev_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 3
    assert ext.payment_documented
    assert ext.category_of_first() == OpportunityCategory.dev_bounty


def test_fourth_wave_extension_source_names(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fourth_wave_bounty_extension,
        build_fourth_wave_dev_extension,
    )

    bounty = build_fourth_wave_bounty_extension()
    dev = build_fourth_wave_dev_extension()
    catalog.register(bounty)
    catalog.register(dev)
    assert {s.name for s in bounty.sources} == {
        "HackerOne",
        "Bugcrowd",
        "Intigriti",
        "YesWeHack",
    }
    assert {s.name for s in dev.sources} == {
        "Open Collective",
        "OnlyDust",
        "Polar",
    }


def test_fourth_wave_payment_docs(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fourth_wave_bounty_extension,
        build_fourth_wave_dev_extension,
        build_payment_doc_fourth_wave,
    )

    catalog.register(build_fourth_wave_bounty_extension())
    catalog.register(build_fourth_wave_dev_extension())
    docs = build_payment_doc_fourth_wave()
    assert len(docs) == 7
    assert docs["HackerOne"]["methods"] == ["paypal", "bank_transfer"]
    assert docs["Intigriti"]["methods"] == ["bank_transfer", "paypal"]
    assert docs["OnlyDust"]["methods"] == ["crypto", "stablecoin"]
    assert docs["Polar"]["methods"] == ["not_published"]


def test_fourth_wave_sources_by_category(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fourth_wave_bounty_extension,
        build_fourth_wave_dev_extension,
    )

    catalog.register(build_fourth_wave_bounty_extension())
    catalog.register(build_fourth_wave_dev_extension())
    assert len(catalog.sources_by_category(OpportunityCategory.bug_bounty)) == 4
    assert len(catalog.sources_by_category(OpportunityCategory.dev_bounty)) == 3


# Fifth-wave extension tests


def test_register_fifth_wave_dev_extension(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fifth_wave_dev_extension,
    )

    ext = build_fifth_wave_dev_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 7
    assert ext.payment_documented
    assert ext.payment_method == "crypto"
    assert ext.category_of_first() == OpportunityCategory.dev_bounty


def test_fifth_wave_extension_source_names(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fifth_wave_dev_extension,
    )

    ext = build_fifth_wave_dev_extension()
    catalog.register(ext)
    assert {s.name for s in ext.sources} == {
        "GitHub Bounty Labels",
        "OpenQ",
        "Codefund",
        "HackerLink",
        "Dework",
        "Guild.xyz",
        "Buidlbox",
    }


def test_fifth_wave_payment_docs(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fifth_wave_dev_extension,
        build_payment_doc_fifth_wave,
    )

    catalog.register(build_fifth_wave_dev_extension())
    docs = build_payment_doc_fifth_wave()
    assert len(docs) == 7
    assert docs["GitHub Bounty Labels"]["methods"] == ["not_published"]
    assert docs["OpenQ"]["methods"] == ["crypto", "stablecoin"]
    assert docs["Dework"]["methods"] == ["crypto", "stablecoin"]
    assert docs["Buidlbox"]["methods"] == ["crypto", "stablecoin"]


def test_fifth_wave_sources_by_category(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_fifth_wave_dev_extension,
    )

    catalog.register(build_fifth_wave_dev_extension())
    assert len(catalog.sources_by_category(OpportunityCategory.dev_bounty)) == 7
    assert len(catalog.sources_by_category(OpportunityCategory.bug_bounty)) == 0


# Sixth-wave extension tests


def test_register_sixth_wave_security_extension(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_sixth_wave_security_extension,
    )

    ext = build_sixth_wave_security_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 1
    assert ext.payment_documented
    assert ext.payment_method == "paypal"
    assert ext.category_of_first() == OpportunityCategory.bug_bounty


def test_register_sixth_wave_dev_extension(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_sixth_wave_dev_extension,
    )

    ext = build_sixth_wave_dev_extension()
    catalog.register(ext)
    assert catalog.count() == 1
    assert catalog.source_count() == 1
    assert ext.payment_documented
    assert ext.payment_method == "crypto"
    assert ext.category_of_first() == OpportunityCategory.dev_bounty


def test_sixth_wave_payment_docs(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_payment_doc_sixth_wave,
        build_sixth_wave_dev_extension,
        build_sixth_wave_security_extension,
    )

    catalog.register(build_sixth_wave_security_extension())
    catalog.register(build_sixth_wave_dev_extension())
    docs = build_payment_doc_sixth_wave()
    assert len(docs) == 2
    assert docs["Patchstack"]["methods"] == ["paypal", "crypto"]
    assert docs["Bountycaster"]["methods"] == ["crypto", "stablecoin"]


def test_sixth_wave_sources_by_category(catalog: OwnWorkExtensionCatalog) -> None:
    from cores.opportunity.own_work_sources_extensions import (
        build_sixth_wave_dev_extension,
        build_sixth_wave_security_extension,
    )

    catalog.register(build_sixth_wave_security_extension())
    catalog.register(build_sixth_wave_dev_extension())
    assert len(catalog.sources_by_category(OpportunityCategory.bug_bounty)) == 1
    assert len(catalog.sources_by_category(OpportunityCategory.dev_bounty)) == 1
