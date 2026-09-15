"""Client Acquisition — Adriel Webs pipeline (lead -> proposal -> project -> maintenance).

Free-tier funnel: landing/portfolio gratis como prueba de valor; el ingreso
recurrente viene de mantenimiento + hosting + SEO + ads. Todo determinista,
sin red: la captura multicanal entra por API/webhook y aquí se ordena.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

logger = logging.getLogger("ownex.client_acquisition")


class LeadSource(StrEnum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    WHATSAPP = "whatsapp"
    WEBSITE_FORM = "website_form"
    REFERRAL = "referral"
    WALK_IN = "walk_in"
    DIRECTORY_SCRAPE = "directory_scrape"
    OTHER = "other"


class LeadStage(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    WON = "won"
    LOST = "lost"


class ProjectType(StrEnum):
    LANDING = "landing"
    CORPORATE_WEB = "corporate_web"
    ECOMMERCE_WEB = "ecommerce_web"
    PORTFOLIO = "portfolio"
    GITHUB_PAGE = "github_page"
    MAINTENANCE_ONLY = "maintenance_only"


class ProjectStage(StrEnum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DELIVERED = "delivered"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


@dataclass(slots=True)
class Lead:
    id: str
    name: str
    contact: str = ""
    source: LeadSource = LeadSource.OTHER
    business_type: str = ""
    has_website: bool = False
    stage: LeadStage = LeadStage.NEW
    notes: str = ""
    email: str = ""
    phone: str = ""
    city: str = ""
    enriched: bool = False
    score: int = 0  # 0-100: sin web + rubro digitalizable = alto
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Proposal:
    id: str
    lead_id: str
    project_type: ProjectType = ProjectType.LANDING
    pages: int = 1
    features: list[str] = field(default_factory=list)
    price_usd: float = 0.0
    timeline_days: int = 7
    free_tier: bool = True
    body_md: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Project:
    id: str
    lead_id: str
    proposal_id: str = ""
    project_type: ProjectType = ProjectType.LANDING
    stage: ProjectStage = ProjectStage.BACKLOG
    repo_url: str = ""
    preview_url: str = ""
    prod_url: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class MaintenanceContract:
    id: str
    project_id: str
    monthly_usd: float = 0.0
    includes_hosting: bool = False
    includes_seo: bool = False
    includes_content: bool = False
    active: bool = True
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


_PROJECT_BASE_PRICE: dict[ProjectType, float] = {
    ProjectType.LANDING: 0.0,
    ProjectType.GITHUB_PAGE: 0.0,
    ProjectType.PORTFOLIO: 0.0,
    ProjectType.CORPORATE_WEB: 150.0,
    ProjectType.ECOMMERCE_WEB: 300.0,
    ProjectType.MAINTENANCE_ONLY: 25.0,
}

_PROJECT_TIMELINE: dict[ProjectType, int] = {
    ProjectType.LANDING: 7,
    ProjectType.GITHUB_PAGE: 5,
    ProjectType.PORTFOLIO: 7,
    ProjectType.CORPORATE_WEB: 21,
    ProjectType.ECOMMERCE_WEB: 30,
    ProjectType.MAINTENANCE_ONLY: 3,
}

_UPSELL_CATALOG: list[dict[str, object]] = [
    {"id": "hosting_ssl", "label": "Hosting + SSL + dominio", "monthly_usd": 15.0},
    {"id": "maintenance", "label": "Mantenimiento mensual (updates + backups)", "monthly_usd": 25.0},
    {"id": "seo", "label": "SEO básico + Analytics", "monthly_usd": 30.0},
    {"id": "content", "label": "Contenido mensual (4 posts + copies)", "monthly_usd": 40.0},
    {"id": "ads", "label": "Gestión de ads (IG/FB/Google)", "monthly_usd": 60.0},
]


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "lead"


class ClientAcquisitionEngine:
    """In-memory kanban + proposal generator (persistencia vía caller/DB futura)."""

    def __init__(self) -> None:
        self._leads: dict[str, Lead] = {}
        self._proposals: dict[str, Proposal] = {}
        self._projects: dict[str, Project] = {}
        self._contracts: dict[str, MaintenanceContract] = {}

    # ── Leads ──
    def capture_lead(
        self,
        name: str,
        contact: str = "",
        source: LeadSource = LeadSource.OTHER,
        business_type: str = "",
        has_website: bool = False,
    ) -> Lead:
        lead_id = f"lead_{_slug(name)}_{int(datetime.now(UTC).timestamp())}"
        lead = Lead(
            id=lead_id,
            name=name.strip(),
            contact=contact.strip(),
            source=source,
            business_type=business_type.strip(),
            has_website=has_website,
        )
        self._leads[lead.id] = lead
        logger.info("Lead captured: %s (%s)", lead.name, lead.source.value)
        return lead

    def get_lead(self, lead_id: str) -> Lead | None:
        return self._leads.get(lead_id)

    def list_leads(self, stage: LeadStage | None = None) -> list[Lead]:
        leads = list(self._leads.values())
        if stage:
            leads = [lead for lead in leads if lead.stage == stage]
        return sorted(leads, key=lambda lead: lead.created_at, reverse=True)

    def advance_lead(self, lead_id: str, stage: LeadStage) -> Lead | None:
        lead = self._leads.get(lead_id)
        if not lead:
            return None
        lead.stage = stage
        lead.updated_at = datetime.now(UTC)
        return lead

    # ── Proposals ──
    def generate_proposal(
        self,
        lead_id: str,
        project_type: ProjectType = ProjectType.LANDING,
        pages: int = 1,
        features: list[str] | None = None,
    ) -> Proposal | None:
        lead = self._leads.get(lead_id)
        if not lead:
            return None
        feats = list(features or [])
        base = _PROJECT_BASE_PRICE.get(project_type, 0.0)
        extra_pages = max(0, pages - 1) * 20.0
        extra_features = len(feats) * 15.0
        price = round(base + extra_pages + extra_features, 2)
        free_tier = price == 0.0
        body = (
            f"# Propuesta — {lead.name}\n\n"
            f"Tipo: {project_type.value} · Páginas: {pages}\n"
            f"Funcionalidades: {', '.join(feats) if feats else 'base'}\n\n"
            f"Precio: {'GRATIS (tier prueba de valor)' if free_tier else f'USD {price}'}\n"
            f"Tiempo estimado: {_PROJECT_TIMELINE.get(project_type, 7)} días\n\n"
            f"Upsell recurrente sugerido: mantenimiento + hosting + SEO.\n"
        )
        proposal = Proposal(
            id=f"prop_{lead_id}_{project_type.value}",
            lead_id=lead_id,
            project_type=project_type,
            pages=max(1, pages),
            features=feats,
            price_usd=price,
            timeline_days=_PROJECT_TIMELINE.get(project_type, 7),
            free_tier=free_tier,
            body_md=body,
        )
        self._proposals[proposal.id] = proposal
        lead.stage = LeadStage.PROPOSAL_SENT
        lead.updated_at = datetime.now(UTC)
        return proposal

    # ── Projects ──
    def start_project(self, lead_id: str, proposal_id: str) -> Project | None:
        lead = self._leads.get(lead_id)
        proposal = self._proposals.get(proposal_id)
        if not lead or not proposal:
            return None
        project = Project(
            id=f"proj_{lead_id}",
            lead_id=lead_id,
            proposal_id=proposal_id,
            project_type=proposal.project_type,
            stage=ProjectStage.IN_PROGRESS,
        )
        self._projects[project.id] = project
        lead.stage = LeadStage.WON
        lead.updated_at = datetime.now(UTC)
        return project

    def advance_project(self, project_id: str, stage: ProjectStage) -> Project | None:
        project = self._projects.get(project_id)
        if not project:
            return None
        project.stage = stage
        project.updated_at = datetime.now(UTC)
        return project

    def list_projects(self, stage: ProjectStage | None = None) -> list[Project]:
        projects = list(self._projects.values())
        if stage:
            projects = [p for p in projects if p.stage == stage]
        return sorted(projects, key=lambda p: p.updated_at, reverse=True)

    # ── Maintenance (recurring revenue) ──
    def create_contract(
        self,
        project_id: str,
        monthly_usd: float = 25.0,
        includes_hosting: bool = True,
        includes_seo: bool = False,
        includes_content: bool = False,
    ) -> MaintenanceContract | None:
        if project_id not in self._projects:
            return None
        contract = MaintenanceContract(
            id=f"mnt_{project_id}",
            project_id=project_id,
            monthly_usd=max(0.0, monthly_usd),
            includes_hosting=includes_hosting,
            includes_seo=includes_seo,
            includes_content=includes_content,
        )
        self._contracts[contract.id] = contract
        project = self._projects[project_id]
        project.stage = ProjectStage.MAINTENANCE
        project.updated_at = datetime.now(UTC)
        return contract

    def monthly_recurring(self) -> float:
        return round(sum(c.monthly_usd for c in self._contracts.values() if c.active), 2)

    def upsell_catalog(self) -> list[dict[str, object]]:
        return [dict(item) for item in _UPSELL_CATALOG]

    def funnel(self) -> dict[str, int]:
        counts: dict[str, int] = {stage.value: 0 for stage in LeadStage}
        for lead in self._leads.values():
            counts[lead.stage.value] += 1
        return counts

    def get_status(self) -> dict[str, object]:
        return {
            "leads": len(self._leads),
            "proposals": len(self._proposals),
            "projects": len(self._projects),
            "contracts": len(self._contracts),
            "mrr_usd": self.monthly_recurring(),
            "funnel": self.funnel(),
        }

    # ── LeadGen Micro-SaaS ($0: scrape propio + enriquecimiento free-tier) ──

    def enrich_lead(self, lead_id: str, email: str = "", phone: str = "", city: str = "") -> Lead | None:
        """Enrich a lead with contact data (Hunter/Apollo free-tier fed by human/job)."""
        lead = self._leads.get(lead_id)
        if not lead:
            return None
        if email.strip():
            lead.email = email.strip()[:120]
        if phone.strip():
            lead.phone = phone.strip()[:40]
        if city.strip():
            lead.city = city.strip()[:80]
        lead.enriched = bool(lead.email or lead.phone)
        lead.score = self.score_lead(lead)
        lead.updated_at = datetime.now(UTC)
        return lead

    @staticmethod
    def score_lead(lead: Lead) -> int:
        """0-100 deterministic: sin web + contacto + rubro digitalizable = alto."""
        score = 20
        if not lead.has_website:
            score += 35
        if lead.email or lead.phone:
            score += 20
        hot = ("gastronom", "taller", "peluquer", "kiosco", "panader", "verduler", "gimnasio", "estetica")
        if any(h in (lead.business_type or "").lower() for h in hot):
            score += 15
        if lead.source == LeadSource.DIRECTORY_SCRAPE:
            score += 10
        return max(0, min(100, score))

    def export_qualified(self, min_score: int = 60) -> list[dict[str, object]]:
        """Export qualified leads as sellable list ($50-200 per 100-500)."""
        rows = [lead for lead in self._leads.values() if self.score_lead(lead) >= min_score]
        rows.sort(key=self.score_lead, reverse=True)
        return [
            {
                "name": lead.name,
                "business_type": lead.business_type,
                "city": lead.city,
                "email": lead.email,
                "phone": lead.phone or lead.contact,
                "has_website": lead.has_website,
                "score": self.score_lead(lead),
                "source": lead.source.value,
            }
            for lead in rows[:500]
        ]

    # ── Service Arbitrage ($0: cliente local -> freelancer junior, margen 50-70%) ──

    def plan_arbitrage(
        self,
        project_id: str,
        freelancer_cost_usd: float = 0.0,
        client_price_usd: float = 0.0,
    ) -> dict[str, object]:
        """Margin check for subcontracted service work. Honest: no margin invented."""
        project = self._projects.get(project_id)
        if not project:
            return {"success": False, "error": "project_not_found"}
        try:
            cost = max(0.0, float(freelancer_cost_usd or 0.0))
            price = max(0.0, float(client_price_usd or 0.0))
        except (TypeError, ValueError):
            return {"success": False, "error": "invalid_amounts"}
        if price <= 0:
            return {"success": False, "error": "client_price_required"}
        margin = round(price - cost, 2)
        margin_pct = round(margin / price * 100, 1) if price else 0.0
        return {
            "success": True,
            "project_id": project_id,
            "client_price_usd": price,
            "freelancer_cost_usd": cost,
            "margin_usd": margin,
            "margin_pct": margin_pct,
            "verdict": "VIABLE" if margin_pct >= 50 and margin > 0 else "THIN" if margin > 0 else "REJECT",
            "note": "Arbitrage viable exige margen ≥50%. Subcontratar solo tras seña del cliente.",
        }


_engine: ClientAcquisitionEngine | None = None


def get_client_acquisition_engine() -> ClientAcquisitionEngine:
    global _engine
    if _engine is None:
        _engine = ClientAcquisitionEngine()
    return _engine
