"""Workspace Registry — minimal abstraction for OWNEX workspaces.

Registers 10 workspace types, manages context isolation, and links tasks/opportunities/revenue to workspaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WorkspaceType(StrEnum):
    """Canonical workspace types for OWNEX."""

    OWNEX = "ownex"  # Core development, maintenance, QA, architecture
    BUG_BOUNTY = "bug_bounty"  # Bug bounty operations
    DEV_BOUNTY = "dev_bounty"  # Developer bounties, OSS work, technical tasks
    AI_TRAINING = "ai_training"  # AI training, data annotation, evaluation, coding evaluation
    DROPPINGLABEL = "droppinglabel"  # Instagram + WhatsApp dropshipping (OPTIONAL)
    MERCADO_LIBRE = "mercado_libre"  # Marketplace/dropshipping (OPTIONAL)
    ADRIEL_WEBS = "adriel_webs"  # Web sales via WhatsApp (OPTIONAL)
    CONTENT_FACTORY = "content_factory"  # Shorts/content automation (OPTIONAL)
    TRADING = "trading"  # Stocks + memecoins (CAPITAL only, never base income; PAPER by default)
    BACKUP_INCOME = "backup_income"  # In-person work CABA/Zona Sur (LAST RESORT safety net)


class AutomationPolicy(StrEnum):
    """Automation policy per workspace."""

    DRAFT_ONLY = "draft_only"  # Prepare only, human approves everything
    AUTO_REVERSIBLE = "auto_reversible"  # Auto-execute reversible actions
    HUMAN_APPROVAL_EXTERNAL = "human_approval_external"  # Human gate for external actions


@dataclass(slots=True)
class WorkspaceContext:
    """Isolated context per workspace."""

    workspace_id: str
    workspace_type: WorkspaceType
    name: str
    description: str = ""
    priority: int = 5  # 1-10
    goals: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    automation_policy: AutomationPolicy = AutomationPolicy.DRAFT_ONLY
    active: bool = True

    # Linkage to core entities (by IDs)
    task_ids: set[str] = field(default_factory=set)
    opportunity_ids: set[str] = field(default_factory=set)
    revenue_ids: set[str] = field(default_factory=set)

    # Runtime state
    created_at: str = ""
    updated_at: str = ""


class WorkspaceRegistry:
    """Central registry for workspace management."""

    def __init__(self) -> None:
        self._workspaces: dict[str, WorkspaceContext] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register the 10 canonical workspace types."""
        defaults = [
            ("ownex", WorkspaceType.OWNEX, "OWNEX Core", "Desarrollo, mantenimiento, QA, arquitectura", 10),
            ("bug_bounty", WorkspaceType.BUG_BOUNTY, "Bug Bounty", "Operaciones de bug bounty", 9),
            ("dev_bounty", WorkspaceType.DEV_BOUNTY, "Dev Bounty", "Developer bounties, OSS work, tareas técnicas", 8),
            (
                "ai_training",
                WorkspaceType.AI_TRAINING,
                "AI Training",
                "AI training, data annotation, evaluación, coding evaluation",
                8,
            ),
            ("droppinglabel", WorkspaceType.DROPPINGLABEL, "Droppinglabel", "Instagram + WhatsApp dropshipping", 5),
            ("mercado_libre", WorkspaceType.MERCADO_LIBRE, "Mercado Libre", "Marketplace/dropshipping", 5),
            ("adriel_webs", WorkspaceType.ADRIEL_WEBS, "Adriel Webs", "Venta páginas web vía WhatsApp", 5),
            (
                "content_factory",
                WorkspaceType.CONTENT_FACTORY,
                "Content Factory",
                "Shorts y automatización de contenido",
                5,
            ),
            (
                "trading",
                WorkspaceType.TRADING,
                "Trading",
                "Acciones + memecoins (capital, PAPER default, jamás renta base)",
                4,
            ),
            (
                "backup_income",
                WorkspaceType.BACKUP_INCOME,
                "Backup Income",
                "Trabajo presencial CABA/Zona Sur (último recurso)",
                3,
            ),
        ]
        for ws_id, ws_type, name, desc, priority in defaults:
            ctx = WorkspaceContext(
                workspace_id=ws_id,
                workspace_type=ws_type,
                name=name,
                description=desc,
                priority=priority,
                automation_policy=(
                    AutomationPolicy.AUTO_REVERSIBLE if ws_type == WorkspaceType.OWNEX else AutomationPolicy.DRAFT_ONLY
                ),
            )
            self._workspaces[ws_id] = ctx
        self._seed_real_context()

    def _seed_real_context(self) -> None:
        """Real owner context (verified 2026-09-11). Goals + gates per workspace.

        Content Factory runs $0 (Ollama 3B + Edge TTS + Pexels free) but video
        materials block on a free Pexels/Coverr API key — generation stays
        DRAFT_ONLY until the key lands in MPT config.toml.
        """
        seeds: dict[str, dict[str, Any]] = {
            "droppinglabel": {
                "goals": ["Primera venta con comisión registrada", "Medir comisión promedio por rubro"],
                "settings": {
                    "rubros": ["ropa", "deportiva", "relojes", "perfumes"],
                    "stock_propio": False,
                    "canales": ["instagram", "whatsapp"],
                },
            },
            "mercado_libre": {
                "goals": ["Auditar margen neto real por producto", "Escalar solo winners validados"],
                "settings": {"modelo": "dropshipping", "productos_meta": 100, "regla": "validacion_antes_de_escala"},
            },
            "adriel_webs": {
                "goals": ["Publicar landing + portfolio", "Primer negocio contactado"],
                "settings": {
                    "canales": ["facebook", "whatsapp_personal"],
                    "stack": ["github_pages", "landing", "portfolio"],
                    "oferta": ["negocios_sin_web", "negocios_con_web", "servicio_completo", "mantenimiento"],
                },
            },
            "trading": {
                "goals": ["Paper trading validado sin órdenes reales", "Kill switch probado en max-loss"],
                "settings": {
                    "mode": "paper",
                    "max_position_pct": 5.0,
                    "max_daily_loss_pct": 2.0,
                    "leverage": False,
                    "venues_allowlist": [],
                    "activation": "explicit_human_arm_only",
                },
            },
            "backup_income": {
                "goals": ["Zona + traslado configurados", "Ofertas con salario neto/hora real"],
                "settings": {
                    "zonas": ["CABA", "Zona Sur"],
                    "modalidad": "presencial",
                    "salario_neto_hora": True,
                    "incluye_traslado": True,
                },
            },
            "content_factory": {
                "goals": ["Primer Short EN generado end-to-end", "Serie numerada curiosidad/ciencia"],
                "settings": {
                    "nicho": "curiosidad_ciencia_en",
                    "idioma": "en",
                    "formato": "9:16_35s",
                    "llm": "ollama_qwen2.5:3b-instruct",
                    "tts": "edge_en-US-GuyNeural",
                    "materiales": "pexels_free",
                    "mpt_base_url": "http://127.0.0.1:8081",
                    "blocked_on": "pexels_api_key (gratis, pexels.com/api) o coverr_api_key",
                    "publish": "draft_only_hasta_canal_youtube",
                    "costo": 0,
                },
            },
        }
        for ws_id, seed in seeds.items():
            ctx = self._workspaces.get(ws_id)
            if ctx is None:
                continue
            ctx.goals = seed["goals"]
            ctx.settings.update(seed["settings"])

    def register(self, context: WorkspaceContext) -> None:
        """Register a workspace context."""
        self._workspaces[context.workspace_id] = context

    def get(self, workspace_id: str) -> WorkspaceContext | None:
        """Get workspace by ID."""
        return self._workspaces.get(workspace_id)

    def get_by_type(self, workspace_type: WorkspaceType) -> WorkspaceContext | None:
        """Get workspace by type."""
        for ctx in self._workspaces.values():
            if ctx.workspace_type == workspace_type:
                return ctx
        return None

    def list_all(self) -> list[WorkspaceContext]:
        """List all workspaces."""
        return list(self._workspaces.values())

    def list_active(self) -> list[WorkspaceContext]:
        """List only active workspaces."""
        return [ctx for ctx in self._workspaces.values() if ctx.active]

    def activate(self, workspace_id: str) -> bool:
        """Activate a workspace."""
        ctx = self._workspaces.get(workspace_id)
        if ctx:
            ctx.active = True
            return True
        return False

    def deactivate(self, workspace_id: str) -> bool:
        """Deactivate a workspace."""
        ctx = self._workspaces.get(workspace_id)
        if ctx:
            ctx.active = False
            return True
        return False

    def link_task(self, workspace_id: str, task_id: str) -> bool:
        """Link a task to workspace."""
        ctx = self._workspaces.get(workspace_id)
        if ctx:
            ctx.task_ids.add(task_id)
            return True
        return False

    def unlink_task(self, workspace_id: str, task_id: str) -> bool:
        """Unlink a task from workspace."""
        ctx = self._workspaces.get(workspace_id)
        if ctx:
            ctx.task_ids.discard(task_id)
            return True
        return False

    def link_opportunity(self, workspace_id: str, opportunity_id: str) -> bool:
        """Link an opportunity to workspace."""
        ctx = self._workspaces.get(workspace_id)
        if ctx:
            ctx.opportunity_ids.add(opportunity_id)
            return True
        return False

    def link_revenue(self, workspace_id: str, revenue_id: str) -> bool:
        """Link a revenue entry to workspace."""
        ctx = self._workspaces.get(workspace_id)
        if ctx:
            ctx.revenue_ids.add(revenue_id)
            return True
        return False

    def get_linked_tasks(self, workspace_id: str) -> set[str]:
        """Get task IDs linked to workspace."""
        ctx = self._workspaces.get(workspace_id)
        return ctx.task_ids if ctx else set()

    def get_linked_opportunities(self, workspace_id: str) -> set[str]:
        """Get opportunity IDs linked to workspace."""
        ctx = self._workspaces.get(workspace_id)
        return ctx.opportunity_ids if ctx else set()

    def get_linked_revenue(self, workspace_id: str) -> set[str]:
        """Get revenue IDs linked to workspace."""
        ctx = self._workspaces.get(workspace_id)
        return ctx.revenue_ids if ctx else set()

    def update_settings(self, workspace_id: str, settings: dict[str, Any]) -> bool:
        """Update workspace settings."""
        ctx = self._workspaces.get(workspace_id)
        if ctx:
            ctx.settings.update(settings)
            return True
        return False

    def set_automation_policy(self, workspace_id: str, policy: AutomationPolicy) -> bool:
        """Set automation policy for workspace."""
        ctx = self._workspaces.get(workspace_id)
        if ctx:
            ctx.automation_policy = policy
            return True
        return False


# Singleton
_workspace_registry: WorkspaceRegistry | None = None


def get_workspace_registry() -> WorkspaceRegistry:
    """Get singleton workspace registry."""
    global _workspace_registry
    if _workspace_registry is None:
        _workspace_registry = WorkspaceRegistry()
    return _workspace_registry
