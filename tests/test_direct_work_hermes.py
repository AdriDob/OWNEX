"""Tests for the Hermes Direct Work Adapter prototype (Fase C — Contract Verification).

Scope:
- The adapter imports cleanly from api.adapters.direct_work_hermes.
- The adapter accepts a DiscoverySource in __init__ (same contract as the base
  adapter) and stores an optional hermes_source for Hermes-specific fields.
- The adapter produces opportunity objects that conform to the engine contract:
  platform, category, payment_method, employment_type, entry_mechanism,
  international_payment, experience_requirement, rate_source, technology_tags.
- The adapter does NOT claim payment verification, Argentina compatibility, or
  FULLY_ELIGIBLE status for any source.
"""

from __future__ import annotations

import pytest

from api.adapters.direct_work_hermes import HermesDirectWorkAdapter
from cores.direct_work_engine import models as dwe_models
from cores.direct_work_engine.discovery import DiscoverySource


def _make_catalog_source(**kwargs):
    """Factory helper: create a minimal SourceDefinition-like object from real
    catalog field names so we can test with real catalog source shapes.

    Each concrete source must provide at least id, name, url, category, and
    platform (either a platform string or None) so the adapter can run the
    whole mapping pipeline.
    """
    defaults = {
        "id": kwargs.get("id", "test"),
        "name": kwargs.get("name", kwargs.get("id", "test")),
        "url": kwargs.get("url", "https://example.test"),
        "category": kwargs.get("category", "dev_bounty"),
        "platform": kwargs.get("platform", None),
        "employment_type": kwargs.get("employment_type", "bounty"),
        "payment_methods": kwargs.get("payment_methods", []),
        "requires_account": kwargs.get("requires_account", False),
        "apply_method": kwargs.get("apply_method", "direct"),
        "region": kwargs.get("region", ""),
        "requires_experience": kwargs.get("requires_experience", False),
        "tags": kwargs.get("tags", []),
        "heuristics_analyzed": kwargs.get("heuristics_analyzed", None),
        "analysis_complete": kwargs.get("analysis_complete", None),
        "cached_analysis": kwargs.get("cached_analysis", None),
        "analysis_revision": kwargs.get("analysis_revision", None),
        "analysis_started_at": kwargs.get("analysis_started_at", None),
    }
    defaults.update(kwargs)
    return type("SourceDefinition", (), defaults)()


def test_hermes_adapter_imports():
    from api.adapters.direct_work_hermes import HermesDirectWorkAdapter

    assert hasattr(HermesDirectWorkAdapter, "fetch_opportunities")
    assert hasattr(HermesDirectWorkAdapter, "validate_connection")


def test_hermes_adapter_constructs_with_discovery_source():
    """HermesDirectWorkAdapter accepts a DiscoverySource and stores the
    hermes_source placeholder as None until a catalog source is loaded."""
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    assert adapter.source is source
    assert adapter.hermes_source is None


def test_hermes_adapter_loads_catalog_source():
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
    )
    adapter.load_catalog_source(catalog_source)
    assert adapter.hermes_source is catalog_source


