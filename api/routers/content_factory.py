"""Content Factory API — visibility over MoneyPrinterTurbo pipeline + Whop clip-pack tracking.

Generation/publishing run on the factory's own APScheduler
(cores.content_factory.scheduler.get_content_factory_jobs); the /status and
/jobs endpoints only expose state so Mission Control can see them.
No manual triggers for generation here: video generation is heavy and stays
on schedule or behind explicit Human Gate flows.

The /whop/* endpoints track human clip-pack actions (create → video →
posted → submitted → paid). Posting and submitting are human clicks;
nothing here publishes automatically or touches external APIs.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/content-factory", tags=["content-factory"])


@router.get("/status")
async def content_factory_status() -> dict[str, Any]:
    """MPT health + material-key state + schedule overview (never raises)."""
    health: dict[str, Any] = {"healthy": False, "reason": "unknown"}
    try:
        from cores.content_factory.scheduler import run_health_check

        try:
            health = await asyncio.wait_for(run_health_check(), timeout=35.0)
        except TimeoutError:
            health = {"healthy": False, "reason": "health_check_timeout"}
    except Exception as exc:
        health = {"healthy": False, "reason": f"check_failed: {type(exc).__name__}"}
    try:
        from cores.setup.checklist import _detect_mpt_material_key

        material = _detect_mpt_material_key()
    except Exception:
        material = {"configured": False, "reason": "detector_unavailable"}
    return {"mpt": health, "material_key": material}


@router.get("/jobs")
async def content_factory_jobs() -> dict[str, Any]:
    """Scheduled factory jobs (generate/publish/analytics/optimize/health)."""
    try:
        from cores.content_factory.scheduler import get_content_factory_jobs

        jobs = []
        for job in get_content_factory_jobs():
            trigger = job.get("trigger")
            jobs.append(
                {
                    "job_id": job.get("job_id", ""),
                    "name": job.get("name", ""),
                    "handler": job.get("handler", ""),
                    "schedule": str(trigger) if trigger is not None else "unknown",
                }
            )
        return {"total": len(jobs), "jobs": jobs}
    except Exception as exc:
        return {"total": 0, "jobs": [], "error": f"jobs_unavailable: {type(exc).__name__}"}


# ── Whop clip-pack tracking (human actions only, never auto-posts) ──


def _clip_store():  # type: ignore[no-untyped-def]
    from cores.content_factory.whop import ClipPackStore

    return ClipPackStore()  # data-dir aware per request (OWNEX_DATA_DIR), test-safe


class EvaluateIn(BaseModel):
    rate_per_1k_usd: float | None = None
    cap_usd: float | None = None
    minimum_usd: float | None = None
    budget_remaining_usd: float | None = None
    entry_fee_usd: float = 0.0
    expected_views: float | None = None


class PackIn(BaseModel):
    campaign_name: str = Field(min_length=1, max_length=200)
    campaign_type: str = "ugc"
    rate_per_1k_usd: float = 0.0
    cap_usd: float = 0.0
    brief_url: str = ""


class VideoIn(BaseModel):
    video_path: str = Field(min_length=1)


class PostedIn(BaseModel):
    post_url: str = Field(min_length=1)


class PaidIn(BaseModel):
    amount_usd: float


class RejectedIn(BaseModel):
    reason: str = Field(min_length=1)


@router.post("/whop/evaluate")
async def whop_evaluate(payload: EvaluateIn) -> dict[str, Any]:
    """Pure brief math: VIABLE/SKIP + reasons + net hint (None = UNKNOWN)."""
    from cores.content_factory.whop import evaluate_campaign

    return evaluate_campaign(
        rate_per_1k_usd=payload.rate_per_1k_usd,
        cap_usd=payload.cap_usd,
        minimum_usd=payload.minimum_usd,
        budget_remaining_usd=payload.budget_remaining_usd,
        entry_fee_usd=payload.entry_fee_usd,
        expected_views=payload.expected_views,
    )


@router.post("/whop/packs", status_code=201)
async def whop_create_pack(payload: PackIn) -> dict[str, Any]:
    """Open a clip-pack for a campaign (status: building)."""
    try:
        pack = _clip_store().create(
            campaign_name=payload.campaign_name,
            campaign_type=payload.campaign_type,
            rate_per_1k_usd=payload.rate_per_1k_usd,
            cap_usd=payload.cap_usd,
            brief_url=payload.brief_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return pack.to_dict()


@router.get("/whop/packs")
async def whop_list_packs() -> dict[str, Any]:
    """Clip-packs + paid totals (PAID acreditado only)."""
    store = _clip_store()
    return {**store.summary(), "packs": [p.to_dict() for p in store.list()]}


def _pack_or_404(pack_id: str):  # type: ignore[no-untyped-def]
    pack = _clip_store().get(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="pack desconocido")
    return pack


@router.post("/whop/packs/{pack_id}/video")
async def whop_attach_video(pack_id: str, payload: VideoIn) -> dict[str, Any]:
    """Attach the produced video (MPT output or manual edit) → ready."""
    _pack_or_404(pack_id)
    ok, reason = _clip_store().attach_video(pack_id, payload.video_path)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)
    return _clip_store().get(pack_id).to_dict()  # type: ignore[union-attr]


@router.post("/whop/packs/{pack_id}/posted")
async def whop_mark_posted(pack_id: str, payload: PostedIn) -> dict[str, Any]:
    """Record the human post URL (the posting itself is a human click)."""
    _pack_or_404(pack_id)
    ok, reason = _clip_store().mark_posted(pack_id, payload.post_url)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)
    return _clip_store().get(pack_id).to_dict()  # type: ignore[union-attr]


@router.post("/whop/packs/{pack_id}/submitted")
async def whop_mark_submitted(pack_id: str) -> dict[str, Any]:
    """Record submission to the campaign (human submits the URL on Whop)."""
    _pack_or_404(pack_id)
    ok, reason = _clip_store().mark_submitted(pack_id)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)
    return _clip_store().get(pack_id).to_dict()  # type: ignore[union-attr]


@router.post("/whop/packs/{pack_id}/paid")
async def whop_record_paid(pack_id: str, payload: PaidIn) -> dict[str, Any]:
    """Record accredited payout (monto > 0; aprobación sola no es cobro)."""
    _pack_or_404(pack_id)
    ok, reason = _clip_store().record_paid(pack_id, payload.amount_usd)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)
    return _clip_store().get(pack_id).to_dict()  # type: ignore[union-attr]


@router.post("/whop/packs/{pack_id}/rejected")
async def whop_mark_rejected(pack_id: str, payload: RejectedIn) -> dict[str, Any]:
    """Record brand rejection with reason (evidence for the one appeal)."""
    _pack_or_404(pack_id)
    ok, reason = _clip_store().mark_rejected(pack_id, payload.reason)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)
    return _clip_store().get(pack_id).to_dict()  # type: ignore[union-attr]


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    campaign_type: str = "ugc"
    rate_per_1k_usd: float = 0.0
    cap_usd: float = 0.0
    minimum_usd: float | None = None
    budget_remaining_usd: float | None = None
    entry_fee_usd: float = 0.0
    language: str = "en"
    brief_url: str = ""
    voice_name: str = ""
    verified: bool = False


@router.post("/whop/campaigns", status_code=201)
async def whop_register_campaign(payload: CampaignIn) -> dict[str, Any]:
    """Register a human-pasted brief (numbers confirmed in the Whop app).

    Only verified + free + ES/EN + VIABLE briefs auto-build. Unverified briefs
    are stored and ranked as excluded — visible, never executed.
    """
    store = _clip_store()
    brief, verdict = store.register_campaign(
        name=payload.name,
        campaign_type=payload.campaign_type,
        rate_per_1k_usd=payload.rate_per_1k_usd,
        cap_usd=payload.cap_usd,
        minimum_usd=payload.minimum_usd,
        budget_remaining_usd=payload.budget_remaining_usd,
        entry_fee_usd=payload.entry_fee_usd,
        language=payload.language,
        brief_url=payload.brief_url,
        voice_name=payload.voice_name,
        verified=payload.verified,
    )
    if brief is None:
        raise HTTPException(status_code=422, detail="; ".join(verdict.get("reasons", ["brief inválido"])))
    return {"brief": brief.to_dict(), "verdict": verdict}


@router.get("/whop/campaigns")
async def whop_ranked_campaigns(languages: str = "es,en") -> dict[str, Any]:
    """Best free verified briefs first (rate desc, cap desc)."""
    langs = tuple(part.strip().lower() for part in languages.split(",") if part.strip()) or ("es", "en")
    ranked = _clip_store().rank_campaigns(languages=langs)
    return {"total": len(ranked), "campaigns": ranked}


@router.post("/whop/auto-build")
async def whop_auto_build() -> dict[str, Any]:
    """Manual trigger of the auto-build: rank → packs → MPT video → ready.

    Same function the 06:30 job runs. Stops at ready; posting stays human.
    """
    from cores.content_factory.whop import auto_build_packs

    return await auto_build_packs(_clip_store())
