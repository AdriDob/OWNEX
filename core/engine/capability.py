"""Capability Engine — knows what OWNEX can do.

Not "what models" or "what tools". WHAT CAPABILITIES.
Tools implement capabilities. The engine matches opportunity requirements
to available capabilities and tells the Planner what's feasible.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from core.engine.base import Engine

logger = logging.getLogger("ownex.capability")


@dataclass
class Capability:
    """A capability is something OWNEX can do.

    Not a tool. A capability. Tools implement capabilities.
    """

    id: str  # "web_scraping", "code_execution", "git_ops"
    name: str  # "Web Scraping"
    description: str
    category: str  # "data_collection", "analysis", "execution"

    # Tools that provide this capability
    providers: list[str] = field(default_factory=list)

    # Models that are good at this
    preferred_models: list[str] = field(default_factory=list)

    # Required credentials
    required_credentials: list[str] = field(default_factory=list)

    # Cost estimation
    estimated_cost_per_run: float = 0.0
    estimated_time_per_run: int = 60  # seconds

    # Availability
    available: bool = True
    requires_user: bool = False  # needs user approval


BUILTIN_CAPABILITIES: dict[str, dict[str, Any]] = {
    "web_scraping": {
        "name": "Web Scraping",
        "description": "Fetch and parse web pages, APIs, RSS feeds",
        "category": "data_collection",
        "providers": ["httpx", "urllib", "playwright", "feedparser"],
        "estimated_cost_per_run": 0.001,
    },
    "code_execution": {
        "name": "Code Execution",
        "description": "Execute Python, Node.js, shell scripts",
        "category": "execution",
        "providers": ["pipeline_engine", "agent_registry"],
        "estimated_cost_per_run": 0.01,
    },
    "git_operations": {
        "name": "Git Operations",
        "description": "Clone, pull, commit, push, create PR",
        "category": "execution",
        "providers": ["shell"],
        "estimated_cost_per_run": 0.001,
    },
    "browser_automation": {
        "name": "Browser Automation",
        "description": "Control browser for JS-heavy sites, form filling, screenshots",
        "category": "data_collection",
        "providers": ["playwright"],
        "estimated_cost_per_run": 0.01,
        "estimated_time_per_run": 300,
    },
    "llm_reasoning": {
        "name": "LLM Reasoning",
        "description": "Use AI models for analysis, planning, classification, generation",
        "category": "analysis",
        "providers": ["provider_router"],
        "estimated_cost_per_run": 0.02,
    },
    "document_parsing": {
        "name": "Document Parsing",
        "description": "Parse PDF, DOCX, HTML, Markdown, JSON, YAML",
        "category": "data_collection",
        "providers": ["pymupdf", "python-docx", "beautifulsoup4"],
        "estimated_cost_per_run": 0.001,
    },
    "api_interaction": {
        "name": "API Interaction",
        "description": "Call REST APIs, handle auth, pagination, rate limiting",
        "category": "data_collection",
        "providers": ["httpx"],
        "estimated_cost_per_run": 0.001,
    },
    "network_scanning": {
        "name": "Network Scanning",
        "description": "Port scanning, subdomain discovery, technology fingerprinting",
        "category": "analysis",
        "providers": ["nmap", "nuclei", "httpx_tools"],
        "requires_user": True,
        "estimated_cost_per_run": 0.05,
    },
    "ocr": {
        "name": "OCR",
        "description": "Extract text from images, screenshots, scanned documents",
        "category": "data_collection",
        "providers": ["tesseract"],
        "estimated_cost_per_run": 0.01,
    },
    "automation_scripting": {
        "name": "Automation Scripting",
        "description": "Write and execute automation scripts in bash, Python",
        "category": "execution",
        "providers": ["pipeline_engine"],
        "estimated_cost_per_run": 0.001,
    },
}


# ── Source-type → capability mapping ────────────────────────────


TYPE_REQUIREMENTS: dict[str, list[str]] = {
    "bug_bounty": ["web_scraping", "api_interaction", "network_scanning", "llm_reasoning", "git_operations"],
    "dev_bounty": ["git_operations", "code_execution", "api_interaction"],
    "ai_work": ["code_execution", "document_parsing", "llm_reasoning"],
    "microtask": ["browser_automation", "automation_scripting"],
    "freelance": ["all"],
    "oss_sponsor": ["git_operations", "code_execution"],
    "job_application": ["browser_automation", "document_parsing"],
}


# ── Capability Engine ────────────────────────────────────────────


class CapabilityEngine(Engine):
    """Matches opportunity requirements to OWNEX capabilities.

    The Planner asks: "What do I need to execute this opportunity?"
    CapabilityEngine answers: "These N capabilities, available via these providers."
    """

    name = "capability_engine"

    def __init__(self) -> None:
        super().__init__()
        self._capabilities: dict[str, Capability] = {}
        self._register_builtin()

    def _register_builtin(self) -> None:
        for cap_id, attrs in BUILTIN_CAPABILITIES.items():
            self._capabilities[cap_id] = Capability(id=cap_id, **attrs)

    def register(self, capability: Capability) -> None:
        """Register a new capability (e.g. from a plugin)."""
        self._capabilities[capability.id] = capability

    def get(self, capability_id: str) -> Capability | None:
        return self._capabilities.get(capability_id)

    def list_all(self) -> dict[str, Capability]:
        return dict(self._capabilities)

    def list_by_category(self, category: str) -> list[Capability]:
        return [c for c in self._capabilities.values() if c.category == category]

    def list_by_availability(self, available_only: bool = True) -> list[Capability]:
        if not available_only:
            return list(self._capabilities.values())
        return [c for c in self._capabilities.values() if c.available]

    def match_opportunity(
        self,
        source_type: str,
    ) -> list[Capability]:
        """Match an opportunity's source_type to required capabilities.

        Returns a list of Capability objects required for this type.
        """
        required_ids = TYPE_REQUIREMENTS.get(source_type, ["llm_reasoning"])

        if "all" in required_ids:
            return list(self._capabilities.values())

        return [self._capabilities[r] for r in required_ids if r in self._capabilities]

    def can_execute(self, source_type: str) -> tuple[bool, list[str]]:
        """Check if OWNEX has all capabilities for a source_type.

        Returns (can_execute, missing_capability_ids).
        """
        required = self.match_opportunity(source_type)
        missing = [cap.id for cap in required if not cap.available]
        return len(missing) == 0, missing

    async def initialize(self) -> None:
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        total = len(self._capabilities)
        available = sum(1 for c in self._capabilities.values() if c.available)
        return {
            "status": "ok",
            "name": self.name,
            "capabilities": total,
            "available": available,
            "categories": list({c.category for c in self._capabilities.values()}),
        }
