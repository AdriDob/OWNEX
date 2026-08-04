"""Magic Experience Engine — universal request understanding + opportunity execution plans.

Covers the two execution specs ("Opportunity Execution Engine" and "Magic
Experience Engine") with deterministic, honest logic:

1. ``plan_objective`` — turn a loose request ("create a website", "prepare a
   Fiverr delivery", "analyze this bug") into an organized execution blueprint:
   Goal → Requirements → Plan → Tools → Execution → Verification → Deliverable,
   with a Time Compression estimate (normal hours vs OWNEX-optimized hours) and
   the human decisions that remain. No fabricated results, no fake LLM.

2. ``plan_execution`` — turn an existing opportunity (a raw dict or a Work Bank
   item) into an execution plan: Opportunity Report (fields + direct links),
   human-vs-automation split, work-reduction model, the 4-step roadmap
   (Prepare → Execute → QC → Deliver) and the Expected Value ranking
   ``EV = reward × success_probability / human_hours``.

Both reuse the existing Direct Work Engine models and constants — this module
adds the *plan* layer only, it does not re-implement discovery/scoring/delivery.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.execution_planner")

ACCELERATION_250 = 5.0  # Magic example used by the specs: 6 days -> ~1h5m is ~130x
CATEGORY_DEFAULT = "general"

# ─────────────────────────────────────────────────────────────
# Request templates — "Universal Request Understanding"
# Curated/mél tables, no magic strings; each category maps a
# request to a full blueprint + an honest time-compression model.
# ─────────────────────────────────────────────────────────────


@dataclass
class RequestBlueprint:
    category: str
    goal: str
    requirements: list[str]
    tools: list[str]
    plan: list[str]
    verification: list[str]
    deliverables: list[str]
    normal_hours: float
    ownex_hours: float
    human_decision: str
    error_hint: str = ""


REQUESTS: dict[str, RequestBlueprint] = {
    "website": RequestBlueprint(
        category="frontend",
        goal="Una web funcional para {subject}",
        requirements=[
            "Propósito y audiencia clara de {subject}",
            "Secciones (landing, features, contacto)",
            "Paleta/marca de referencia",
            "Dominio/hosting objetivo",
        ],
        tools=["Vite + Vue 3/Tailwind", "Deployment a Netlify/Vercel si aplica"],
        plan=[
            "Estructurar la SPA y componentes",
            "Diseñar visual (Tokens de marca OWNEX)",
            "Contenido de cada sección",
            "Responsive + SEO básico",
        ],
        verification=["Corre en local", "Responsive en 3 tamaños", "Links/CTAs funcionan", "Build de producción OK"],
        deliverables=["Código fuente", "Build de producción", "Vec de despliegue"],
        normal_hours=40.0,
        ownex_hours=4.0,
        human_decision="Aprobar contenido, dominio y look final",
    ),
    "fiverr_delivery": RequestBlueprint(
        category="delivery",
        goal="Paquete de entrega listo para {subject}",
        requirements=[
            "Requerimientos del gig de {subject} (del brief del comprador)",
            "Formato y archivos pedidos",
            "Extras que aplican",
        ],
        tools=["Plantillas de entrega (README/proposal)", "Conversores de formato"],
        plan=[
            "Releer el brief y extraer checkboxes",
            "Generar los archivos pedidos",
            "Redactar mensaje de entrega",
            "Adjuntar muestra/preview + resumen",
        ],
        verification=["Cada requisito del brief cubierto", "Archivos abren OK", "Mensaje claro y corto"],
        deliverables=["Archivos del gig", "Mensaje de entrega", "Preview/imagen de muestra"],
        normal_hours=3.0,
        ownex_hours=0.5,
        human_decision="Revisión final y clic en Enviar",
    ),
    "bug_analysis": RequestBlueprint(
        category="security",
        goal="Análisis del bug: causa, impacto y PoC",
        requirements=[
            "Descripción/URL del bug de {subject}",
            "Acceso o request de ejemplo",
            "Edición objetivo / Endpoint",
        ],
        tools=["HTTP probe tooling", "Scripts de PoC"],
        plan=[
            "Recon de {subject} y mapeo del input",
            "Pruebas controladas (sin impacto)",
            "Documentar evidencia + impacto",
            "Redactar reporte/describir hallazgo",
        ],
        verification=["Causa raíz identificada", "PoC reproducible", "Sin daño colateral"],
        deliverables=["Reporte técnico", "PoC", "Evidencia capturada"],
        normal_hours=8.0,
        ownex_hours=1.0,
        human_decision="Validar el PoC y la severidad antes de reportar",
    ),
    "tool_install": RequestBlueprint(
        category="devops",
        goal="Instalar y dejar operativo {subject}",
        requirements=[
            "Sistema objetivo (OS/version)",
            "Version deseada de {subject}",
            "Perfil de uso (dev/producción)",
        ],
        tools=["Gestor de paquetes", "Config + systemd/servicio"],
        plan=[
            "Verificar dependencias",
            "Instalar {subject}",
            "Configurar y probar arranque",
            "Documentar comandos de uso",
        ],
        verification=["Servicio levanta", "Comando de version OK", "Log sin errores", "Reinicio sobrevive"],
        deliverables=["Instalación operativa", "Nota de configuración"],
        normal_hours=2.0,
        ownex_hours=0.5,
        human_decision="Elegir versión/lugar de instalación",
    ),
    "documentation": RequestBlueprint(
        category="documentation",
        goal="Documentación profesional de {subject}",
        requirements=["Qué documentar de {subject}", "Público objetivo", "Formato deseado (Markdown/PDF)"],
        tools=["Templates OWNEX", "Markdown/lint"],
        plan=[
            "Inventariar entidades/features",
            "Redactar guías por sección",
            "Revisar claridad y ejemplos",
            "Exportar",
        ],
        verification=["Sin secciones vacías", "Ejemplos válidos", "Estilo consistente"],
        deliverables=["Documento final", "Fuente editable"],
        normal_hours=12.0,
        ownex_hours=1.5,
        human_decision="Confirmar alcance y aprobar versión final",
    ),
    "market_research": RequestBlueprint(
        category="market",
        goal="Informe de mercado de {subject}",
        requirements=["Mercado/plataforma de {subject}", "Preguntas a responder", "Horizonte"],
        tools=["Source Intelligence + Radar OWNEX", "Fuentes curadas"],
        plan=[
            "Escaneo de fuentes de {subject}",
            "Ranking por EV/barrera",
            "Análisis de oportunidad",
            "Resumen accionable",
        ],
        verification=["Datos reales (no inventados)", "Top claro", "Recomendación accionable"],
        deliverables=["Informe de mercado", "Top oportunidades"],
        normal_hours=16.0,
        ownex_hours=0.5,
        human_decision="Elegir en qué fuente profundizar",
    ),
    "project_prep": RequestBlueprint(
        category="planning",
        goal="Proyecto organizado: requisitos + plan + próximo paso",
        requirements=["Objetivo de {subject}", "Restricciones", "Recursos disponibles"],
        tools=["Work Bank", "Extension evaluator"],
        plan=["Definir alcance", "Desglosar tareas", "Asignar OWNEX/robot vs humano", "Fijar entregables"],
        verification=["Cada tarea tiene dueño", "Pasos ejecutables"],
        deliverables=["Plan de proyecto", "Cola de trabajo"],
        normal_hours=4.0,
        ownex_hours=0.5,
        human_decision="Aprobar alcance e hitos",
    ),
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "website": ["website", "web ", "sitio", "landing", "pagina", "page", "site"],
    "fiverr_delivery": ["fiverr", "gig", "delivery", "entrega", "order"],
    "bug_analysis": ["bug", "error", "analiza", "vulnerab", "exploit", "po?c", "crash", "audit"],
    "tool_install": ["install", "instalar", "setup", "environment", "entorno"],
    "documentation": ["documentation", "documentacion", "doc", "readme", "manual", "guia", "guide"],
    "market_research": ["market", "research", "mercado", "investiga", "radar", "sources"],
    "project_prep": ["project", "proyecto", "organiza", "prepare", "prepara", "plan"],
}

# ─────────────────────────────────────────────────────────────
# Plan output
# ─────────────────────────────────────────────────────────────


@dataclass
class PlanResult:
    objective: str
    category: str
    goal: str
    requirements: list[str]
    plan: list[str]
    tools: list[str]
    verification: list[str]
    deliverables: list[str]
    normal_hours: float
    ownex_hours: float
    automation_pct: int
    human_decisions: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["time_compression"] = _time_compression(self.normal_hours, self.ownex_hours)
        return d


def _time_compression(normal_hours: float, ownex_hours: float) -> dict[str, Any]:
    if normal_hours <= 0 or ownex_hours <= 0:
        return {"ratio": 1.0, "label": "sin estimación"}
    ratio = round(normal_hours / ownex_hours, 1)
    if ratio >= 1000:
        label = "horas → segundos"
    elif ratio >= 60:
        label = "horas → minutos"
    elif ratio >= 8:
        label = "días → horas"
    else:
        label = "optimizado"
    return {"ratio": ratio, "label": label}


def plan_objective(objective: str) -> PlanResult:
    """Understand a loose request and return the magic blueprint + time model.

    Deterministic classification over curated keywords; honest numbers from the
    blueprint tables (no invented "97% optimization").
    """
    text = objective.strip()
    if not text:
        return PlanResult(
            objective=text,
            category=CATEGORY_DEFAULT,
            goal="Sin objetivo",
            requirements=[],
            plan=[],
            tools=[],
            verification=[],
            deliverables=[],
            normal_hours=0.0,
            ownex_hours=0.0,
            automation_pct=0,
            human_decisions="Definir el objetivo primero",
            error="Objetivo vacío",
        )

    fallback = RequestBlueprint(
        category=CATEGORY_DEFAULT,
        goal="{subject}",
        requirements=["Requerimientos de {subject}", "Restricciones", "Recursos disponibles"],
        tools=[],
        plan=["Relevar qué se pide", "Definir pasos", "Asignar tareas", "Entregar y verificar"],
        verification=["El objetivo queda claro", "Entregable definido"],
        deliverables=["Entregable definido por el usuario"],
        normal_hours=4.0,
        ownex_hours=1.0,
        human_decision="Definir el objetivo con precisión",
    )

    lower = text.lower()
    category = CATEGORY_DEFAULT
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(kw.strip())}\b", lower) for kw in keywords if kw.strip()):
            category = cat
            break

    blueprint = REQUESTS.get(category, fallback)
    automation = _automation_pct(blueprint.ownex_hours, blueprint.normal_hours)
    return PlanResult(
        objective=text,
        category=blueprint.category,
        goal=blueprint.goal.format(subject=text[:40]),
        requirements=blueprint.requirements,
        plan=blueprint.plan,
        tools=blueprint.tools,
        verification=blueprint.verification,
        deliverables=blueprint.deliverables,
        normal_hours=blueprint.normal_hours,
        ownex_hours=blueprint.ownex_hours,
        automation_pct=automation,
        human_decisions=blueprint.human_decision,
    )


def _automation_pct(ownex_hours: float, normal_hours: float) -> int:
    if normal_hours <= 0 or ownex_hours <= 0:
        return 0
    return max(0, min(100, int(round((1 - ownex_hours / normal_hours) * 100))))


# ─────────────────────────────────────────────────────────────
# Opportunity execution plan
# ─────────────────────────────────────────────────────────────


@dataclass
class OpportunityPlan:
    opportunity_id: str
    title: str
    category: str
    platform: str
    url: str
    reward_usd: float
    difficulty: str
    required_skills: list[str] = field(default_factory=list)
    success_probability: float = 0.0
    direct_links: dict[str, str] = field(default_factory=dict)
    human_work_minutes: float = 0.0
    automation_pct: int = 0
    original_hours: float = 0.0
    remaining_human_hours: float = 0.0
    expected_value_per_hour: float = 0.0
    roadmap: list[dict[str, Any]] = field(default_factory=list)
    next_button: str = ""
    elgibility_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _effort_hours(difficulty: str | None, reward: float, base_hours: float) -> float:
    """Honest base effort: reward acts only as a sanity floor, never as promise."""
    if difficulty:
        dl = str(difficulty).lower()
        if "high" in dl or "hard" in dl or "expert" in dl:
            base_hours = max(base_hours, 20.0)
        elif "medium" in dl or "intermediate" in dl:
            base_hours = max(base_hours, 6.0)
    if reward and base_hours < 1.0:
        base_hours = 1.0  # floor
    return round(base_hours, 1)


def _success_probability(reward: float, has_hard_reqs: bool, has_experience_reqs: bool) -> float:
    """Explicit, conservative probability used in EV — never a guaranteed payout."""
    p = 0.35 if reward > 0 else 0.0
    if reward > 2000:
        p = max(0.0, p - 0.25)  # big bounties are competitive
    if has_hard_reqs:
        p = max(0.0, p - 0.15)
    if has_experience_reqs:
        p = max(0.0, p - 0.10)
    return round(max(0.0, min(1.0, p)), 2)


def _roadmap(
    title: str,
    url: str,
    needs_account: bool,
    needs_review: bool,
    needs_submission: bool,
) -> list[dict[str, Any]]:
    """The 4-step execution roadmap: prepare → execute → QC → deliver."""
    steps: list[dict[str, Any]] = []
    prep_actions = [
        "Crear/cargar cuenta en la plataforma" if needs_account else "Verificar acceso existente a la plataforma",
        "Leer reglas, requisitos y formato de entrega",
    ]
    steps.append(
        {
            "stage": "1. Preparation",
            "actions": prep_actions,
            "own_ex_delivers": "Guía de la plataforma + plantillas de requisitos",
            "human": "Crear cuenta y aceptar términos si no existe",
        }
    )
    steps.append(
        {
            "stage": "2. Execución",
            "actions": ["Generar archivos", "Escribir código/docs", "Ejecutar pruebas"],
            "own_ex_delivers": "Genera archivos, código y docs vía herramientas locales",
            "human": "Aprobar el contenido principal",
        }
    )
    qc_actions = ["Revisar requisitos cubiertos", "Eliminar errores", "Verificar formato de entrega"]
    steps.append(
        {
            "stage": "3. Quality Control",
            "actions": qc_actions,
            "own_ex_delivers": "Checklist de cumplimiento + formato",
            "human": "Revisión final del entregable",
        }
    )
    delivery_actions = ["Preparar paquete final", "Redactar mensaje", "Seguir instrucciones de envío"]
    if needs_submission:
        delivery_actions.append("Enviar en la plataforma")
    steps.append(
        {
            "stage": "4. Delivery",
            "actions": delivery_actions,
            "own_ex_delivers": "Paquete listo en disco + mensaje",
            "human": "Clic en Enviar (la entrega es siempre del usuario)" if needs_submission else "Confirmar entrega",
        }
    )
    return steps


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def plan_execution(
    opportunity: dict[str, Any] | Any,
    platform_url: str = "",
    success_probability: float | None = None,
) -> OpportunityPlan:
    """Build an execution plan from a raw opportunity dict or a Work Bank item.

    Direct links are always provided from the opportunity fields + the platform
    URL override (never forces the user to search). Human time is modeled from
    what truly requires the user (account, review, submission); everything else
    is OWNEX automation.
    """
    title = str(_get(opportunity, "title", "") or "Sin título")
    opp_id = str(_get(opportunity, "id", "") or title)
    category = str(_get(opportunity, "category", "") or "")
    platform = str(_get(opportunity, "platform", "") or "")
    url = str(_get(opportunity, "url", "") or "")
    reward = float(_get(opportunity, "reward", 0.0) or 0.0)
    if not reward:
        reward = float(_get(opportunity, "payment", 0.0) or 0.0)
    difficulty = str(_get(opportunity, "difficulty", "") or "")
    skills = list(_get(opportunity, "required_skills", []) or [])
    est_hours = float(_get(opportunity, "estimated_time_hours", 0.0) or 0.0)
    needs_account = bool(_get(opportunity, "needs_account", True))
    registration_required = bool(_get(opportunity, "registration_required", False))
    portfolio_required = bool(_get(opportunity, "portfolio_required", False))

    if not url and platform == "fiverr":
        url = "https://www.fiverr.com/"
    if not url and platform:
        url = platform_url or ""

    base_hours = est_hours or _effort_hours(difficulty, reward, 3.0)
    needs_review = True
    needs_submission = True
    p_success = (
        success_probability
        if success_probability is not None
        else _success_probability(
            reward, has_hard_reqs=portfolio_required, has_experience_reqs=bool(portfolio_required)
        )
    )

    # Human work is only the irreducible personal decisions/actions.
    human_minutes = 0.0
    if needs_account or registration_required:
        human_minutes += 5.0  # account creation
    if needs_review:
        human_minutes += 20.0  # final review
    if needs_submission:
        human_minutes += 5.0  # submission
    remaining_h = max(0.0, round(human_minutes / 60.0, 2))

    autom = _automation_pct(remaining_h, max(base_hours, remaining_h)) if base_hours > 0 else 0

    ev = 0.0
    if remaining_h > 0:
        ev = round((reward * p_success) / remaining_h, 2)

    direct_links: dict[str, str] = {}
    if url:
        direct_links["official_platform"] = url
    if platform:
        direct_links["platform"] = platform
    if url:
        direct_links["direct_task"] = url
    direct_links["documentation"] = platform_url or ""

    return OpportunityPlan(
        opportunity_id=opp_id,
        title=title,
        category=category,
        platform=platform,
        url=url,
        reward_usd=round(reward, 2),
        difficulty=difficulty,
        required_skills=skills,
        success_probability=p_success,
        direct_links=direct_links,
        human_work_minutes=round(human_minutes, 1),
        automation_pct=autom,
        original_hours=base_hours,
        remaining_human_hours=remaining_h,
        expected_value_per_hour=ev,
        roadmap=_roadmap(title, url, needs_account, needs_review, needs_submission),
        next_button="Entrar al plan de entrega del Work Bank"
        if platform and (reward > 0)
        else "Ver documentos y reglas",
        elgibility_note=(
            "Requiere crear cuenta y portfolio" if (needs_account or portfolio_required) else "Sin barreras de acceso"
        ),
    )
