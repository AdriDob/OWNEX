"""OWNEX Fiverr Strategic Integration Engine.

Fiverr is a primary long-term revenue ecosystem for OWNEX. The philosophy is:
never sell programming hours, always sell *solutions*. Clients buy outcomes,
not effort — every gig solves one clear technical problem.

The engine does four things:

1. **Gig catalog** — generated, curated service templates (``GigTemplate``) that
   solve one problem each, across the agreed categories (Python automation,
   API/AI integration, bug fixing, browser/desktop automation, data processing,
   developer utilities, Unity/Unreal programming).
2. **Delivery pipeline planning** — every order becomes an ordered plan
   (Requirement analysis -> breakdown -> structure -> implementation -> testing
   -> documentation -> delivery package), reusing the existing AssistedExecutor
   to actually produce the files.
3. **Pricing intelligence** — Starter / Standard / Premium tiers derived from
   difficulty, market demand, delivery time and competition curves, always on a
   single source of truth (no magic numbers).
4. **Reusable asset knowledge base** — every completed order feeds the asset
   ledger so the next delivery is faster. Persistent (survives restarts).

Ethical: original work only, never violate licenses/ToS, never misrepresent
capabilities.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.fiverr")

# ── Single source of truth: gig categories (one problem each) ────────────────

_CATEGORY_SKILLS: dict[str, list[str]] = {
    "python_automation": ["python", "automation", "scripts", "scheduling", "pandas"],
    "api_integration": ["python", "rest", "webhooks", "fastapi", "http"],
    "ai_integration": ["python", "openai", "llm", "rag", "prompting"],
    "bug_fixing": ["python", "javascript", "typescript", "csharp", "java", "cpp"],
    "custom_scripts": ["python", "bash", "cli", "tooling"],
    "desktop_automation": ["python", "windows", "pyautogui", "offce_automation"],
    "browser_automation": ["python", "playwright", "selenium", "scraping"],
    "data_processing": ["python", "pandas", "csv", "excel", "etl"],
    "developer_utilities": ["python", "cli", "templates", "internal_tools"],
    "unity_programming": ["csharp", "unity"],
    "unreal_programming": ["cpp", "unreal"],
}

# Default pricing curves per difficulty/category: (starter, standard, premium).
# Extracted once here so pricing intelligence is auditable, not scattered.
_DEFAULT_PRICE_BANDS: dict[str, list[int]] = {
    "low": [30, 60, 120],
    "mid": [60, 120, 250],
    "high": [150, 300, 600],
    "expert": [400, 800, 1600],
}

# Delivery time table (days) per tier.
_TIER_DELIVERY_DAYS: dict[str, int] = {"starter": 3, "standard": 5, "premium": 10}
_TIER_LABELS: tuple[str, ...] = ("starter", "standard", "premium")


@dataclass(slots=True)
class PricingRecommendation:
    starter: int
    standard: int
    premium: int
    band: str
    delivery_days: dict[str, int] = field(default_factory=lambda: dict(_TIER_DELIVERY_DAYS))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GigTemplate:
    """One solutionable gig: solves exactly one problem."""

    key: str
    title: str
    problem: str
    deliverables: list[str]
    category: str
    tech_skills: list[str]
    estimated_hours: float
    difficulty: str
    demands: list[str] = field(default_factory=list)
    pricing: PricingRecommendation = field(
        default_factory=lambda: PricingRecommendation(starter=0, standard=0, premium=0, band="low")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "pricing": self.pricing.to_dict(),
        }


@dataclass(slots=True)
class OrderPlan:
    """Per-order delivery pipeline plan (requirement -> delivery package)."""

    order_id: str
    gig_key: str
    title: str
    platform: str = "fiverr"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    steps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AssetRecord:
    """A reusable asset produced by a completed order."""

    name: str
    kind: str  # template | library | module | snippet | framework | documentation
    source_order_id: str = ""
    category: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Reusable asset knowledge base (persistent) ───────────────────────────────


class AssetKnowledgeBase:
    """Persistent ledger of reusable assets (templates, libraries, modules...).

    Stored at ``data/fiverr_assets.json``; survives restarts. Every completed
    order should register at least one asset so the next delivery is faster.
    """

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._store_path = Path(store_path or Path(__file__).resolve().parents[3] / "data" / "fiverr_assets.json")
        self._assets: dict[str, AssetRecord] = {}
        self._load()

    def add(self, record: AssetRecord) -> None:
        if not record.name:
            return
        self._assets[record.name] = record
        self._save()

    def add_many(self, records: list[AssetRecord]) -> None:
        for rec in records:
            self.add(rec)

    def count_by_kind(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for rec in self._assets.values():
            counts[rec.kind] = counts.get(rec.kind, 0) + 1
        return counts

    def total(self) -> int:
        return len(self._assets)

    def _load(self) -> None:
        try:
            if not self._store_path.exists():
                return
            data = json.loads(self._store_path.read_text())
            for raw in data.get("assets", []):
                rec = AssetRecord(**raw)
                self._assets[rec.name] = rec
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not load Fiverr asset store: %s", exc)

    def _save(self) -> None:
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            self._store_path.write_text(json.dumps({"assets": [a.to_dict() for a in self._assets.values()]}, indent=2))
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not save Fiverr asset store: %s", exc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_path": str(self._store_path),
            "total_assets": self.total(),
            "by_kind": self.count_by_kind(),
            "assets": [a.to_dict() for a in self._assets.values()],
        }


# ── The engine ────────────────────────────────────────────────────────────────


class FiverrEngine:
    """Strategic integration engine for the Fiverr revenue ecosystem."""

    def __init__(self, knowledge_base: AssetKnowledgeBase | None = None) -> None:
        self.knowledge_base = knowledge_base or AssetKnowledgeBase()

    # ── Gig catalog ──
    def catalog(self, category: str | None = None) -> list[GigTemplate]:
        """Return generated gig templates (optionally filtered by category)."""
        owned = [self._build_gig_template(key, skills) for key, skills in _CATEGORY_SKILLS.items()]
        if category:
            owned = [g for g in owned if g.category == category]
        return owned

    def _build_gig_template(self, key: str, skills: list[str]) -> GigTemplate:
        """Build a single gig template solving one problem (solution, not hours)."""
        first, rest = key.split("_", 1)
        title_map = {
            "python": "Python scripts & workflow automation",
            "api": "API integrations & webhooks (REST, FastAPI)",
            "ai": "AI & LLM integration (OpenAI, RAG, automation)",
            "bug": "Fast debugging & bug fixing (Python/JS/TS/C#/Java/C++)",
            "custom": "Custom scripts & time-saving tools",
            "desktop": "Desktop automation for Windows",
            "browser": "Browser automation (Playwright/Selenium, ToS-compliant)",
            "data": "Data processing, cleaning & analysis",
            "developer": "Developer utilities, CLI tools & templates",
            "unity": "Unity programming (code only, no art)",
            "unreal": "Unreal gameplay systems & optimization (C++ only)",
        }
        title = title_map.get(first, key.replace("_", " "))
        difficulty = self._difficulty(key)
        hours = self._hours(key, difficulty)
        return GigTemplate(
            key=key,
            title=title,
            problem=self._problem(key),
            deliverables=self._deliverables(key),
            category=key,
            tech_skills=skills,
            estimated_hours=hours,
            difficulty=difficulty,
            pricing=self.price(key, difficulty, hours),
        )

    # ── Pricing intelligence ──
    def price(self, gig_key: str, difficulty: str | None = None, hours: float | None = None) -> PricingRecommendation:
        """Recommend Starter/Standard/Premium from difficulty, hours and demand.

        Single source of truth is ``_DEFAULT_PRICE_BANDS``; harder/more central
        gigs sit on a higher band. No magic numbers outside that table.
        """
        band = self._band(difficulty or self._difficulty(gig_key), hours or self._hours(gig_key, None))
        low, mid, high = _DEFAULT_PRICE_BANDS[band]
        return PricingRecommendation(starter=low, standard=mid, premium=high, band=band)

    # ── Delivery pipeline ──
    def plan_order(self, order_id: str, gig_key: str, title: str = "") -> OrderPlan:
        """Create the per-order delivery pipeline plan (Requirement -> package)."""
        gig = next((g for g in self.catalog() if g.key == gig_key), None)
        title = title or (gig.title if gig else gig_key.replace("_", " ").capitalize())

        order_steps = (
            "requirement_analysis",
            "task_breakdown",
            "project_structure",
            "implementation",
            "testing",
            "documentation",
            "delivery_package",
        )
        plan = OrderPlan(order_id=order_id, gig_key=gig_key, title=title)
        plan.steps = [{"step": s, "status": "pending"} for s in order_steps]
        return plan

    async def prepare_delivery(self, opportunity: dict[str, Any], gig_key: str) -> dict[str, Any]:
        """Prepare the delivery package files reusing the existing AssistedExecutor.

        Reuses the established, tested execution layer instead of duplicating a
        submission pipeline (Golden Rule: extend, don't reimplement).
        """
        from core.opportunity.executors.assisted_mode import AssistedExecutor

        order = self.plan_order(str(opportunity.get("id", "")), gig_key, opportunity.get("title", ""))
        executor = AssistedExecutor(base_executor=None)
        prepared = await executor.prepare_work(opportunity)
        work_dir = await executor.save_work_to_disk(prepared)
        return {
            "order_id": order.order_id,
            "gig_key": gig_key,
            "title": order.title,
            "steps": order.steps,
            "files": sorted(prepared.files.keys()),
            "package_path": str(work_dir),
            "submission_url": prepared.submission_url,
            "guide_url": prepared.guide_url,
        }

    # ── Knowledge growth ──
    def record_asset(
        self,
        name: str,
        kind: str = "module",
        source_order_id: str = "",
        category: str = "",
        description: str = "",
    ) -> AssetRecord:
        rec = AssetRecord(
            name=name,
            kind=kind,
            source_order_id=source_order_id,
            category=category,
            description=description,
        )
        self.knowledge_base.add(rec)
        return rec

    def assets(self) -> dict[str, Any]:
        return self.knowledge_base.to_dict()

    # ── Ethics check ──
    @staticmethod
    def validate_deliverable(text: str) -> dict[str, bool]:
        """Simple ethics gate: never plagiarize, never misrepresent.

        Flags obvious red flags in delivery copy so release is intentional.
        """
        checks = {
            "plagiarism_risk": any(s in text.lower() for s in ("copy-paste from ", "stolen ", "download source of ")),
            "overclaim": any(s in text.lower() for s in ("guaranteed ban", "guaranteed 100%", "undetectable")),
            "tos_violation": any(s in text.lower() for s in ("evade anti-bot", "bypass captcha", "instagram bot")),
        }
        checks["passed"] = not any(checks.values())
        return checks

    # ── Helpers (single source of rules) ──
    def _difficulty(self, key: str) -> str:
        if key in ("unity_programming", "unreal_programming", "ai_integration"):
            return "high"
        if key in ("desktop_automation", "browser_automation", "custom_scripts"):
            return "mid"
        return "low"

    def _hours(self, key: str, _: str | None) -> float:
        if key in ("ai_integration", "unreal_programming"):
            return 16.0
        if key in ("unity_programming", "browser_automation", "data_processing", "api_integration"):
            return 8.0
        return 4.0

    def _band(self, difficulty: str, hours: float) -> str:
        if difficulty == "high" or hours >= 16:
            return "expert"
        if difficulty == "mid" or hours >= 8:
            return "high"
        if hours >= 6:
            return "mid"
        return "low"

    def _problem(self, key: str) -> str:
        problems = {
            "python_automation": "Manual repetitive tasks that waste hours every week.",
            "api_integration": "Two systems that do not talk to each other.",
            "ai_integration": "A business that needs AI inside its product, not a chatbot demo.",
            "bug_fixing": "Broken code with no clear next step and no documentation.",
            "custom_scripts": "A repeated manual process that deserves one script.",
            "desktop_automation": "Windows workflows done by hand hundreds of times.",
            "browser_automation": "A boring browser workflow that eats the client's day.",
            "data_processing": "Messy data the client cannot analyze or convert.",
            "developer_utilities": "Missing internal tooling that would save the team hours.",
            "unity_programming": "A game feature that needs real programming, not art.",
            "unreal_programming": "Gameplay systems and optimization that need C++.",
        }
        return problems.get(key, "A clear technical problem that needs solving.")

    def _deliverables(self, key: str) -> list[str]:
        common = ["clean code", "documentation", "installation guide", "examples", "testing notes"]
        extra = {
            "api_integration": ["endpoint documentation", "webhook setup"],
            "ai_integration": ["RAG setup", "prompt templates"],
            "browser_automation": ["robots.txt-compliant script", "headless runner"],
            "data_processing": ["cleaned dataset", "conversion report"],
            "unity_programming": ["C# scripts", "scene integration"],
            "unreal_programming": ["C++ modules", "optimization report"],
        }
        return common + extra.get(key, [])


_fiverr_engine: FiverrEngine | None = None


def get_fiverr_engine() -> FiverrEngine:
    """Process-wide Fiverr engine singleton."""
    global _fiverr_engine
    if _fiverr_engine is None:
        _fiverr_engine = FiverrEngine()
    return _fiverr_engine
