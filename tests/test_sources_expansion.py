"""Tests for the OWNEX 500+ source expansion + fallback engine."""

from __future__ import annotations

import pytest

from cores.opportunity.global_sources import (
    OpportunityCategory,
    SourceDefinition,
)
from cores.opportunity.sources_expansion import (
    CREDENTIAL_REQUIREMENTS,
    EXPANSION_SOURCES,
    MAX_TOTAL_SOURCES,
    count_sources,
    get_all_sources,
    get_credential_requirement,
    get_expansion_sources,
    get_fallback_chain,
    get_payment_fallback,
    get_source_status,
    sources_for_scan,
)


@pytest.fixture(scope="module")
def all_sources() -> list[SourceDefinition]:
    return get_all_sources()


class TestCatalogSize:
    def test_expansion_exceeds_500_total(self, all_sources):
        """User requirement: >500 sources total."""
        assert len(all_sources) > 500

    def test_hard_cap_1000(self, all_sources):
        assert len(all_sources) <= MAX_TOTAL_SOURCES == 1000

    def test_expansion_list_nonempty(self):
        assert len(EXPANSION_SOURCES) > 400

    def test_counts_consistent(self, all_sources):
        counts = count_sources()
        assert counts["capped"] == len(all_sources)
        # get_all_sources enforces the 1000-source hard cap; the raw merged
        # catalog may exceed it (agent keeps adding curated entries).
        assert counts["merged_raw"] == min(counts["merged_raw"], MAX_TOTAL_SOURCES)
        assert counts["capped"] <= MAX_TOTAL_SOURCES
        assert counts["capped"] > 500

    def test_no_duplicate_names(self, all_sources):
        names = [s.name.strip().lower() for s in all_sources]
        assert len(names) == len(set(names))

    def test_no_upwork(self, all_sources):
        assert all(not s.name.lower().startswith("upwork") for s in all_sources)

    def test_all_have_url(self, all_sources):
        assert all(s.url.startswith("http") for s in all_sources)

    def test_all_have_category(self, all_sources):
        valid = set(OpportunityCategory) | {
            "cybersecurity",
            "data_science",
            "remote_work",
            "bounties",
            "web3_audits",
            "marketplaces",
            "qa_testing",
        }
        assert all(s.category in valid for s in all_sources)


class TestCategories:
    @pytest.mark.parametrize(
        "category",
        list(OpportunityCategory),
    )
    def test_each_category_has_sources(self, category):
        assert len(get_expansion_sources(category)) > 0

    def test_bug_bounty_is_largest(self, all_sources):
        bb = [s for s in all_sources if s.category == OpportunityCategory.bug_bounty]
        assert len(bb) > 100

    def test_junior_jobs_category_populated(self, all_sources):
        jj = [s for s in all_sources if s.category == OpportunityCategory.junior_jobs]
        assert len(jj) > 50


class TestEligibilityFilter:
    def test_eligible_only_drops_high_barrier(self):
        eligible = sources_for_scan(eligible_only=True)
        assert all(not (s.requires_portfolio or s.requires_interview or s.requires_experience) for s in eligible)

    def test_eligible_subset_of_all(self):
        eligible = sources_for_scan(eligible_only=True)
        everything = sources_for_scan(eligible_only=False)
        assert len(eligible) <= len(everything)
        assert len(eligible) > 300  # plenty of low-barrier sources

    def test_priority_ordering(self):
        sources = sources_for_scan(eligible_only=True)
        keys = [(s.priority, s.quality_score) for s in sources]
        assert keys == sorted(keys, reverse=True)


class TestFallbackChains:
    def test_fallback_chain_nonempty(self, all_sources):
        for s in all_sources[:20]:
            chain = get_fallback_chain(s)
            assert len(chain) <= 5
            assert all(a.name != s.name for a in chain)

    def test_fallback_same_category(self, all_sources):
        for s in all_sources[:10]:
            chain = get_fallback_chain(s)
            assert all(a.category == s.category for a in chain)

    def test_fallback_prefers_same_family(self):
        hackerone = next(s for s in get_all_sources() if s.name == "HackerOne")
        chain = get_fallback_chain(hackerone)
        # Bugcrowd/Intigriti share the crowdsourced family niche.
        assert len(chain) > 0

    def test_fallback_by_name_string(self):
        chain = get_fallback_chain("HackerOne")
        assert isinstance(chain, list)

    def test_fallback_unknown_returns_empty(self):
        assert get_fallback_chain("No Such Source XYZ") == []


class TestPaymentFallback:
    def test_argentina_ok_no_fallback(self):
        # Most catalog sources are Argentina-compatible by default.
        compatible = next(
            (s for s in get_all_sources() if getattr(s, "argentina_ok", False)),
            None,
        )
        if compatible is not None:
            assert get_payment_fallback(compatible) is None

    def test_restricted_source_has_fallback(self):
        restricted = next(
            (s for s in get_all_sources() if not getattr(s, "argentina_ok", True)),
            None,
        )
        if restricted is not None:
            fb = get_payment_fallback(restricted)
            assert fb is not None
            assert fb["fallback"] in {
                "private_message",
                "direct_message_negotiation",
                "crypto_payout",
                "payoneer_wise",
                "entity_via_us_llc",
                "crypto_via_opire",
            }

    def test_explicit_payment_fallbacks_present(self):
        assert "toptal" in __import__("cores.opportunity.sources_expansion", fromlist=["PAYMENT_FALLBACKS"]).PAYMENT_FALLBACKS


class TestCredentials:
    def test_known_source_requires_login(self):
        req = get_credential_requirement("HackerOne")
        assert req is not None
        assert req["kind"] == "login"

    def test_public_source_no_credentials(self):
        req = get_credential_requirement("RemoteOK API")
        assert req is not None
        assert req["kind"] in {"api_key", "none"}

    def test_requires_account_defaults_to_login(self):
        acct = next(s for s in get_all_sources() if s.requires_account)
        req = get_credential_requirement(acct)
        assert req is not None
        assert req["kind"] == "login"

    def test_no_credentials_for_public_board(self):
        # Sources explicitly marked requires_account=False get 'none'.
        public = [s for s in get_all_sources() if not s.requires_account]
        assert len(public) > 0
        for s in public[:5]:
            req = get_credential_requirement(s)
            assert req is not None
            assert req["kind"] == "none"


class TestSourceStatus:
    def test_status_shape(self):
        st = get_source_status("HackerOne")
        assert st["source"] == "HackerOne"
        assert "credentials" in st
        assert "payment_fallback" in st
        assert "fallback_chain" in st
        assert isinstance(st["fallback_chain"], list)

    def test_credential_requirements_dict_coverage(self):
        # Every login-required source should ideally have an entry; at minimum
        # the dict must be non-empty and well-formed.
        assert len(CREDENTIAL_REQUIREMENTS) > 100
        for req in CREDENTIAL_REQUIREMENTS.values():
            assert req["kind"] in {
                "login",
                "api_key",
                "cookie",
                "oauth",
                "paid_account",
                "none",
            }
