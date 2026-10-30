"""Tests for the Finding Marketplace (cores/marketplace/finding_market.py)."""

from __future__ import annotations

import pytest

from cores.marketplace.finding_market import (
    FindingListing,
    FindingMarketplace,
    FindingOffer,
    FindingType,
    ListingStatus,
    TransferType,
    get_finding_marketplace,
)


def _listing(**kwargs):
    defaults = dict(
        seller_id="s1",
        title="Listing",
        finding_type=FindingType.VULNERABILITY,
        transfer_type=TransferType.FULL_TRANSFER,
        description="d",
        severity="high",
        asking_price=500.0,
    )
    defaults.update(kwargs)
    return FindingListing(**defaults)


def _offer(**kwargs):
    defaults = dict(buyer_id="b1", offered_price=400.0)
    defaults.update(kwargs)
    return FindingOffer(**defaults)


@pytest.fixture()
def market(tmp_path, monkeypatch):
    m = FindingMarketplace(data_dir=tmp_path)
    monkeypatch.setattr("cores.marketplace.finding_market._finding_marketplace", m)
    return m


def test_create_listing(market):
    listing = market.create_listing(_listing())
    assert listing.id.startswith("listing_")
    assert listing.status == ListingStatus.DRAFT
    assert market.get_listing(listing.id) is not None


def test_publish_and_filter(market):
    l1 = market.create_listing(
        _listing(title="A", finding_type=FindingType.POC, transfer_type=TransferType.LICENSE, asking_price=100.0)
    )
    market.publish_listing(l1.id, "s1")
    assert len(market.get_listings(status=ListingStatus.ACTIVE)) == 1
    assert len(market.get_listings(status=ListingStatus.DRAFT)) == 0


def test_offer_flow(market):
    listing = market.create_listing(_listing(title="B"))
    market.publish_listing(listing.id, "s1")
    offer = market.create_offer(_offer(listing_id=listing.id))
    assert offer.id.startswith("offer_")
    accepted = market.accept_offer(offer.id, "s1")
    assert accepted.status == "accepted"
    assert market.get_listing(listing.id).status == ListingStatus.NEGOTIATING


def test_reject_offer(market):
    listing = market.create_listing(_listing(title="C", transfer_type=TransferType.LICENSE, asking_price=50.0))
    market.publish_listing(listing.id, "s1")
    offer = market.create_offer(_offer(listing_id=listing.id, offered_price=30.0))
    assert market.reject_offer(offer.id, "s1").status == "rejected"


def test_counter_offer(market):
    listing = market.create_listing(_listing(title="D", transfer_type=TransferType.COLLABORATION, asking_price=200.0))
    market.publish_listing(listing.id, "s1")
    offer = market.create_offer(_offer(listing_id=listing.id, offered_price=150.0))
    countered = market.counter_offer(offer.id, "s1", 180.0)
    assert countered.status == "countered"
    assert countered.counter_price == 180.0


def test_complete_transaction(market):
    listing = market.create_listing(_listing(title="E", severity="critical", asking_price=1000.0))
    market.publish_listing(listing.id, "s1")
    offer = market.create_offer(_offer(listing_id=listing.id, offered_price=900.0))
    market.accept_offer(offer.id, "s1")
    txn = market.complete_transaction(listing.id, offer.id, "s1", "b1", 900.0)
    assert txn.id.startswith("txn_")
    assert market.get_listing(listing.id).status == ListingStatus.COMPLETED
    assert market.get_reputation("s1")["successful"] >= 1


def test_cannot_offer_on_own_listing(market):
    listing = market.create_listing(_listing(seller_id="s1", title="F", asking_price=10.0))
    with pytest.raises(ValueError):
        market.create_offer(_offer(listing_id=listing.id, buyer_id="s1", offered_price=10.0))


def test_search_listings(market):
    listing = market.create_listing(_listing(title="GraphQL introspection leak", asking_price=800.0))
    market.publish_listing(listing.id, "s1")
    results = market.search_listings("graphql")
    assert len(results) == 1
    assert results[0].title == "GraphQL introspection leak"
    assert len(market.search_listings("nosuchthingxyz")) == 0


def test_reputation_persists(market):
    rep = market.get_reputation("unknown_user")
    assert rep["successful"] == 0


def test_singleton():
    assert get_finding_marketplace() is get_finding_marketplace()
