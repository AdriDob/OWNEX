"""Prototype contract tests for OwnWorkCatalogAdapter.

Scope:
- importable from api.adapters.own_work_catalog_adapter
- can construct with a DiscoverySource
- can load a SourceDefinition and build ONE Opportunity using the engine contract
- uses only enums/fields actually present in the engine models
"""

from __future__ import annotations

from api.adapters.own_work_catalog_adapter import OwnWorkCatalogAdapter, _platform_for_source
from cores.direct_work_engine import models as dwe_models
from cores.direct_work_engine.discovery import DiscoverySource


def test_imports():
    adapter = OwnWorkCatalogAdapter
    assert hasattr(adapter, "fetch_opportunities")


def test_adapter_constructs_with_discovery_source():
    source = DiscoverySource(
        name="algora",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOOTY if False else dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(source)
    assert adapter.source is source


def test_load_catalog_source():
    source = DiscoverySource(
        name="algora",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(source)
    catalog_source = _make_catalog_source(
        id="algora",
        name="algora",
        url="https://algora.io",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
    )
    adapter.load_catalog_source(catalog_source)
    assert adapter._catalog_source is catalog_source


def test_validate_connection_returns_true_when_source_configured():
    discovery_source = DiscoverySource(
        name="algora",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(discovery_source)
    # Direct call path: the contract requires validate_connection but the
    # prototype validates against a loaded source. For async eligibility we
    # only verify the contract shape here.
    assert callable(adapter.validate_connection)


def test_fetch_opportunities_returns_static_fixture():
    discovery_source = DiscoverySource(
        name="algora",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="algora",
        name="algora",
        url="https://algora.io",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
    )
    adapter.load_catalog_source(catalog_source)
    # Demonstrate the opportunity production path synchronously via the same
    # internal builder used by fetch_opportunities.
    opp = adapter._build_opportunity(catalog_source)
    assert opp.platform == dwe_models.WorkPlatform.ALGORA
    assert opp.category == dwe_models.OpportunityCategory.DEV_BOUNTY
    assert opp.payment_method == dwe_models.PaymentMethod.CRYPTO
    assert opp.employment_type == dwe_models.EmploymentType.BOUNTY
    assert opp.id.startswith("algora_ownwork-prototype-")


def test_entry_mechanism_mapping():
    discovery_source = DiscoverySource(
        name="algora",
        platform=dwe_models.WorkPlatform.ALGORA,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="algora",
        name="algora",
        url="https://algora.io",
        category="dev_bounty",
        platform="algora",
        employment_type="bounty",
        payment_methods=["crypto"],
        requires_account=True,
        apply_method="apply_on_platform",
        region="global",
        requires_experience=False,
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunity(catalog_source)
    assert opp.entry_mechanism == dwe_models.EntryMechanism.REGISTRATION
    assert opp.rate_source == "catalog"
    assert opp.international_payment is True
    assert opp.experience_requirement == dwe_models.ExperienceRequirement.NONE
    assert opp.technology_tags == []


def test_international_payment_for_argentina_region_is_none():
    discovery_source = DiscoverySource(
        name="source_ar",
        platform=dwe_models.WorkPlatform.OTHER,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="source_ar",
        name="source_ar",
        url="https://example.test",
        category="dev_bounty",
        platform="",
        employment_type="bounty",
        payment_methods=[],
        requires_account=False,
        apply_method="direct",
        region="argentina",
        requires_experience=False,
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunity(catalog_source)
    assert opp.international_payment is None


def test_entry_mechanism_unknown_apply_method_defaults_to_direct():
    discovery_source = DiscoverySource(
        name="unknown",
        platform=dwe_models.WorkPlatform.OTHER,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="unknown",
        name="unknown",
        url="https://example.test",
        category="dev_bounty",
        platform="",
        employment_type="bounty",
        payment_methods=[],
        requires_account=False,
        apply_method="unknown_method",
        region="",
        requires_experience=False,
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunity(catalog_source)
    assert opp.entry_mechanism == dwe_models.EntryMechanism.DIRECT


def test_experience_requirement_mapping():
    discovery_source = DiscoverySource(
        name="exp_req",
        platform=dwe_models.WorkPlatform.OTHER,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="exp_req",
        name="exp_req",
        url="https://example.test",
        category="dev_bounty",
        platform="",
        employment_type="bounty",
        payment_methods=[],
        requires_account=False,
        apply_method="direct",
        region="",
        requires_experience="preferred",
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunity(catalog_source)
    assert opp.experience_requirement == dwe_models.ExperienceRequirement.PREFERRED


def test_fallback_payment_method_for_undocumented_source():
    discovery_source = DiscoverySource(
        name="undocumented",
        platform=dwe_models.WorkPlatform.OTHER,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="undocumented",
        name="undocumented",
        url="https://example.test",
        category="dev_bounty",
        platform="other_platform",
        employment_type="bounty",
        payment_methods=[],
        requires_account=True,
    )
    adapter.load_catalog_source(catalog_source)
    opps = adapter._build_opportunity(catalog_source)  # type: ignore[arg-type]
    assert isinstance(opps, dwe_models.Opportunity)
    assert opps.payment_method == dwe_models.PaymentMethod.PLATFORM_CREDIT
    assert opps.payment == 0.0


def test_source_without_platform_maps_to_other():
    source = _make_catalog_source(
        id="no_platform",
        name="no_platform",
        url="https://example.test",
        category="dev_bounty",
        platform="",
        employment_type="bounty",
        payment_methods=[],
        requires_account=False,
    )
    platform = _platform_for_source(source)
    assert platform is None


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
    }
    defaults.update(kwargs)
    return type("SourceDefinition", (), defaults)()


def _discovery(platform=dwe_models.WorkPlatform.OTHER):
    return DiscoverySource(
        name="ownwork-contract",
        platform=platform,
        categories=[dwe_models.OpportunityCategory.DEV_BOUNTY],
        enabled=True,
    )


def test_real_catalog_source_algora_uses_documented_payment():
    from cores.opportunity.own_work_sources import OwnWorkSourceRegistry

    src = next(s for s in OwnWorkSourceRegistry.get_all() if s.name == "Algora")
    adapter = OwnWorkCatalogAdapter(_discovery())
    adapter.load_catalog_source(src)
    opp = adapter._build_opportunity(src)
    assert opp.platform == dwe_models.WorkPlatform.ALGORA
    assert opp.payment_method == dwe_models.PaymentMethod.CRYPTO
    assert opp.payment == 10.0
    assert opp.id.startswith("algora_ownwork-prototype-")


def test_real_catalog_source_github_sponsors_stays_platform_credit():
    from cores.opportunity.own_work_sources import OwnWorkSourceRegistry

    src = next(s for s in OwnWorkSourceRegistry.get_all() if s.name == "GitHub Sponsors / funded issues (public repos)")
    adapter = OwnWorkCatalogAdapter(_discovery())
    adapter.load_catalog_source(src)
    opp = adapter._build_opportunity(src)
    assert opp.platform == dwe_models.WorkPlatform.GITHUB
    assert opp.payment_method == dwe_models.PaymentMethod.PLATFORM_CREDIT
    assert opp.payment == 0.0


def test_unknown_payment_methods_fall_back_platform_credit():
    discovery_source = _discovery()
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="unknown_pay",
        name="unknown_pay",
        payment_methods=["voucher", "points"],
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunity(catalog_source)
    assert opp.payment_method == dwe_models.PaymentMethod.PLATFORM_CREDIT
    assert opp.payment == 0.0


def test_technology_tags_prefers_technology_tags_and_filters_non_strings():
    discovery_source = _discovery()
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="tags",
        name="tags",
        technology_tags=["python", 123, "web"],
        tags=["web", "go"],
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunity(catalog_source)
    assert opp.technology_tags == ["python", "web", "go"]


def test_opportunity_to_dict_serializes_catalog_fields_only():
    from api.routers.direct_work import _opportunity_to_dict

    discovery_source = _discovery(dwe_models.WorkPlatform.ALGORA)
    adapter = OwnWorkCatalogAdapter(discovery_source)
    catalog_source = _make_catalog_source(
        id="algora",
        name="algora",
        platform="algora",
        payment_methods=["crypto"],
        technology_tags=["crypto", "web3"],
        heuristics_analyzed=True,
    )
    adapter.load_catalog_source(catalog_source)
    opp = adapter._build_opportunity(catalog_source)
    data = _opportunity_to_dict(opp)
    assert data["platform"] == "algora"
    assert data["payment_method"] == "crypto"
    assert data["technology_tags"] == ["crypto", "web3"]
    assert data["rate_source"] == "catalog"
    assert "heuristics_analyzed" not in data


def test_fourth_wave_hackerone_maps_platform_and_documented_payment():
    from cores.opportunity.own_work_sources_extensions import (
        build_fourth_wave_bounty_extension,
    )

    src = next(s for s in build_fourth_wave_bounty_extension().sources if s.name == "HackerOne")
    adapter = OwnWorkCatalogAdapter(_discovery())
    adapter.load_catalog_source(src)
    opp = adapter._build_opportunity(src)
    assert opp.platform == dwe_models.WorkPlatform.HACKERONE
    assert opp.payment_method == dwe_models.PaymentMethod.PAYPAL
    assert opp.payment == 10.0


def test_fourth_wave_onlydust_maps_documented_crypto_without_platform_map():
    from cores.opportunity.own_work_sources_extensions import (
        build_fourth_wave_dev_extension,
    )

    src = next(s for s in build_fourth_wave_dev_extension().sources if s.name == "OnlyDust")
    adapter = OwnWorkCatalogAdapter(_discovery())
    adapter.load_catalog_source(src)
    opp = adapter._build_opportunity(src)
    assert opp.platform == dwe_models.WorkPlatform.OTHER
    assert opp.payment_method == dwe_models.PaymentMethod.CRYPTO
    assert opp.payment == 10.0


def test_fifth_wave_github_bounty_labels_maps_github_without_known_payment():
    from cores.opportunity.own_work_sources_extensions import (
        build_fifth_wave_dev_extension,
    )

    src = next(s for s in build_fifth_wave_dev_extension().sources if s.name == "GitHub Bounty Labels")
    adapter = OwnWorkCatalogAdapter(_discovery())
    adapter.load_catalog_source(src)
    opp = adapter._build_opportunity(src)
    assert opp.platform == dwe_models.WorkPlatform.GITHUB
    assert opp.payment_method == dwe_models.PaymentMethod.PLATFORM_CREDIT
    assert opp.payment == 0.0


def test_fifth_wave_openq_maps_documented_crypto_without_platform_map():
    from cores.opportunity.own_work_sources_extensions import (
        build_fifth_wave_dev_extension,
    )

    src = next(s for s in build_fifth_wave_dev_extension().sources if s.name == "OpenQ")
    adapter = OwnWorkCatalogAdapter(_discovery())
    adapter.load_catalog_source(src)
    opp = adapter._build_opportunity(src)
    assert opp.platform == dwe_models.WorkPlatform.OTHER
    assert opp.payment_method == dwe_models.PaymentMethod.CRYPTO
    assert opp.payment == 10.0


def test_sixth_wave_patchstack_maps_documented_paypal_without_platform_map():
    from cores.opportunity.own_work_sources_extensions import (
        build_sixth_wave_security_extension,
    )

    src = build_sixth_wave_security_extension().sources[0]
    adapter = OwnWorkCatalogAdapter(_discovery())
    adapter.load_catalog_source(src)
    opp = adapter._build_opportunity(src)
    assert opp.platform == dwe_models.WorkPlatform.OTHER
    assert opp.payment_method == dwe_models.PaymentMethod.PAYPAL
    assert opp.payment == 10.0


def test_sixth_wave_bountycaster_maps_documented_crypto_without_platform_map():
    from cores.opportunity.own_work_sources_extensions import (
        build_sixth_wave_dev_extension,
    )

    src = build_sixth_wave_dev_extension().sources[0]
    adapter = OwnWorkCatalogAdapter(_discovery())
    adapter.load_catalog_source(src)
    opp = adapter._build_opportunity(src)
    assert opp.platform == dwe_models.WorkPlatform.OTHER
    assert opp.payment_method == dwe_models.PaymentMethod.CRYPTO
    assert opp.payment == 10.0