def test_hermes_adapter_fetch_opportunities_populates_base_fields():
    """The adapter builds an Opportunity with the same base mappings as the
    base adapter; Hermes-specific analysis fields are NOT set on the
    Opportunity because the engine model uses __slots__ and blocks injection
    of fields that do not exist in the model. These fields live only in the
    catalog source object (this adapter's own space)."""
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
        heuristics_analyzed=True,
        analysis_complete=False,
        cached_analysis=True,
        analysis_revision=2,
        analysis_started_at="2024-01-15T10:00:00Z",
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    assert len(opps) == 1
    opp = opps[0]
    assert opp.platform == dwe_models.WorkPlatform.ALGORA
    assert opp.category == dwe_models.OpportunityCategory.DEV_BOUNTY
    assert opp.payment_method == dwe_models.PaymentMethod.CRYPTO
    assert opp.employment_type == dwe_models.EmploymentType.BOUNTY
    assert opp.entry_mechanism == dwe_models.EntryMechanism.DIRECT
    assert opp.international_payment is True
    assert opp.experience_requirement == dwe_models.ExperienceRequirement.NONE
    assert opp.rate_source == "catalog"
    assert set(opp.technology_tags) == {"crypto", "web3"}
    # Hermes-specific analysis fields are NOT set on the Opportunity because
    # the engine model uses __slots__ and blocks injection of fields that do
    # not exist in the model. The catalog source object (this adapter's own
    # space) keeps them.
    assert not hasattr(opp, "heuristics_analyzed")
    assert not hasattr(opp, "analysis_complete")
    assert not hasattr(opp, "cached_analysis")
    assert not hasattr(opp, "analysis_revision")
    assert not hasattr(opp, "analysis_started_at")
    # The catalog source object (this adapter's own space) does have them.
    assert catalog_source.heuristics_analyzed is True
    assert catalog_source.analysis_complete is False
    assert catalog_source.cached_analysis is True
    assert catalog_source.analysis_revision == 2
    assert catalog_source.analysis_started_at == "2024-01-15T10:00:00Z"


def test_hermes_adapter_respects_hermes_specific_fields():
    """Hermes-specific analysis fields are NOT set on the Opportunity because
    the engine model uses __slots__ and blocks injection of fields that do not
    exist in the model. These fields live only in the catalog source object
    (this adapter's own space) and are NOT transferred to the engine's
    Opportunity."""
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
        heuristics_analyzed=True,
        analysis_complete=False,
        cached_analysis=True,
        analysis_revision=2,
        analysis_started_at="2024-01-15T10:00:00Z",
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    opp = opps[0]
    # The engine model blocks injection of these fields, so they are NOT on
    # the Opportunity. The catalog source object (this adapter's own space)
    # keeps them.
    assert not hasattr(opp, "heuristics_analyzed")
    assert not hasattr(opp, "analysis_complete")
    assert not hasattr(opp, "cached_analysis")
    assert not hasattr(opp, "analysis_revision")
    assert not hasattr(opp, "analysis_started_at")
    assert catalog_source.heuristics_analyzed is True
    assert catalog_source.analysis_complete is False
    assert catalog_source.cached_analysis is True
    assert catalog_source.analysis_revision == 2
    assert catalog_source.analysis_started_at == "2024-01-15T10:00:00Z"


def test_hermes_adapter_maps_entry_mechanism():
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    assert opps[0].entry_mechanism == dwe_models.EntryMechanism.DIRECT


def test_hermes_adapter_maps_international_payment():
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    assert opps[0].international_payment is True


def test_hermes_adapter_maps_experience_requirement():
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    assert opps[0].experience_requirement == dwe_models.ExperienceRequirement.NONE


def test_hermes_adapter_maps_rate_source():
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    assert opps[0].rate_source == "catalog"


def test_hermes_adapter_maps_technology_tags():
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    assert set(opps[0].technology_tags) == {"crypto", "web3"}


@pytest.mark.asyncio
async def test_hermes_adapter_handles_empty_catalog_source():
    """When no catalog source is loaded, fetch_opportunities returns an empty list."""
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    opps = await adapter.fetch_opportunities()
    assert opps == []


def test_hermes_adapter_handles_unknown_employment_type():
    """Unknown employment_type falls back to EmploymentType.BOUNTY via the base
    mapping, same as the base adapter."""
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="unknown_type",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    # Unknown employment_type falls back to BOUNTY (the default mapping)
    assert opps[0].employment_type == dwe_models.EmploymentType.BOUNTY


