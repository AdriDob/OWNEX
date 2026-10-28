"""Tests for the Client Acquisition pipeline (Adriel Webs funnel)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.client_acquisition import router
from cores.client_acquisition import (
    ClientAcquisitionEngine,
    LeadSource,
    LeadStage,
    ProjectStage,
    ProjectType,
)

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_free_tier_landing_is_zero() -> None:
    engine = ClientAcquisitionEngine()
    lead = engine.capture_lead("Panadería Sur", source=LeadSource.INSTAGRAM, has_website=False)
    proposal = engine.generate_proposal(lead.id, project_type=ProjectType.LANDING, pages=1)
    assert proposal is not None
    assert proposal.free_tier is True
    assert proposal.price_usd == 0.0


def test_paid_corporate_prices_extras() -> None:
    engine = ClientAcquisitionEngine()
    lead = engine.capture_lead("Taller CABA", source=LeadSource.WHATSAPP)
    proposal = engine.generate_proposal(
        lead.id, project_type=ProjectType.CORPORATE_WEB, pages=5, features=["turnos", "whatsapp"]
    )
    assert proposal is not None
    assert proposal.free_tier is False
    assert proposal.price_usd > 150.0
    assert proposal.timeline_days == 21


def test_lead_funnel_and_project_flow() -> None:
    engine = ClientAcquisitionEngine()
    lead = engine.capture_lead("Kiosco Zona Sur", source=LeadSource.FACEBOOK)
    assert engine.funnel()[LeadStage.NEW.value] >= 1
    proposal = engine.generate_proposal(lead.id, project_type=ProjectType.GITHUB_PAGE)
    assert proposal is not None
    project = engine.start_project(lead.id, proposal.id)
    assert project is not None
    assert engine.advance_project(project.id, ProjectStage.DELIVERED) is not None
    contract = engine.create_contract(project.id, monthly_usd=25.0)
    assert contract is not None
    assert engine.monthly_recurring() == 25.0


def test_upsell_catalog_has_five_items() -> None:
    engine = ClientAcquisitionEngine()
    assert len(engine.upsell_catalog()) == 5


class TestClientAcquisitionApi:
    def test_status(self) -> None:
        resp = client.get("/api/client-acquisition/status")
        assert resp.status_code == 200
        assert "mrr_usd" in resp.json()

    def test_capture_and_propose_flow(self) -> None:
        lead_resp = client.post(
            "/api/client-acquisition/leads/capture",
            json={"name": "Verdulería Test", "source": "whatsapp", "has_website": False},
        )
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["id"]
        prop_resp = client.post(
            f"/api/client-acquisition/leads/{lead_id}/proposals/generate",
            json={"project_type": "landing", "pages": 1, "features": []},
        )
        assert prop_resp.status_code == 200
        assert prop_resp.json()["free_tier"] is True

    def test_invalid_stage_is_422(self) -> None:
        resp = client.get("/api/client-acquisition/leads", params={"stage": "nope"})
        assert resp.status_code == 422

    def test_empty_name_is_422(self) -> None:
        resp = client.post("/api/client-acquisition/leads/capture", json={"name": "  "})
        assert resp.status_code == 422
