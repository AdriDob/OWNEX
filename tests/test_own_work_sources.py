"""Tests for the OWNEX-owned OwnWork source extension.

Owns a small curated extension of the global source database in
``cores.opportunity.own_work_sources`` and a documented payment-method map in
``cores.opportunity.source_payment_docs``.

This is owned by this session only. It does NOT modify the SSOT catalog in
``cores.opportunity.global_sources``.
"""

from __future__ import annotations

import pytest

from cores.opportunity.own_work_sources import OwnWorkSourceRegistry
from cores.opportunity.source_payment_docs import KNOWN_PAYMENT_METHODS


@pytest.mark.parametrize("source", OwnWorkSourceRegistry.get_all())
def test_own_work_source_no_interview(source):
    assert source.requires_interview is False, f"{source.name} must not require an interview in this owned block"


@pytest.mark.parametrize("source", OwnWorkSourceRegistry.get_all())
def test_own_work_source_no_professional_experience_required(source):
    assert source.requires_experience is False, f"{source.name} must not require professional experience in this block"


@pytest.mark.parametrize("source", OwnWorkSourceRegistry.get_all())
def test_own_work_source_no_portfolio_required(source):
    assert source.requires_portfolio is False, f"{source.name} must not require a portfolio in this owned block"


def test_own_work_source_counts():
    all_sources = OwnWorkSourceRegistry.get_all()
    dev_sources = OwnWorkSourceRegistry.get_development_work_sources()
    crypto_sources = OwnWorkSourceRegistry.get_crypto_dev_sources()

    assert len(all_sources) == len(dev_sources) + len(crypto_sources)
    assert len(dev_sources) == 13
    assert len(crypto_sources) == 5
    assert len(all_sources) == 18


def test_own_work_sources_only_curated_categories_with_payment_notes():
    """Every source in the owned block has a documented payment note where possible."""
    sources = OwnWorkSourceRegistry.get_all()
    names = {s.name for s in sources}
    doc_names = set(KNOWN_PAYMENT_METHODS.keys())

    # Every owned source should either be documented or explicitly "not_published"
    # in the payment docs, so the block is self-contained.
    missing_docs = names - doc_names
    assert not missing_docs, "Owned sources without any payment documentation entry: " + ", ".join(sorted(missing_docs))


def test_own_work_payment_docs_include_preferred_methods_only():
    """Documented methods stay within the preferred set for this block."""
    preferred = {"paypal", "bank_transfer", "crypto", "stablecoin", "not_published"}

    for name, doc in KNOWN_PAYMENT_METHODS.items():
        methods = set(doc.get("methods", []))
        assert methods.issubset(preferred), f"{name} lists non-preferred payment methods: " + ", ".join(sorted(methods - preferred))


def test_own_work_registry_count():
    assert OwnWorkSourceRegistry.count() == 18
