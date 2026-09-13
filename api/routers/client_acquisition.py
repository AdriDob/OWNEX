"""Client Acquisition API — Adriel Webs funnel (lead -> proposal -> project -> MRR).

Free-tier funnel: landing/portfolio/github-page gratis como prueba de valor;
el ingreso está en mantenimiento + hosting + SEO + ads (MRR honesto).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.client_acquisition import (
    LeadSource,
    LeadStage,
    ProjectStage,
    ProjectType,
    get_client_acquisition_engine,
)

router = APIRouter(prefix="/api/client-acquisition", tags=["client-acquisition"])


class LeadIn(BaseModel):
    name: str
    contact: str = ""
    source: LeadSource = LeadSource.OTHER
    business_type: str = ""
    has_website: bool = False


class ProposalIn(BaseModel):
    project_type: ProjectType = ProjectType.LANDING
    pages: int = 1
    features: list[str] = Field(default_factory=list)


class ContractIn(BaseModel):
    monthly_usd: float = 25.0
    includes_hosting: bool = True
    includes_seo: bool = False
    includes_content: bool = False


@router.get("/status")
async def acquisition_status() -> dict[str, Any]:
    return dict(get_client_acquisition_engine().get_status())


@router.get("/upsell-catalog")
async def acquisition_upsells() -> dict[str, Any]:
    return {"items": get_client_acquisition_engine().upsell_catalog()}


@router.post("/leads/capture")
async def acquisition_capture_lead(payload: LeadIn) -> dict[str, Any]:
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="name is required")
    lead = get_client_acquisition_engine().capture_lead(
        name=payload.name,
        contact=payload.contact,
        source=payload.source,
        business_type=payload.business_type,
        has_website=payload.has_website,
    )
    return {"success": True, "id": lead.id, "stage": lead.stage.value}


@router.get("/leads")
async def acquisition_list_leads(stage: str | None = None) -> dict[str, Any]:
    engine = get_client_acquisition_engine()
    stage_enum = None
    if stage:
        try:
            stage_enum = LeadStage(stage)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid stage: {stage}") from None
    leads = engine.list_leads(stage=stage_enum)
    return {
        "total": len(leads),
        "leads": [
            {
                "id": lead.id,
                "name": lead.name,
                "source": lead.source.value,
                "business_type": lead.business_type,
                "has_website": lead.has_website,
                "stage": lead.stage.value,
            }
            for lead in leads[:100]
        ],
    }


@router.post("/leads/{lead_id}/advance")
async def acquisition_advance_lead(lead_id: str, stage: str) -> dict[str, Any]:
    try:
        stage_enum = LeadStage(stage)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid stage: {stage}") from None
    lead = get_client_acquisition_engine().advance_lead(lead_id, stage_enum)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True, "id": lead.id, "stage": lead.stage.value}


@router.post("/leads/{lead_id}/proposals/generate")
async def acquisition_generate_proposal(lead_id: str, payload: ProposalIn) -> dict[str, Any]:
    proposal = get_client_acquisition_engine().generate_proposal(
        lead_id, project_type=payload.project_type, pages=payload.pages, features=payload.features
    )
    if not proposal:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {
        "success": True,
        "id": proposal.id,
        "price_usd": proposal.price_usd,
        "free_tier": proposal.free_tier,
        "timeline_days": proposal.timeline_days,
        "body_md": proposal.body_md,
    }


@router.post("/leads/{lead_id}/projects/start")
async def acquisition_start_project(lead_id: str, proposal_id: str) -> dict[str, Any]:
    project = get_client_acquisition_engine().start_project(lead_id, proposal_id)
    if not project:
        raise HTTPException(status_code=404, detail="Lead or proposal not found")
    return {"success": True, "id": project.id, "stage": project.stage.value}


@router.post("/projects/{project_id}/advance")
async def acquisition_advance_project(project_id: str, stage: str) -> dict[str, Any]:
    try:
        stage_enum = ProjectStage(stage)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid stage: {stage}") from None
    project = get_client_acquisition_engine().advance_project(project_id, stage_enum)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True, "id": project.id, "stage": project.stage.value}


@router.get("/projects")
async def acquisition_list_projects() -> dict[str, Any]:
    engine = get_client_acquisition_engine()
    projects = engine.list_projects()
    return {
        "total": len(projects),
        "mrr_usd": engine.monthly_recurring(),
        "projects": [
            {
                "id": p.id,
                "lead_id": p.lead_id,
                "project_type": p.project_type.value,
                "stage": p.stage.value,
                "prod_url": p.prod_url,
            }
            for p in projects[:100]
        ],
    }


@router.post("/projects/{project_id}/maintenance")
async def acquisition_create_contract(project_id: str, payload: ContractIn) -> dict[str, Any]:
    contract = get_client_acquisition_engine().create_contract(
        project_id,
        monthly_usd=payload.monthly_usd,
        includes_hosting=payload.includes_hosting,
        includes_seo=payload.includes_seo,
        includes_content=payload.includes_content,
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True, "id": contract.id, "monthly_usd": contract.monthly_usd}
