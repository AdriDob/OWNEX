"""Project Registry — every project is data on ONE engine.

Persists to OWNEX_DATA_DIR/projects.json (atomic write). Seeds 5 blueprints
(ownex/droppinglabel/mercado_libre/adriel_webs/rastro) as DATA referencing
workspace_ids — no code per project. Finance is a read-only view over the
Revenue Ledger filtered by metadata project. Maintenance = recurring templates
per project (prompt §27). Dedup before create (prompt §33).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.projects.models import (
    AutomationLevel,
    Project,
    ProjectPhase,
    ProjectState,
    ProjectTask,
    TaskState,
    health_score,
    priority_score,
)

logger = logging.getLogger("ownex.projects.registry")


def _store_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "projects.json"


# ── Phase templates (prompt §6: FASE 0-9, trimmed per project) ──

_STD_PHASES = [
    ("descubrimiento", "Blueprint: qué/problema/dinero/recursos/riesgos"),
    ("preparacion", "Cuentas, perfiles, configs, plantillas, métricas base"),
    ("construccion", "Productos/servicios/catálogo/infra/automatizaciones"),
    ("lanzamiento", "Publicar, validar, primeras acciones comerciales"),
    ("operacion", "Tareas diarias/semanales, controles, alertas"),
    ("optimizacion", "Qué funciona / qué cortar / qué mejorar"),
    ("crecimiento", "Nuevos productos/clientes/canales"),
    ("mantenimiento", "Recurrentes con mínimo esfuerzo"),
]


def _phases(names: list[str] | None = None) -> list[ProjectPhase]:
    wanted = names or [n for n, _ in _STD_PHASES]
    goals = dict(_STD_PHASES)
    return [ProjectPhase(name=n, goal=goals.get(n, ""), order=i) for i, n in enumerate(wanted)]


def _t(
    pid: str,
    phase: str,
    title: str,
    desc: str = "",
    *,
    priority: int = 5,
    state: TaskState = TaskState.BACKLOG,
    effort_min: int = 30,
    automation: AutomationLevel = AutomationLevel.MANUAL,
    tool: str = "",
    expected: str = "",
    financial: float = 0.0,
    urgency: int = 5,
    risk: int = 5,
    growth: int = 5,
    recurring: str | None = None,
    depends_on: list[str] | None = None,
) -> ProjectTask:
    tid = f"{pid}-{phase}-{abs(hash(title)) % 100000:05d}"
    return ProjectTask(
        id=tid,
        project_id=pid,
        phase=phase,
        title=title,
        description=desc,
        priority=priority,
        state=state,
        effort_min=effort_min,
        automation=automation,
        tool=tool,
        expected_result=expected,
        financial_impact_usd=financial,
        urgency=urgency,
        risk=risk,
        growth=growth,
        recurring=recurring,
        depends_on=depends_on or [],
    )


def _seed_ownex() -> Project:
    p = Project(
        id="ownex",
        workspace_id="ownex",
        name="OWNEX",
        description="Sistema operativo personal de ejecución",
        category="platform",
        business_model="infraestructura propia",
        state=ProjectState.OPERACION,
        priority=10,
        goals=["FINAL STABLE daily use", "Daily autonomous execution", "W1-W12 físico"],
        phases=_phases(),
    )
    tasks = [
        _t(
            "ownex",
            "operacion",
            "Daily digest 08:00",
            "Revisar best_action y ejecutar #1",
            state=TaskState.READY,
            effort_min=15,
            automation=AutomationLevel.AUTOMATICA,
            tool="daily_digest",
            expected="best_action ejecutada",
            urgency=9,
            recurring="daily",
        ),
        _t(
            "ownex",
            "mantenimiento",
            "Fast gate verde",
            "make test-fast 102/1 + ruff 0",
            state=TaskState.READY,
            effort_min=10,
            automation=AutomationLevel.AUTOMATICA,
            tool="pytest+ruff",
            expected="gate verde",
            urgency=7,
            recurring="daily",
        ),
        _t(
            "ownex",
            "operacion",
            "Validación física W1-W12",
            "Owner ejecuta en Windows 11 real",
            state=TaskState.WAITING,
            effort_min=120,
            automation=AutomationLevel.MANUAL,
            expected="12/12 PASS",
            urgency=8,
            risk=3,
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_droppinglabel() -> Project:
    p = Project(
        id="droppinglabel",
        workspace_id="droppinglabel",
        name="Droppinglabel",
        description="Instagram + WhatsApp sin stock propio",
        category="social_commerce",
        business_model="comision_dropshipping",
        state=ProjectState.PREPARACION,
        priority=6,
        goals=["Primer proveedor validado", "Primera venta con comisión registrada"],
        financial_goal_usd=500.0,
        phases=_phases(
            [
                "descubrimiento",
                "preparacion",
                "construccion",
                "lanzamiento",
                "operacion",
                "optimizacion",
                "mantenimiento",
            ]
        ),
    )
    tasks = [
        _t(
            "droppinglabel",
            "descubrimiento",
            "Registrar proveedor #1 (ropa/fútbol)",
            "Ficha: catálogo, comisión, stock, envío, devoluciones",
            state=TaskState.READY,
            effort_min=45,
            automation=AutomationLevel.MANUAL,
            tool="supplier_import",
            expected="proveedor en registry con score",
            urgency=8,
            growth=7,
        ),
        _t(
            "droppinglabel",
            "preparacion",
            "Calcular margen por producto",
            "costo+envío+comisión vs precio",
            state=TaskState.BACKLOG,
            effort_min=30,
            automation=AutomationLevel.SEMIAUTOMATICA,
            tool="sourcing/score",
            expected="margen >=25%",
            urgency=7,
            depends_on=[],
        ),
        _t(
            "droppinglabel",
            "operacion",
            "Revisar consultas WhatsApp",
            "Responder <1h, registrar pedido",
            state=TaskState.READY,
            effort_min=20,
            automation=AutomationLevel.MANUAL,
            expected="0 consultas sin respuesta",
            urgency=8,
            recurring="daily",
        ),
        _t(
            "droppinglabel",
            "mantenimiento",
            "Marcar winners/archivados",
            "Exposición a winners, archivar muertos",
            state=TaskState.BACKLOG,
            effort_min=20,
            automation=AutomationLevel.SEMIAUTOMATICA,
            expected="catálogo limpio",
            recurring="weekly",
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_mercadolibre() -> Project:
    p = Project(
        id="mercado_libre",
        workspace_id="mercado_libre",
        name="Mercado Libre",
        description="Marketplace dropshipping, catálogo validado antes de escalar",
        category="marketplace",
        business_model="margen_dropshipping",
        state=ProjectState.PREPARACION,
        priority=6,
        goals=["Primer producto con margen auditado", "100 listings solo validados"],
        financial_goal_usd=1000.0,
        phases=_phases(
            [
                "descubrimiento",
                "preparacion",
                "construccion",
                "lanzamiento",
                "operacion",
                "optimizacion",
                "mantenimiento",
            ]
        ),
    )
    tasks = [
        _t(
            "mercado_libre",
            "preparacion",
            "Sync catálogo proveedor → DRAFT",
            "sync-catalog, nada auto-publica",
            state=TaskState.READY,
            effort_min=30,
            automation=AutomationLevel.AUTOMATICA,
            tool="sync_supplier_catalog",
            expected="DRAFTs revisables",
            urgency=8,
        ),
        _t(
            "mercado_libre",
            "construccion",
            "Ficha SEO + precio mínimo",
            "costo+envío+comisión+impuestos+margen",
            state=TaskState.BACKLOG,
            effort_min=40,
            automation=AutomationLevel.SEMIAUTOMATICA,
            expected="precio mínimo calculado",
            urgency=7,
        ),
        _t(
            "mercado_libre",
            "operacion",
            "Revisar stock/precio/preguntas",
            "Diaria: stock, precio, preguntas, reputación",
            state=TaskState.READY,
            effort_min=25,
            automation=AutomationLevel.SEMIAUTOMATICA,
            expected="0 quiebres sin alerta",
            urgency=8,
            recurring="daily",
        ),
        _t(
            "mercado_libre",
            "mantenimiento",
            "Limpiar catálogo mensual",
            "Eliminar inviables, renegociar",
            state=TaskState.BACKLOG,
            effort_min=60,
            automation=AutomationLevel.MANUAL,
            expected="solo winners",
            recurring="monthly",
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_adriel_webs() -> Project:
    p = Project(
        id="adriel_webs",
        workspace_id="adriel_webs",
        name="Adriel Webs",
        description="Venta de webs a negocios locales vía WhatsApp",
        category="b2b_services",
        business_model="proyecto+mantenimiento",
        state=ProjectState.PREPARACION,
        priority=7,
        goals=["Landing + portfolio publicados", "Primer negocio contactado"],
        financial_goal_usd=1500.0,
        phases=_phases(
            [
                "descubrimiento",
                "preparacion",
                "construccion",
                "lanzamiento",
                "operacion",
                "crecimiento",
                "mantenimiento",
            ]
        ),
    )
    tasks = [
        _t(
            "adriel_webs",
            "preparacion",
            "Publicar landing + portfolio",
            "GitHub Pages gratis, WhatsApp CTA",
            state=TaskState.READY,
            effort_min=90,
            automation=AutomationLevel.SEMIAUTOMATICA,
            expected="URLs vivas",
            urgency=8,
            growth=8,
        ),
        _t(
            "adriel_webs",
            "operacion",
            "Contactar 5 negocios sin web",
            "Mensaje preparado + lead score",
            state=TaskState.BACKLOG,
            effort_min=60,
            automation=AutomationLevel.SEMIAUTOMATICA,
            tool="client_acquisition",
            expected="5 contactos enviados",
            financial=500.0,
            urgency=7,
            growth=8,
            recurring="weekly",
        ),
        _t(
            "adriel_webs",
            "operacion",
            "Seguimiento leads 48h",
            "Revisar respuestas, proponer",
            state=TaskState.BACKLOG,
            effort_min=30,
            automation=AutomationLevel.MANUAL,
            expected="0 leads fríos sin follow-up",
            urgency=7,
            recurring="weekly",
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_rastro() -> Project:
    p = Project(
        id="rastro",
        workspace_id="bug_bounty",
        name="Rastro",
        description="Signal compression para bug bounty (sin explotación automática)",
        category="security_intel",
        business_model="upside_bounties",
        state=ProjectState.OPERACION,
        priority=8,
        goals=["Ranking ROI real", "Duplicate risk medido", "Upside sin fricción"],
        phases=_phases(["operacion", "optimizacion", "mantenimiento"]),
    )
    tasks = [
        _t(
            "rastro",
            "operacion",
            "Refresh feeds intel",
            "intelligence_refresh 05:00 verifica",
            state=TaskState.READY,
            effort_min=5,
            automation=AutomationLevel.AUTOMATICA,
            tool="intelligence_refresh",
            expected="7 feeds frescos",
            urgency=6,
            recurring="daily",
        ),
        _t(
            "rastro",
            "optimizacion",
            "Revisar top ROI semanal",
            "ROI 0-100 + duplicate risk",
            state=TaskState.BACKLOG,
            effort_min=30,
            automation=AutomationLevel.SEMIAUTOMATICA,
            expected="1 target priorizado",
            urgency=6,
            recurring="weekly",
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_content_factory() -> Project:
    p = Project(
        id="content_factory",
        workspace_id="content_factory",
        name="Content Factory",
        description="YouTube MPT 100% gratis + POD @estampalo.ig promocional Nova Store",
        category="content",
        business_model="audience_recurring",
        state=ProjectState.PREPARACION,
        priority=5,
        goals=["Canal YouTube MPT con 1 video/día 14 días", "POD @estampalo.ig como promoción MeLi"],
        financial_goal_usd=300.0,
        phases=_phases(["preparacion", "construccion", "lanzamiento", "operacion", "optimizacion", "mantenimiento"]),
    )
    tasks = [
        _t(
            "content_factory",
            "preparacion",
            "Pexels API key gratis en MPT",
            "pexels.com/api → MPT config",
            state=TaskState.READY,
            effort_min=15,
            automation=AutomationLevel.MANUAL,
            expected="MPT genera video sin error",
            urgency=7,
        ),
        _t(
            "content_factory",
            "preparacion",
            "Definir nombre canal YouTube (separado de POD)",
            "Branding Canva gratis, no usar @estampalo.ig",
            state=TaskState.BACKLOG,
            effort_min=30,
            automation=AutomationLevel.MANUAL,
            expected="nombre + logo",
            urgency=6,
        ),
        _t(
            "content_factory",
            "operacion",
            "1 Short/día 14 días (MPT → Human Gate → subir)",
            "Guion Ollama + voz Edge + video Pexels",
            state=TaskState.BACKLOG,
            effort_min=30,
            automation=AutomationLevel.SEMIAUTOMATICA,
            expected="14 videos publicados",
            urgency=7,
            recurring="daily",
        ),
        _t(
            "content_factory",
            "operacion",
            "POD @estampalo.ig: 3 posts/sem promocionales MeLi",
            "Diseños en Canva, DM/WhatsApp → pedido → proveedor",
            state=TaskState.BACKLOG,
            effort_min=20,
            automation=AutomationLevel.MANUAL,
            expected="engagement + DM → venta MeLi",
            urgency=6,
            recurring="weekly",
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_trading() -> Project:
    p = Project(
        id="trading",
        workspace_id="trading",
        name="Trading",
        description="Memecoins + acciones, PAPER default, jamás renta base",
        category="capital",
        business_model="capital_only",
        state=ProjectState.PREPARACION,
        priority=4,
        goals=["Paper loop 2 semanas validado", "Kill switch humano probado"],
        phases=_phases(["preparacion", "operacion", "optimizacion", "mantenimiento"]),
    )
    tasks = [
        _t(
            "trading",
            "preparacion",
            "Paper memecoins DRY_RUN verificado",
            "DexScreener + RugCheck + Jupiter",
            state=TaskState.READY,
            effort_min=20,
            automation=AutomationLevel.AUTOMATICA,
            expected="fills simulados ok",
            urgency=6,
        ),
        _t(
            "trading",
            "operacion",
            "Paper loop cada 15m ≥2 semanas",
            "run_paper_cycle_once + job trading_memecoin_paper",
            state=TaskState.BACKLOG,
            effort_min=5,
            automation=AutomationLevel.AUTOMATICA,
            expected="win-rate/profit-factor/drawdown",
            urgency=6,
            recurring="daily",
        ),
        _t(
            "trading",
            "optimizacion",
            "Revisar métricas paper con owner → live solo con orden",
            "Human Gate + IdentityVault + capital declarado",
            state=TaskState.BACKLOG,
            effort_min=30,
            automation=AutomationLevel.MANUAL,
            expected="decisión live/paper",
            urgency=5,
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_backup_income() -> Project:
    p = Project(
        id="backup_income",
        workspace_id="backup_income",
        name="Laburo Presencial",
        description="Trabajo presencial Zona Sur/CABA, LAST_RESORT, neto/hora con traslado",
        category="local_jobs",
        business_model="safety_net",
        state=ProjectState.PREPARACION,
        priority=3,
        goals=["Zonas + neto/hora mínimo definidos", "CV ATS + perfiles bolsas listos"],
        phases=_phases(["preparacion", "operacion", "mantenimiento"]),
    )
    tasks = [
        _t(
            "backup_income",
            "preparacion",
            "CV ATS 1 página + perfiles Zonajobs/Bumeran",
            "Skills reales Profile Kit",
            state=TaskState.READY,
            effort_min=60,
            automation=AutomationLevel.MANUAL,
            expected="CV + 3 perfiles completos",
            urgency=6,
        ),
        _t(
            "backup_income",
            "operacion",
            "Búsqueda 30 min/día solo si se activa (LAST_RESORT)",
            "5 postulaciones/día max, carta adaptada",
            state=TaskState.BACKLOG,
            effort_min=30,
            automation=AutomationLevel.MANUAL,
            expected="0 postulaciones sin follow-up",
            urgency=5,
            recurring="daily",
        ),
        _t(
            "backup_income",
            "operacion",
            "Seguimiento 48h + comparar vs neto/hora mínimo",
            "Rechazo automático bajo mínimo",
            state=TaskState.BACKLOG,
            effort_min=20,
            automation=AutomationLevel.MANUAL,
            expected="oferta vs mínimo comparada",
            urgency=5,
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_dev_bounty() -> Project:
    p = Project(
        id="dev_bounty",
        workspace_id="dev_bounty",
        name="Dev Bounty",
        description="Algora/Opire/IssueHunt/GitHub — outcome-based, 1 claim activo hasta merge",
        category="dev_bounty",
        business_model="outcome_based",
        state=ProjectState.PREPARACION,
        priority=8,
        goals=["1 claim activo $50-200 <10 comentarios", "PR con tests + README → merge → PAID"],
        phases=_phases(["preparacion", "operacion", "optimizacion", "mantenimiento"]),
    )
    tasks = [
        _t(
            "dev_bounty",
            "preparacion",
            "GITHUB_TOKEN en vault",
            "github.com/settings/tokens",
            state=TaskState.READY,
            effort_min=10,
            automation=AutomationLevel.MANUAL,
            expected="token verificado",
            urgency=9,
        ),
        _t(
            "dev_bounty",
            "operacion",
            "Filtrar bounties $50-200 <10 comentarios",
            "workbank cycle + /decision/evaluate",
            state=TaskState.BACKLOG,
            effort_min=30,
            automation=AutomationLevel.SEMIAUTOMATICA,
            expected="top-3 elegidos",
            urgency=8,
        ),
        _t(
            "dev_bounty",
            "operacion",
            "1 claim activo hasta merge (no 5 paralelos)",
            "Comentar + fork + branch",
            state=TaskState.BACKLOG,
            effort_min=20,
            automation=AutomationLevel.MANUAL,
            expected="claim activo",
            urgency=8,
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


def _seed_ai_training() -> Project:
    p = Project(
        id="ai_training",
        workspace_id="ai_training",
        name="AI Training",
        description="Mercor/Outlier/Alignerr — assessments primero, luego tareas $15-55/h",
        category="ai_work",
        business_model="hourly_tasks",
        state=ProjectState.PREPARACION,
        priority=7,
        goals=["3 assessments submitted", "1er task pagado $8-55/h"],
        phases=_phases(["preparacion", "operacion", "optimizacion", "mantenimiento"]),
    )
    tasks = [
        _t(
            "ai_training",
            "preparacion",
            "Assessments Mercor/Outlier/Alignerr en paralelo",
            "Profile Kit para respuestas",
            state=TaskState.READY,
            effort_min=120,
            automation=AutomationLevel.MANUAL,
            expected="3 submitted",
            urgency=9,
        ),
        _t(
            "ai_training",
            "operacion",
            "Daily 1h Outlier/Alignerr si aprobado",
            "quality > speed, guidelines 2x",
            state=TaskState.BACKLOG,
            effort_min=60,
            automation=AutomationLevel.MANUAL,
            expected="streak 10/14 días",
            urgency=7,
            recurring="daily",
        ),
    ]
    for t in tasks:
        p.tasks[t.id] = t
    return p


_SEEDS = (
    _seed_ownex,
    _seed_droppinglabel,
    _seed_mercadolibre,
    _seed_adriel_webs,
    _seed_rastro,
    _seed_content_factory,
    _seed_trading,
    _seed_backup_income,
    _seed_dev_bounty,
    _seed_ai_training,
)


class ProjectStore:
    """Persisted project registry (atomic JSON). Seeds on first run."""

    def __init__(self, path=None) -> None:
        self._path = Path(path) if path else _store_path()
        self._projects: dict[str, Project] = {}
        self._load_or_seed()

    # ── persistence ──
    def _load_or_seed(self) -> None:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                for pid, pdata in raw.get("projects", {}).items():
                    self._projects[pid] = _project_from_dict(pdata)
                if self._projects:
                    return
            except Exception:
                logger.warning("projects.json corrupto, re-seed")
        for fn in _SEEDS:
            p = fn()
            self._projects[p.id] = p
        self._save()

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(
                    {"projects": {k: _project_to_dict(v) for k, v in self._projects.items()}},
                    ensure_ascii=False,
                    indent=1,
                ),
                encoding="utf-8",
            )
            tmp.replace(self._path)
        except Exception as exc:
            logger.warning("project save falló: %s", exc)

    # ── CRUD ──
    def list(self) -> list[Project]:
        return list(self._projects.values())

    def get(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def add_task(self, project_id: str, task: ProjectTask) -> bool:
        """Dedup before create (prompt §33): same title+phase → reject."""
        p = self._projects.get(project_id)
        if p is None:
            return False
        norm = task.title.strip().lower()
        for t in p.tasks.values():
            if t.phase == task.phase and t.title.strip().lower() == norm:
                logger.info("task duplicada rechazada: %s/%s", project_id, norm)
                return False
        p.tasks[task.id] = task
        p.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return True

    def set_task_state(self, project_id: str, task_id: str, state: TaskState, *, evidence: str = "") -> bool:
        p = self._projects.get(project_id)
        if p is None or task_id not in p.tasks:
            return False
        t = p.tasks[task_id]
        t.state = state
        t.updated_at = datetime.now(UTC).isoformat()
        if evidence:
            t.evidence = evidence
        if state == TaskState.DONE:
            t.done_at = datetime.now(UTC).isoformat()
        p.updated_at = t.updated_at
        self._save()
        return True

    def set_project_state(self, project_id: str, state: ProjectState) -> bool:
        p = self._projects.get(project_id)
        if p is None:
            return False
        p.state = state
        p.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return True

    def record_decision(self, project_id: str, decision: str, rationale: str = "") -> bool:
        p = self._projects.get(project_id)
        if p is None:
            return False
        p.decisions.append({"at": datetime.now(UTC).isoformat(), "decision": decision, "rationale": rationale})
        self._save()
        return True


def _project_to_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "workspace_id": p.workspace_id,
        "name": p.name,
        "description": p.description,
        "category": p.category,
        "business_model": p.business_model,
        "state": p.state.value,
        "priority": p.priority,
        "started_at": p.started_at,
        "updated_at": p.updated_at,
        "goals": p.goals,
        "financial_goal_usd": p.financial_goal_usd,
        "phases": [ph.to_dict() for ph in p.phases],
        "tasks": {tid: t.to_dict() for tid, t in p.tasks.items()},
        "supplier_ids": p.supplier_ids,
        "lead_ids": p.lead_ids,
        "product_ids": p.product_ids,
        "urls": p.urls,
        "metrics": p.metrics,
        "decisions": p.decisions,
    }


def _project_from_dict(d: dict) -> Project:
    from cores.projects.models import ProjectPhase

    p = Project(
        id=d["id"],
        workspace_id=d.get("workspace_id", d["id"]),
        name=d.get("name", d["id"]),
        description=d.get("description", ""),
        category=d.get("category", ""),
        business_model=d.get("business_model", ""),
        state=ProjectState(d.get("state", "idea")),
        priority=int(d.get("priority", 5)),
        started_at=d.get("started_at", ""),
        updated_at=d.get("updated_at", ""),
        goals=d.get("goals", []),
        financial_goal_usd=float(d.get("financial_goal_usd", 0.0)),
        phases=[
            ProjectPhase(name=ph["name"], goal=ph.get("goal", ""), order=ph.get("order", 0))
            for ph in d.get("phases", [])
        ],
        supplier_ids=d.get("supplier_ids", []),
        lead_ids=d.get("lead_ids", []),
        product_ids=d.get("product_ids", []),
        urls=d.get("urls", {}),
        metrics=d.get("metrics", {}),
        decisions=d.get("decisions", []),
    )
    for tid, td in (d.get("tasks", {}) or {}).items():
        try:
            t = ProjectTask(
                id=tid,
                project_id=d["id"],
                phase=td.get("phase", ""),
                title=td.get("title", ""),
                description=td.get("description", ""),
                priority=int(td.get("priority", 5)),
                state=TaskState(td.get("state", "backlog")),
                depends_on=td.get("depends_on", []),
                effort_min=int(td.get("effort_min", 30)),
                due=td.get("due"),
                recurring=td.get("recurring"),
                automation=AutomationLevel(td.get("automation", "manual")),
                tool=td.get("tool", ""),
                expected_result=td.get("expected_result", ""),
                evidence=td.get("evidence", ""),
                financial_impact_usd=float(td.get("financial_impact_usd", 0.0)),
                urgency=int(td.get("urgency", 5)),
                risk=int(td.get("risk", 5)),
                growth=int(td.get("growth", 5)),
                created_at=td.get("created_at", ""),
                updated_at=td.get("updated_at", ""),
                done_at=td.get("done_at"),
            )
            p.tasks[tid] = t
        except Exception:
            continue
    return p


# ── Cross-project queries (prompt §9/§28/§29/§30) ──


def _deps_blocked(task: ProjectTask, tasks: dict[str, ProjectTask]) -> bool:
    for dep in task.depends_on:
        d = tasks.get(dep)
        if d is not None and d.state != TaskState.DONE:
            return True
    return False


def next_actions(store: ProjectStore, *, limit: int = 3) -> list[dict[str, Any]]:
    """TOP-N actions across ALL projects by priority_score (blocked sinks to 0)."""
    scored: list[tuple[float, Project, ProjectTask]] = []
    for p in store.list():
        if p.state in (ProjectState.PAUSADO, ProjectState.CERRADO):
            continue
        for t in p.tasks.values():
            if t.state in (TaskState.DONE, TaskState.CANCELLED, TaskState.ARCHIVED):
                continue
            blocked = _deps_blocked(t, p.tasks)
            scored.append((priority_score(t, blocked=blocked), p, t))
    scored.sort(key=lambda s: s[0], reverse=True)
    out = []
    for score, p, t in scored[:limit]:
        out.append(
            {
                "project": p.id,
                "project_name": p.name,
                "task_id": t.id,
                "title": t.title,
                "phase": t.phase,
                "score": score,
                "state": t.state.value,
                "effort_min": t.effort_min,
                "automation": t.automation.value,
                "expected_result": t.expected_result,
                "ladder_rung": t.to_ladder_rung(),
            }
        )
    return out


def finance_for(project_id: str) -> dict[str, Any]:
    """Read-only finance view: ledger entries tagged with metadata project.

    Totals only from PAID/NET states. No estimates counted as cash.
    """
    try:
        from cores.revenue.ledger import RevenueState, get_revenue_ledger

        ledger = get_revenue_ledger()
        paid = ledger.get_by_state(RevenueState.PAID)
        pending = ledger.get_pending_payouts()
        net = gross = fees = pend = 0.0
        n_paid = 0
        for e in list(paid) + list(pending):
            d = e.to_dict() if hasattr(e, "to_dict") else e
            meta = d.get("metadata") or {}
            if str(meta.get("project", "")) != project_id:
                continue
            if str(d.get("state")) == RevenueState.PAID.value:
                n_paid += 1
                net += float(d.get("net_usd") or 0.0)
                gross += float(d.get("gross_usd") or 0.0)
                fees += float(d.get("fees_usd") or 0.0)
            else:
                pend += float(d.get("gross_usd") or 0.0)
        return {
            "project": project_id,
            "paid_count": n_paid,
            "gross_usd": round(gross, 2),
            "fees_usd": round(fees, 2),
            "net_usd": round(net, 2),
            "pending_usd": round(pend, 2),
        }
    except Exception:
        return {
            "project": project_id,
            "paid_count": 0,
            "gross_usd": 0.0,
            "fees_usd": 0.0,
            "net_usd": 0.0,
            "pending_usd": 0.0,
        }


def maintenance_due(store: ProjectStore) -> list[dict[str, Any]]:
    """Recurring maintenance tasks across projects (prompt §27 daily/weekly/monthly)."""
    out = []
    for p in store.list():
        for t in p.tasks.values():
            if t.recurring and t.state in (TaskState.READY, TaskState.BACKLOG):
                out.append(
                    {
                        "project": p.id,
                        "task_id": t.id,
                        "title": t.title,
                        "recurring": t.recurring,
                        "effort_min": t.effort_min,
                    }
                )
    return out


def portfolio(store: ProjectStore) -> list[dict[str, Any]]:
    """PROJECT PORTFOLIO (prompt §29): status/health/progress/revenue/next/blocker."""
    rows = []
    for p in store.list():
        counts: dict[str, int] = {}
        for t in p.tasks.values():
            counts[t.state.value] = counts.get(t.state.value, 0) + 1
        blocked = counts.get("blocked", 0)
        h = health_score(p, blocked=blocked)
        fin = finance_for(p.id)
        nxt = next_actions(store, limit=50)
        own = [a for a in nxt if a["project"] == p.id][:1]
        rows.append(
            {
                "project": p.id,
                "name": p.name,
                "state": p.state.value,
                "health": h["level"],
                "health_score": h["score"],
                "progress": counts,
                "revenue": fin,
                "next": own[0] if own else None,
                "blocker": f"{blocked} blocked" if blocked else None,
            }
        )
    rows.sort(key=lambda r: (r["health"] != "CRITICAL", -(r["revenue"]["net_usd"] or 0)))
    return rows
