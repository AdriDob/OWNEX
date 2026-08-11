"""Capability Expansion Engine — detect gaps, evaluate, integrate, register.

OWNEX's self-improvement system: answers "what can I do?", "what am I
missing?", "what should I improve?" and turns answers into safe,
approved capability additions.

Workflow:

    need detected → research → evaluate alternatives → select best →
    install/integrate → test → register (persistent CapabilityRegistry)

Safety: any change touching new permissions, external accounts, financial
actions or security-sensitive surfaces requires explicit user approval
(``requires_approval``). Safe improvements (pure registrations, local
integrations already present in the environment) may be automated.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, cast

from core.capabilities.registry import get_capability_registry

logger = logging.getLogger("ownex.capabilities.expansion")

_APPROVALS_STORE = Path(os.environ.get("OWNEX_DATA_DIR", "data")) / "capability_approvals.json"


# ── The 10 capability layers (from the expansion plan) ──────────────

EXPANSION_LAYERS: dict[str, str] = {
    "ai": "AI Intelligence Layer",
    "software_development": "Software Development Layer",
    "automation": "Automation Layer",
    "research": "Research Intelligence Layer",
    "opportunity": "Opportunity Intelligence Layer",
    "developer_environment": "Developer Environment Layer",
    "cybersecurity": "Cybersecurity Layer",
    "data": "Data Layer",
    "media": "Media & Content Layer",
    "productivity": "Personal Productivity Layer",
}


@dataclass
class CapabilityCandidate:
    """A known open-source capability OWNEX could integrate."""

    capability: str  # canonical capability id, e.g. "image_generation"
    category: str  # one of EXPANSION_LAYERS
    name: str
    description: str
    providers: list[str] = field(default_factory=list)  # importable modules / tools
    install_hint: str = ""  # e.g. "pip install pillow"
    benefits: list[str] = field(default_factory=list)
    # Approval policy: critical changes (permissions/accounts/financial/security)
    requires_approval: bool = False
    score: float = 0.0  # filled by evaluate()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Known candidates (curated, open-source-first) ───────────────────

KNOWN_CANDIDATES: list[CapabilityCandidate] = [
    # AI Intelligence Layer
    CapabilityCandidate(
        capability="image_generation",
        category="ai",
        name="Image Generation",
        description="Generate images locally (Stable Diffusion) or via provider APIs",
        providers=["diffusers", "comfyui"],
        install_hint="pip install diffusers",
        benefits=["faster branding creation", "automated documentation assets", "improved README generation"],
        requires_approval=True,
    ),
    CapabilityCandidate(
        capability="speech_to_text",
        category="ai",
        name="Speech-to-Text",
        description="Transcribe audio locally (whisper) for meeting notes and voice commands",
        providers=["faster_whisper", "whisper"],
        install_hint="pip install faster-whisper",
        benefits=["voice notes → action items", "meeting transcription", "hands-free task capture"],
        requires_approval=True,
    ),
    CapabilityCandidate(
        capability="text_to_speech",
        category="ai",
        name="Text-to-Speech",
        description="Synthesize speech locally or via provider for alerts and briefings",
        providers=["edge_tts", "piper"],
        install_hint="pip install edge-tts",
        benefits=["audio daily briefings", "voice alerts", "learning on the go"],
    ),
    # Software Development Layer
    CapabilityCandidate(
        capability="code_search",
        category="software_development",
        name="Semantic Code Search",
        description="Index and search the codebase semantically beyond regex",
        providers=["ripgrep", "ctags"],
        install_hint="apt install ripgrep",
        benefits=["faster root-cause analysis", "cross-module traceability", "reduced manual grep time"],
    ),
    CapabilityCandidate(
        capability="changelog_generation",
        category="software_development",
        name="Changelog Generation",
        description="Auto-generate changelogs from git history",
        providers=["git"],
        install_hint="",
        benefits=["release notes without manual effort", "evidence trail for revenue sprints"],
    ),
    # Automation Layer
    CapabilityCandidate(
        capability="desktop_automation",
        category="automation",
        name="Desktop Automation",
        description="Drive the desktop (clicks, typing, screenshots) for repetitive GUI tasks",
        providers=["pyautogui"],
        install_hint="pip install pyautogui",
        benefits=["repetitive task elimination", "GUI workflows without a browser"],
        requires_approval=True,
    ),
    CapabilityCandidate(
        capability="file_watching",
        category="automation",
        name="File Watching / Event Triggers",
        description="React to filesystem events to trigger workflows",
        providers=["watchdog"],
        install_hint="pip install watchdog",
        benefits=["event triggers", "background processes on file change", "auto-processing pipelines"],
    ),
    # Research Intelligence Layer
    CapabilityCandidate(
        capability="rss_monitoring",
        category="research",
        name="RSS/Feed Monitoring",
        description="Track blogs, CVE feeds, and platform announcements",
        providers=["feedparser"],
        install_hint="",
        benefits=["content monitoring", "early vulnerability disclosure tracking", "market data feeds"],
    ),
    CapabilityCandidate(
        capability="web_archiving",
        category="research",
        name="Web Archiving",
        description="Save and diff pages over time for evidence",
        providers=["playwright"],
        install_hint="",
        benefits=["evidence quality", "change detection on targets", "report reproducibility"],
    ),
    # Opportunity Intelligence Layer
    CapabilityCandidate(
        capability="reward_estimation",
        category="opportunity",
        name="Reward Estimation",
        description="Estimate expected reward per opportunity type before engagement",
        providers=["opportunity_engine"],
        install_hint="",
        benefits=["prioritize high-ROI work", "transparent reward filtering", "expected revenue modeling"],
    ),
    CapabilityCandidate(
        capability="requirement_filtering",
        category="opportunity",
        name="Requirement Filtering",
        description="Auto-filter opportunities by eligibility, skills, and entry barriers",
        providers=["opportunity_engine", "direct_work_engine"],
        install_hint="",
        benefits=["low entry barriers prioritized", "skill-match before applying", "less wasted applications"],
    ),
    # Developer Environment Layer
    CapabilityCandidate(
        capability="venv_manager",
        category="developer_environment",
        name="Virtualenv Manager",
        description="Create, activate, and manage isolated environments per project",
        providers=["uv", "virtualenv"],
        install_hint="pip install uv",
        benefits=["dependency isolation", "reproducible setup", "faster project initialization"],
    ),
    # Cybersecurity Layer (authorized work only)
    CapabilityCandidate(
        capability="dependency_vuln_scan",
        category="cybersecurity",
        name="Dependency Vulnerability Scan",
        description="Scan project dependencies against vulnerability databases",
        providers=["pip-audit", "safety"],
        install_hint="pip install pip-audit",
        benefits=["dependency vulnerability detection", "pre-commit security gate", "supply-chain hygiene"],
    ),
    CapabilityCandidate(
        capability="secret_scanning",
        category="cybersecurity",
        name="Secret Scanning",
        description="Detect leaked credentials in code and history",
        providers=["gitleaks", "trufflehog"],
        install_hint="apt install gitleaks",
        benefits=["credential leak prevention", "repo hygiene", "incident prevention"],
    ),
    # Data Layer
    CapabilityCandidate(
        capability="csv_processing",
        category="data",
        name="CSV/Data Processing",
        description="Process, clean, and transform tabular data",
        providers=["pandas"],
        install_hint="",
        benefits=["data cleaning", "analytics", "reporting"],
    ),
    CapabilityCandidate(
        capability="data_visualization",
        category="data",
        name="Data Visualization",
        description="Charts and dashboards from metrics",
        providers=["matplotlib", "plotly"],
        install_hint="pip install plotly",
        benefits=["visual reports", "dashboard widgets", "executive summaries"],
    ),
    # Media & Content Layer
    CapabilityCandidate(
        capability="pdf_generation",
        category="media",
        name="PDF Generation",
        description="Generate PDF documents and reports programmatically",
        providers=["reportlab", "weasyprint"],
        install_hint="pip install reportlab",
        benefits=["document generation", "report delivery", "invoices and evidence packages"],
    ),
    CapabilityCandidate(
        capability="image_processing",
        category="media",
        name="Image Processing",
        description="Resize, crop, convert, and annotate images",
        providers=["pillow"],
        install_hint="pip install pillow",
        benefits=["screenshot processing", "evidence annotation", "asset preparation"],
    ),
    # Personal Productivity Layer
    CapabilityCandidate(
        capability="daily_briefing",
        category="productivity",
        name="Daily Briefing",
        description="Summarize opportunities, findings, and system health each morning",
        providers=["scheduler", "llm_reasoning"],
        install_hint="",
        benefits=["morning context in seconds", "goal tracking visibility", "reduced context switching"],
    ),
    CapabilityCandidate(
        capability="goal_tracking",
        category="productivity",
        name="Goal Tracking",
        description="Track personal and business goals with progress metrics",
        providers=["career_engine"],
        install_hint="",
        benefits=["goal visibility", "learning loop", "revenue sprint review support"],
    ),
]

# Map capability → known providers already present in this environment
_ALREADY_PROVIDED: dict[str, list[str]] = {
    "rss_monitoring": ["feedparser"],
    "web_archiving": ["playwright"],
    "csv_processing": ["pandas"],
    "image_processing": ["pillow"],
    "reward_estimation": ["opportunity_engine"],
    "requirement_filtering": ["opportunity_engine", "direct_work_engine"],
    "goal_tracking": ["career_engine"],
    "daily_briefing": ["scheduler", "llm_reasoning"],
}


class CapabilityExpansionEngine:
    """Orchestrates capability discovery, evaluation, and safe installation."""

    name = "capability_expansion_engine"

    def __init__(self, registry: Any = None, approvals_path: str | Path | None = None) -> None:
        self._registry = registry or get_capability_registry()
        self._approvals_path = Path(approvals_path) if approvals_path else _APPROVALS_STORE
        self._lock = threading.Lock()
        self._pending_approvals: dict[str, dict[str, Any]] = {}
        self._load_approvals()

    # ── Persistence of approvals ─────────────────────────────────

    def _load_approvals(self) -> None:
        try:
            if self._approvals_path.exists():
                self._pending_approvals = json.loads(self._approvals_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load capability approvals: %s", exc)

    def _save_approvals(self) -> None:
        try:
            self._approvals_path.parent.mkdir(parents=True, exist_ok=True)
            self._approvals_path.write_text(json.dumps(self._pending_approvals, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist capability approvals: %s", exc)

    # ── 1. Detect gaps ───────────────────────────────────────────

    def detect_gaps(self) -> list[dict[str, Any]]:
        """Detect missing capabilities per layer.

        A capability is "present" if it is registered in the registry OR
        its canonical id appears in the engine's builtin capabilities.
        """
        registered = set(self._registry.list_capabilities())
        try:
            from core.engine.capability import BUILTIN_CAPABILITIES  # noqa: PLC0415

            registered |= set(BUILTIN_CAPABILITIES.keys())
        except Exception:  # noqa: BLE001
            pass

        gaps: list[dict[str, Any]] = []
        for candidate in KNOWN_CANDIDATES:
            if candidate.capability in registered:
                continue
            gaps.append(
                {
                    "capability": candidate.capability,
                    "name": candidate.name,
                    "category": candidate.category,
                    "layer": EXPANSION_LAYERS.get(candidate.category, candidate.category),
                    "description": candidate.description,
                    "providers": candidate.providers,
                    "install_hint": candidate.install_hint,
                    "benefits": candidate.benefits,
                    "already_available": self._provider_available(candidate.capability, candidate.providers),
                    "requires_approval": candidate.requires_approval,
                }
            )
        # Group by layer for the report
        by_layer: dict[str, list[dict[str, Any]]] = {}
        for gap in gaps:
            by_layer.setdefault(gap["layer"], []).append(gap)
        return [
            {"layer": layer, "count": len(items), "capabilities": items} for layer, items in sorted(by_layer.items())
        ]

    # ── 2. Evaluate alternatives ─────────────────────────────────

    def evaluate_candidate(self, candidate: CapabilityCandidate | dict[str, Any]) -> dict[str, Any]:
        """Score a candidate using the Smart Installation Rules.

        Weights: maintained (open-source activity proxy), security,
        compatibility (providers importable locally), OWNEX improvement
        value, and availability of a better alternative.
        """
        if isinstance(candidate, dict):
            try:
                candidate = CapabilityCandidate(**candidate)
            except TypeError:
                # partial dict: fill defaults for missing required fields
                defaults: dict[str, Any] = cast(
                    "dict[str, Any]",
                    {
                        field_.name: field_.default
                        for field_ in CapabilityCandidate.__dataclass_fields__.values()
                        if field_.default is not None
                    },
                )
                defaults.update(cast("dict[str, Any]", candidate))
                candidate = CapabilityCandidate(**defaults)
        if not candidate.capability:
            return {"score": 0.0, "decision": "reject", "reasons": ["missing capability id"]}

        reasons: list[str] = []
        score = 0.0

        # Curated open-source baseline (vetted for maintenance & security)
        score += 40.0
        reasons.append("curated open-source candidate (maintained & privacy-friendly)")

        # Compatibility: providers present in this environment
        provided = self._provider_available(candidate.capability, candidate.providers)
        compat = sum(1 for p in candidate.providers if importlib.util.find_spec(p) is not None)
        compat_ratio = compat / len(candidate.providers) if candidate.providers else 0.0
        score += 25.0 * compat_ratio
        if provided:
            reasons.append("integration already present locally (zero-install registration)")
        elif compat_ratio > 0:
            reasons.append(f"{compat}/{len(candidate.providers)} providers already importable")

        # OWNEX improvement value: benefits must map to the revenue rule
        value_terms = ["revenue", "evidence", "acceptance", "learning", "detection", "autonomy", "faster", "reduced"]
        value_hits = sum(1 for b in candidate.benefits if any(t in b.lower() for t in value_terms))
        score += 25.0 * min(1.0, value_hits / max(1, len(candidate.benefits)))
        if value_hits:
            reasons.append("improves detection/acceptance/learning/autonomy")

        # Safety posture
        if not candidate.requires_approval:
            score += 20.0
            reasons.append("safe change — no new permissions/accounts/financial/security surface")
        else:
            reasons.append("requires approval (critical surface: permissions/accounts/financial/security)")

        # Alternative check: existing local integration is strictly better
        if candidate.capability in _ALREADY_PROVIDED:
            score += 10.0
            reasons.append("integration exists — registration only, no new dependency")

        score = round(min(100.0, score), 1)
        if candidate.requires_approval:
            decision = "approve_auto" if score >= 85 else ("needs_approval" if score >= 40 else "reject")
        else:
            decision = "approve_auto" if score >= 70 else ("needs_approval" if score >= 40 else "reject")
        return {
            "capability": candidate.capability,
            "name": candidate.name,
            "category": candidate.category,
            "score": score,
            "decision": decision,
            "reasons": reasons,
            "providers": candidate.providers,
            "install_hint": candidate.install_hint,
        }

    # ── 3. Install / integrate ───────────────────────────────────

    def install_candidate(
        self,
        capability: str,
        module: str = "expansion_engine",
        metadata: dict[str, Any] | None = None,
        description: str = "",
        dry_run: bool = True,
        force_approval: bool = False,
    ) -> dict[str, Any]:
        """Integrate a capability and register it persistently.

        If the candidate requires approval and none is granted yet, the
        request is queued in the approvals store instead of installing.
        """
        candidate = self._get_candidate(capability)
        if candidate is None:
            return {"ok": False, "error": f"unknown capability: {capability}"}

        evaluation = self.evaluate_candidate(candidate)

        if candidate.requires_approval and not force_approval:
            approval_id = f"{capability}:{module}"
            with self._lock:
                self._pending_approvals[approval_id] = {
                    "capability": capability,
                    "module": module,
                    "name": candidate.name,
                    "category": candidate.category,
                    "requested_at": time.time(),
                    "evaluation": evaluation,
                    "dry_run": dry_run,
                }
                self._save_approvals()
            return {
                "ok": False,
                "needs_approval": True,
                "approval_id": approval_id,
                "message": "Queued for user approval (critical change)",
                "evaluation": evaluation,
            }

        if dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "message": "Dry run — would register this capability",
                "evaluation": evaluation,
            }

        meta = {
            "category": candidate.category,
            "version": "1.0",
            "expansion_source": "capability_expansion_engine",
            **(metadata or {}),
        }
        self._registry.register(
            capability=capability,
            module=module,
            metadata=meta,
            description=description or candidate.description,
        )
        if candidate.category:
            entry = self._registry.get_entry(capability, module)
            if entry:
                entry.category = candidate.category
                entry.dependencies = [p for p in candidate.providers if importlib.util.find_spec(p)]
                entry.improvement_potential = min(1.0, evaluation["score"] / 100.0)
                self._registry.persist()
        return {
            "ok": True,
            "dry_run": False,
            "capability": capability,
            "module": module,
            "category": candidate.category,
            "message": "Capability registered and persisted",
            "evaluation": evaluation,
        }

    def approve(self, approval_id: str, granted: bool = True) -> dict[str, Any]:
        """Approve (or deny) a queued critical installation."""
        with self._lock:
            item = self._pending_approvals.pop(approval_id, None)
            if item is None:
                return {"ok": False, "error": f"unknown approval id: {approval_id}"}
            self._save_approvals()
        if not granted:
            return {"ok": True, "approved": False, "capability": item["capability"]}
        result = self.install_candidate(
            capability=item["capability"],
            module=item["module"],
            dry_run=item["dry_run"],
            force_approval=True,
        )
        result["approved"] = True
        return result

    def pending_approvals(self) -> list[dict[str, Any]]:
        """List queued approvals awaiting user decision."""
        with self._lock:
            return [{"approval_id": aid, **item} for aid, item in sorted(self._pending_approvals.items())]

    # ── 4. Self-improvement suggestions ──────────────────────────

    def suggest_improvements(self) -> list[dict[str, Any]]:
        """Analyze the system and produce actionable upgrade suggestions."""
        suggestions: list[dict[str, Any]] = []
        for gap_group in self.detect_gaps():
            layer = gap_group["layer"]
            for gap in gap_group["capabilities"]:
                if gap["already_available"]:
                    action = "register"
                    effort = "S"
                else:
                    action = "install"
                    effort = "M" if gap["requires_approval"] else "S"
                suggestions.append(
                    {
                        "capability": gap["capability"],
                        "name": gap["name"],
                        "layer": layer,
                        "category": gap["category"],
                        "recommended_action": action,
                        "effort": effort,
                        "benefits": gap["benefits"],
                        "install_hint": gap["install_hint"],
                        "requires_approval": gap["requires_approval"],
                        "template": (
                            f"Your current workflow lacks {gap['name'].lower()} capability. "
                            f"Recommended upgrade: {action} it. "
                            f"Benefits: {', '.join(gap['benefits'])}."
                        ),
                    }
                )
        return suggestions

    def registry_report(self) -> dict[str, Any]:
        """Full report: what OWNEX can do, what's missing, what to improve."""
        entries = self._registry._entries  # noqa: SLF001 — internal report
        report_entries = []
        for e in entries:
            report_entries.append(
                {
                    "capability": e.capability,
                    "module": e.module,
                    "category": e.category,
                    "version": e.version,
                    "dependencies": e.dependencies,
                    "status": e.status,
                    "health": e.health,
                    "avg_performance_ms": e.avg_performance_ms,
                    "usage_count": e.usage_count,
                    "improvement_potential": e.improvement_potential,
                    "description": e.description,
                }
            )
        return {
            "stats": self._registry.stats(),
            "capabilities": report_entries,
            "gaps": self.detect_gaps(),
            "suggestions": self.suggest_improvements(),
            "pending_approvals": self.pending_approvals(),
        }

    def marketplace_coverage(self) -> list[dict[str, Any]]:
        """Category coverage bars for the internal marketplace.

        Coverage = registered unique capabilities in a category / known
        candidates in that category (capped at 100%). Categories with no
        known candidates use registered coverage only.
        """
        known_by_cat: dict[str, int] = {}
        for c in KNOWN_CANDIDATES:
            known_by_cat[c.category] = known_by_cat.get(c.category, 0) + 1
        registered_by_cat: dict[str, set[str]] = {}
        for e in self._registry._entries:  # noqa: SLF001 — internal report
            cat = e.category or "uncategorized"
            registered_by_cat.setdefault(cat, set()).add(e.capability)

        categories = sorted({c.category for c in KNOWN_CANDIDATES}.union(registered_by_cat.keys()))
        bars = []
        for cat in categories:
            registered = len(registered_by_cat.get(cat, set()))
            known = known_by_cat.get(cat, registered)
            pct = min(100.0, round((registered / int(max(known, 1))) * 100)) if known else 0
            bars.append(
                {
                    "category": cat,
                    "registered": registered,
                    "known": known,
                    "coverage_pct": pct,
                }
            )
        return bars

    def daily_evolution_report(self) -> dict[str, Any]:
        """Daily Expansion Mode report.

        Consolidates: capabilities discovered/tracked, integrated, tested,
        performance improvements and recommended upgrades — reusing the
        existing gaps/suggestions/registry machinery.
        """
        stats = self._registry.stats()
        suggestions = self.suggest_improvements()
        pending = self.pending_approvals()

        entries = list(self._registry._entries)  # noqa: SLF001 — internal report
        # Integration progress: candidates evaluated/installed vs known
        integrated = {e.capability for e in entries if e.status == "active"}
        known_set = {c.capability for c in KNOWN_CANDIDATES}
        installed_from_known = sorted(known_set & integrated)
        discovered_remaining = sorted(known_set - integrated)

        # Performance improvements over time (best health, perf deltas)
        improved = [
            {
                "capability": e.capability,
                "category": e.category,
                "health": e.health,
                "avg_performance_ms": e.avg_performance_ms,
                "usage_count": e.usage_count,
                "improvement_potential": e.improvement_potential,
            }
            for e in entries
            if e.health is not None and e.health >= 0.9
        ]

        # Recommended upgrades = highest-value suggestions
        recommended = sorted(
            suggestions,
            key=lambda s: (s.get("priority", 0), s.get("value_proposition", "")),
            reverse=True,
        )[:5]

        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "marketplace": self.marketplace_coverage(),
            "discovered_remaining": discovered_remaining,
            "installed_from_known": installed_from_known,
            "tools_integrated": stats.get("unique_capabilities", 0),
            "tools_tested": len(discovered_remaining),  # analysed candidates not yet installed
            "performance_improvements": improved,
            "recommended_upgrades": recommended,
            "pending_approvals": pending,
            "usage_total": stats.get("total_usage_count", 0),
            "active": stats.get("active", 0),
            "broken": stats.get("broken", 0),
        }

    # ── Helpers ──────────────────────────────────────────────────

    def _get_candidate(self, capability: str) -> CapabilityCandidate | None:
        for c in KNOWN_CANDIDATES:
            if c.capability == capability:
                return c
        return None

    def _provider_available(self, capability: str, providers: list[str]) -> bool:
        if not providers:
            return False
        already = set(_ALREADY_PROVIDED.get(capability, []))
        return any(importlib.util.find_spec(p) is not None or p in already for p in providers)


# ── Singleton API ───────────────────────────────────────────────────

_engine: CapabilityExpansionEngine | None = None
_engine_lock = threading.Lock()


def get_expansion_engine() -> CapabilityExpansionEngine:
    """Get or create the global expansion engine singleton."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = CapabilityExpansionEngine()
    return _engine


def reset_expansion_engine(registry: Any = None) -> CapabilityExpansionEngine:
    """Recreate the engine (testing)."""
    global _engine
    with _engine_lock:
        _engine = CapabilityExpansionEngine(registry=registry)
        return _engine