def test_hermes_adapter_construction_is_fast():
    """Construction + load + first build is fast enough for prototype iteration."""
    source = DiscoverySource(
        name="hermes",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = HermesDirectWorkAdapter(source)
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        url="https://example.test",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        region="AR",
        entry_mechanism="direct",
        international_payment=True,
        experience_requirement="none",
        rate_source="catalog",
        technology_tags=["crypto", "web3"],
        heuristics_analyzed=True,
        analysis_complete=False,
        cached_analysis=True,
        analysis_revision=2,
        analysis_started_at="2024-01-15T10:00:00Z",
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunities()
    assert len(opps) == 1


def _hermes_discovery(platform=dwe_models.WorkPlatform.ALGORA):
    return DiscoverySource(
        name="hermes-contract",
        platform=platform,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )


def test_hermes_adapter_unknown_payment_methods_fall_back_platform_credit():
    adapter = HermesDirectWorkAdapter(_hermes_discovery())
    catalog_source = _make_catalog_source(
        id="unknown_pay",
        name="unknown_pay",
        platform="algora",
        payment_methods=["voucher", "points"],
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunities()[0]
    assert opp.payment_method == dwe_models.PaymentMethod.PLATFORM_CREDIT
    assert opp.payment == 0.0


def test_hermes_adapter_unknown_platform_keeps_discovery_platform():
    adapter = HermesDirectWorkAdapter(_hermes_discovery(dwe_models.WorkPlatform.OTHER))
    catalog_source = _make_catalog_source(
        id="unknown_platform",
        name="unknown_platform",
        platform="not_in_source_platform_map",
        payment_methods=["crypto"],
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunities()[0]
    assert opp.platform == dwe_models.WorkPlatform.OTHER
    assert opp.id.startswith("other_hermes-prototype-")


def test_hermes_adapter_unknown_category_falls_back_dev_bounty():
    adapter = HermesDirectWorkAdapter(_hermes_discovery())
    catalog_source = _make_catalog_source(
        id="unknown_category",
        name="unknown_category",
        platform="algora",
        category="mystery_category",
        payment_methods=["crypto"],
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunities()[0]
    assert opp.category == dwe_models.OpportunityCategory.DEV_BOUNTY


def test_hermes_adapter_explicit_international_payment_false_wins():
    adapter = HermesDirectWorkAdapter(_hermes_discovery())
    catalog_source = _make_catalog_source(
        id="no_intl",
        name="no_intl",
        platform="algora",
        payment_methods=["crypto"],
        region="global",
        international_payment=False,
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunities()[0]
    assert opp.international_payment is False


def test_hermes_adapter_serialization_excludes_catalog_only_fields():
    from api.routers.direct_work import _opportunity_to_dict

    adapter = HermesDirectWorkAdapter(_hermes_discovery())
    catalog_source = _make_catalog_source(
        id="hermes",
        name="hermes",
        platform="algora",
        payment_methods=["crypto"],
        technology_tags=["crypto", "web3"],
        heuristics_analyzed=True,
        analysis_complete=False,
        cached_analysis=True,
        analysis_revision=2,
        analysis_started_at="2024-01-15T10:00:00Z",
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunities()[0]
    data = _opportunity_to_dict(opp)
    assert data["platform"] == "algora"
    assert data["payment_method"] == "crypto"
    assert data["technology_tags"] == ["crypto", "web3"]
    assert data["rate_source"] == "catalog"
    for field in (
        "heuristics_analyzed",
        "analysis_complete",
        "cached_analysis",
        "analysis_revision",
        "analysis_started_at",
    ):
        assert field not in data


def test_hermes_adapter_builds_many_sources_deterministically():
    opps = []
    for i in range(100):
        adapter = HermesDirectWorkAdapter(_hermes_discovery())
        catalog_source = _make_catalog_source(
            id=f"bulk_{i}",
            name=f"bulk_{i}",
            platform="algora",
            payment_methods=["crypto"],
            technology_tags=[f"tag_{i}", 123, "web"],
            tags=["web", "go"],
        )
        adapter.load_catalog_source(catalog_source)
        opps.extend(adapter._build_opportunities())
    assert len(opps) == 100
    assert len({opp.id for opp in opps}) == 100
    assert opps[0].technology_tags == ["tag_0", "web", "go"]
    assert opps[-1].technology_tags == ["tag_99", "web", "go"]
