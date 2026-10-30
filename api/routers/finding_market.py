"""Finding Marketplace API Router — Sell/transfer validated findings."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from cores.marketplace.finding_market import (
    FindingType,
    ListingStatus,
    TransferType,
    accept_offer,
    complete_transaction,
    counter_offer,
    create_listing,
    get_listing,
    get_user_reputation,
    list_listings,
    make_offer,
    reject_offer,
    search_findings,
)

logger = logging.getLogger("ownex.api.finding_market")

router = APIRouter(prefix="/api/marketplace", tags=["finding-marketplace"])


@router.post("/listings")
async def api_create_listing(
    seller_id: str,
    title: str,
    finding_type: FindingType,
    transfer_type: TransferType,
    description: str,
    severity: str,
    asking_price: float,
    platform: str | None = None,
    program: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new finding listing."""
    listing = create_listing(
        seller_id=seller_id,
        title=title,
        finding_type=finding_type,
        transfer_type=transfer_type,
        description=description,
        severity=severity,
        asking_price=asking_price,
        platform=platform,
        program=program,
        tags=tags,
    )
    return listing.__dict__


@router.get("/listings")
async def api_list_listings(
    seller_id: str | None = Query(None),
    status: ListingStatus | None = Query(None),
    finding_type: FindingType | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """List finding listings with optional filters."""
    listings = list_listings(seller_id, status, finding_type, min_price, max_price, limit)
    return {"count": len(listings), "listings": [item.__dict__ for item in listings]}


@router.get("/listings/{listing_id}")
async def api_get_listing(listing_id: str) -> dict[str, Any]:
    """Get a listing by ID."""
    listing = get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing.__dict__


@router.get("/search")
async def api_search_findings(
    query: str = Query(..., min_length=1),
    finding_type: FindingType | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    """Search active findings."""
    results = search_findings(query, finding_type, min_price, max_price, severity, limit)
    return {"count": len(results), "results": [r.__dict__ for r in results]}


@router.post("/listings/{listing_id}/offers")
async def api_make_offer(
    listing_id: str,
    buyer_id: str,
    offered_price: float,
    transfer_type: TransferType = TransferType.FULL_TRANSFER,
    message: str = "",
) -> dict[str, Any]:
    """Make an offer on a listing."""
    try:
        offer = make_offer(listing_id, buyer_id, offered_price, transfer_type, message)
        return offer.__dict__
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/offers/{offer_id}/accept")
async def api_accept_offer(offer_id: str, seller_id: str) -> dict[str, Any]:
    """Accept an offer."""
    try:
        offer = accept_offer(offer_id, seller_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")
        return offer.__dict__
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None


@router.post("/offers/{offer_id}/reject")
async def api_reject_offer(offer_id: str, seller_id: str) -> dict[str, Any]:
    """Reject an offer."""
    try:
        offer = reject_offer(offer_id, seller_id)
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")
        return offer.__dict__
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None


@router.post("/offers/{offer_id}/counter")
async def api_counter_offer(offer_id: str, seller_id: str, counter_price: float) -> dict[str, Any]:
    """Counter an offer."""
    try:
        offer = counter_offer(offer_id, seller_id, counter_price)
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")
        return offer.__dict__
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None


@router.post("/transactions")
async def api_complete_transaction(
    listing_id: str,
    offer_id: str,
    seller_id: str,
    buyer_id: str,
    final_price: float,
    escrow_id: str | None = None,
) -> dict[str, Any]:
    """Complete a finding transaction."""
    try:
        txn = complete_transaction(listing_id, offer_id, seller_id, buyer_id, final_price, escrow_id)
        return txn.__dict__
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/reputation/{user_id}")
async def api_get_reputation(user_id: str) -> dict[str, Any]:
    """Get user marketplace reputation."""
    return get_user_reputation(user_id)
