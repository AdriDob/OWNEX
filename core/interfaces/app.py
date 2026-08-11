from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter

from core.interfaces.agent import IAgent
from core.interfaces.scheduler import JobDefinition


@dataclass
class IAppPlugin:
    """Manifest for an application plugin.

    Every app in apps/ MUST expose a module-level ``manifest`` instance.
    """

    id: str  # "atlas"
    name: str  # "ATLAS"
    version: str
    description: str
    icon: str = "AppWindow"  # Lucide icon name
    order: int = 99  # Sort order in sidebar

    # Database
    db_path: str = ""  # Relative to CATEYE_DATA_DIR
    models: list[type] = field(default_factory=list)

    # API
    routers: list[APIRouter] = field(default_factory=list)
    router_prefix: str = ""

    # Scheduler
    scheduler_jobs: list[JobDefinition] = field(default_factory=list)

    # Agent
    agent_class: type[IAgent] | None = None

    # Frontend
    frontend_routes: list[dict] = field(default_factory=list)
    widgets: list[dict] = field(default_factory=list)  # KPIs for home dashboard

    # Integrations
    providers: list[str] = field(default_factory=list)

    # Permissions
    requires_auth: bool = True
    hidden: bool = False  # If True, not shown in sidebar
