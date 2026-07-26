"""Financial Hub API — payout intelligence, KYC, route optimization endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.financial_hub import (
    DocumentsChecklist,
    EmergencyRoutes,
    FeesCalculator,
    KYCManager,
    PayoutAdvisor,
    PlatformRegistry,
    RouteOptimizer,
    TaxNotes,
    VerificationTracker,
)

router = APIRouter(prefix="/api/financial-hub", tags=["financial_hub"])

_advisor = PayoutAdvisor()
_kyc = KYCManager()
_routes = RouteOptimizer()
_fees = FeesCalculator()
_registry = PlatformRegistry()
_verification = VerificationTracker()
_docs_checklist = DocumentsChecklist()
_emergency = EmergencyRoutes()
_tax = TaxNotes()


# ── Payout Advisor ────────────────────────────────────────────────────


@router.get("/payout-advisor/platforms")
def list_payout_platforms():
    return _advisor.list_platforms()


@router.get("/payout-advisor/best-routes")
def best_routes_for_argentina():
    return _advisor.best_routes_for_argentina()


@router.get("/payout-advisor/platforms/{platform_id}")
def get_payout_platform(platform_id: str):
    info = _advisor.get_platform_info(platform_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")
    return info


@router.post("/payout-advisor/simulate")
def simulate_payout(amount_usd: float, source_platform: str, preferred_method: str | None = None):
    if amount_usd <= 0:
        raise HTTPException(status_code=400, detail="amount_usd must be positive")
    result = _advisor.simulate_payout(
        amount_usd=amount_usd,
        source_platform=source_platform,
        preferred_method=preferred_method,
    )
    return result.to_dict()


# ── KYC Manager ───────────────────────────────────────────────────────
# NOTE: static paths (summary) must be BEFORE parameterized paths ({platform})


@router.get("/kyc")
def list_kyc():
    return _kyc.get_all()


@router.get("/kyc/summary")
def kyc_summary():
    return _kyc.get_summary()


@router.get("/kyc/{platform}")
def get_kyc(platform: str):
    record = _kyc.get(platform)
    if record is None:
        raise HTTPException(status_code=404, detail=f"KYC record for '{platform}' not found")
    return record


@router.post("/kyc/{platform}")
def upsert_kyc(
    platform: str,
    status: str | None = None,
    documents_submitted: list[str] | None = None,
    notes: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
):
    try:
        return _kyc.upsert(
            platform=platform,
            status=status,
            documents_submitted=documents_submitted,
            notes=notes,
            started_at=started_at,
            completed_at=completed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ── Route Optimizer ────────────────────────────────────────────────────
# NOTE: static path (optimize) must be BEFORE parameterized path ({route_id})


@router.get("/routes")
def list_routes(include_emergency: bool = False):
    return _routes.list_routes(include_emergency=include_emergency)


@router.get("/routes/optimize")
def optimize_route(amount_usd: float, source_platform: str = "hackerone"):
    if amount_usd <= 0:
        raise HTTPException(status_code=400, detail="amount_usd must be positive")
    return _routes.calculate_optimal(amount_usd=amount_usd, source_platform=source_platform)


@router.get("/routes/{route_id}")
def get_route(route_id: int):
    route = _routes.get_route(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail=f"Route #{route_id} not found")
    return route


# ── Fees Calculator ────────────────────────────────────────────────────


@router.post("/fees/estimate")
def estimate_fees(amount_usd: float, fee_percent: float = 0.0, fee_fixed: float = 0.0, method_type: str = "wallet"):
    if amount_usd <= 0:
        raise HTTPException(status_code=400, detail="amount_usd must be positive")
    return _fees.estimate(amount_usd=amount_usd, method_type=method_type, fee_percent=fee_percent, fee_fixed=fee_fixed)


@router.post("/fees/compare")
def compare_methods(amount_usd: float, methods: list[dict[str, Any]]):
    if amount_usd <= 0:
        raise HTTPException(status_code=400, detail="amount_usd must be positive")
    return _fees.compare_methods(amount_usd=amount_usd, methods=methods)


# ── Platform Registry ────────────────────────────────────────────────


@router.get("/platforms")
def list_platforms():
    return _registry.list_platforms()


@router.post("/platforms/compare")
def compare_platforms(platform_ids: list[str]):
    return _registry.compare(platform_ids)


@router.get("/platforms/argentina/ranked")
def argentina_ranked():
    return _registry.argentina_ranked()


@router.get("/platforms/{platform_id}")
def get_platform(platform_id: str):
    info = _registry.get_platform(platform_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Platform '{platform_id}' not found")
    return info


# ── Verification Tracker ──────────────────────────────────────────────


@router.get("/verifications/progress")
def verification_progress():
    return _verification.get_overall_progress()


@router.get("/verifications/pending")
def pending_verifications():
    return _verification.get_pending_verifications()


# ── Documents Checklist ───────────────────────────────────────────────
# NOTE: static path (summary) must be BEFORE parameterized path ({doc_id})


@router.get("/documents")
def list_documents():
    return _docs_checklist.list_all()


@router.get("/documents/summary")
def documents_summary():
    return _docs_checklist.get_summary()


@router.get("/documents/{doc_id}")
def get_document(doc_id: int):
    doc = _docs_checklist.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document #{doc_id} not found")
    return doc


@router.post("/documents/{doc_id}/complete")
def complete_document(doc_id: int):
    doc = _docs_checklist.mark_completed(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document #{doc_id} not found")
    return doc


@router.post("/documents/{doc_id}/incomplete")
def incomplete_document(doc_id: int):
    doc = _docs_checklist.mark_incomplete(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document #{doc_id} not found")
    return doc


# ── Emergency Routes ───────────────────────────────────────────────────
# NOTE: static paths (fallback, quickest) must be BEFORE parameterized path ({route_id})


@router.get("/emergency-routes")
def list_emergency_routes():
    return _emergency.list_all()


@router.get("/emergency-routes/fallback")
def primary_fallback():
    route = _emergency.get_primary_fallback()
    if route is None:
        raise HTTPException(status_code=404, detail="No emergency fallback route configured")
    return route


@router.get("/emergency-routes/quickest")
def quickest_emergency():
    route = _emergency.get_quickest_emergency()
    if route is None:
        raise HTTPException(status_code=404, detail="No emergency routes configured")
    return route


@router.post("/emergency-routes/{route_id}/enable")
def enable_emergency_route(route_id: int):
    route = _emergency.enable(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail=f"Route #{route_id} not found")
    return route


@router.post("/emergency-routes/{route_id}/disable")
def disable_emergency_route(route_id: int):
    route = _emergency.disable(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail=f"Route #{route_id} not found")
    return route


# ── Tax Notes ──────────────────────────────────────────────────────────
# NOTE: static paths (by-category, for-platform) must be BEFORE parameterized path ({record_id})


@router.get("/tax-notes")
def list_tax_notes(country: str = "AR"):
    return _tax.list_all(country=country)


@router.get("/tax-notes/by-category")
def tax_notes_by_category(country: str = "AR"):
    return _tax.by_category(country=country)


@router.get("/tax-notes/for-platform/{platform_id}")
def tax_notes_for_platform(platform_id: str, country: str = "AR"):
    return _tax.for_platform(platform_id=platform_id, country=country)


@router.get("/tax-notes/{record_id}")
def get_tax_note(record_id: int):
    note = _tax.get(record_id)
    if note is None:
        raise HTTPException(status_code=404, detail=f"Tax note #{record_id} not found")
    return note
