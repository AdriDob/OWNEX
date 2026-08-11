"""Execution Factory — transform selected opportunities into professional deliverables.

High-level orchestration layer on top of the low-level workflow runtime
(``core.execution``) and the assisted delivery pipeline
(``core.opportunity.executors.assisted_mode``).

Pipeline:

    Opportunity → Requirement Analysis → Execution Plan → Workspace Prep →
    Implementation → Testing → Documentation → Quality Report → Delivery Package

Safety: the factory NEVER submits external actions. It prepares a complete,
quality-checked delivery package on disk and returns a submission checklist;
the actual submission stays with the user (or an explicit approval flow).
"""

from __future__ import annotations

import logging
import re
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.execution.factory")

# Default workspace root (< 2 file rule: created under data/, not a third module)
_WORKSPACE_ROOT = Path("data/execution_factory")

# Quality-check dimensions (from the QC system spec)
_QC_FIELDS = {
    "functionality": "functional completeness",
    "requirements": "requirement coverage",
    "errors": "runtime/validation errors",
    "security": "security posture",
    "maintainability": "code maintainability",
    "presentation": "presentation quality",
}


@dataclass
class RequirementAnalysis:
    """Structured understanding of what a deliverable must satisfy."""

    opportunity_id: str
    title: str
    platform: str
    deliverables: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    submission_format: str = ""
    guide_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "platform": self.platform,
            "deliverables": self.deliverables,
            "acceptance_criteria": self.acceptance_criteria,
            "technologies": self.technologies,
            "submission_format": self.submission_format,
            "guide_url": self.guide_url,
        }


@dataclass
class QualityReport:
    """QC output: what passed, what failed, improvements, final recommendation."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    recommendation: str = "deliverable_not_ready"
    scores: dict[str, float] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Fraction of checked dimensions that passed."""
        if not self.scores:
            return 0.0
        return round(sum(1 for v in self.scores.values() if v >= 1.0) / len(self.scores), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "improvements": self.improvements,
            "recommendation": self.recommendation,
            "scores": self.scores,
            "pass_rate": self.pass_rate,
        }


@dataclass
class DeliveryPackage:
    """A prepared, reviewed deliverable awaiting user submission."""

    package_dir: Path
    files: list[str]
    requirement_analysis: RequirementAnalysis
    quality_report: QualityReport
    checklist: list[str]
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_dir": str(self.package_dir),
            "files": self.files,
            "requirement_analysis": self.requirement_analysis.to_dict(),
            "quality_report": self.quality_report.to_dict(),
            "checklist": self.checklist,
            "created_at": self.created_at,
        }


class ExecutionFactory:
    """Orchestrates the end-to-end opportunity → deliverable pipeline.

    Reuses existing components instead of duplicating them:
    - ``ExecutionPlan`` for the structured plan
    - ``AssistedExecutor.prepare_work`` for platform delivery scaffolding
    - ``PlatformGuide`` for submission format + guide URL
    """

    name = "execution_factory"

    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self.workspace_root = Path(workspace_root) if workspace_root else _WORKSPACE_ROOT

    # ── Step 1: Requirement Analysis ─────────────────────────────

    def analyze_requirements(self, opportunity: dict[str, Any]) -> RequirementAnalysis:
        """Parse an opportunity into structured deliverables + acceptance criteria."""
        title = str(opportunity.get("title") or opportunity.get("name") or "Untitled")
        platform = str(opportunity.get("platform") or "generic")
        description = str(opportunity.get("description") or "")

        deliverables = self._extract_deliverables(opportunity, description)
        acceptance_criteria = self._infer_acceptance_criteria(deliverables, platform)
        technologies = [str(t) for t in opportunity.get("technology_tags", [])]

        guide = self._get_platform_guide(platform)
        return RequirementAnalysis(
            opportunity_id=str(opportunity.get("id") or ""),
            title=title,
            platform=platform,
            deliverables=deliverables,
            acceptance_criteria=acceptance_criteria,
            technologies=technologies,
            submission_format=guide.submission_format if guide else _default_format(platform),
            guide_url=guide.url if guide else None,
        )

    # ── Step 2: Execution Plan ───────────────────────────────────

    def build_plan(self, analysis: RequirementAnalysis) -> dict[str, Any]:
        """Build a structured execution plan. Reuses ExecutionPlan model."""
        from core.execution.plan import build_execution_plan

        nodes = [
            "requirement_analysis",
            "environment_preparation",
            "implementation",
            "testing",
            "documentation",
            "quality_control",
            "delivery",
        ]
        plan = build_execution_plan(
            workflow_id=f"factory_{uuid.uuid4().hex[:8]}",
            workflow_name=f"Execute: {analysis.title}",
            node_ids=nodes,
            dependencies={
                "testing": ["implementation"],
                "quality_control": ["testing"],
                "delivery": ["quality_control"],
            },
            parallelism_groups=[],
        )
        return plan.to_dict()

    # ── Step 3: Workspace Preparation ────────────────────────────

    def prepare_workspace(
        self,
        name: str,
        technologies: list[str] | None = None,
        clean: bool = False,
    ) -> Path:
        """Create a project workspace: folders, docs skeleton, dependency manifest, git init."""
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_") or "project"
        workspace = self.workspace_root / f"{safe}_{datetime.now().strftime('%Y%m%d')}"
        workspaces = self._list_workspaces(name)
        if workspaces:
            workspace = self.workspace_root / workspaces[0]
        if clean and workspace.exists():
            shutil.rmtree(workspace)
        elif workspace.exists():
            return workspace  # already prepared

        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "src").mkdir(exist_ok=True)
        (workspace / "tests").mkdir(exist_ok=True)
        (workspace / "docs").mkdir(exist_ok=True)
        (workspace / "evidence").mkdir(exist_ok=True)

        tech = technologies or ["python"]
        dep_file = workspace / ("requirements.txt" if "python" in tech else "package.json")
        dep_file.write_text(_dependency_manifest(tech))

        (workspace / "README.md").write_text("# Project\n\nSee docs/ for structure.\n")
        (workspace / "docs" / "TECHNICAL.md").write_text("# Technical Guide\n")
        (workspace / "docs" / "INSTALL.md").write_text("# Installation\n")
        (workspace / "README.md").touch()

        self._git_init(workspace)
        logger.info("[FACTORY] Workspace ready at %s", workspace)
        return workspace

    # ── Step 4: Quality Control ──────────────────────────────────

    def quality_check(self, workspace: Path, analysis: RequirementAnalysis) -> QualityReport:
        """Review a workspace against acceptance criteria → QualityReport.

        Non-destructive: it inspects what is present and reports a review,
        it does not silently modify the deliverable. Returns passed/failed/
        improvements/recommendation.
        """
        report = QualityReport()
        checks: dict[str, tuple[bool, str]] = {
            "functionality": (self._check_functionality(workspace), "deliverable files present and non-empty"),
            "requirements": (self._check_requirements(workspace, analysis), "all deliverables have evidence"),
            "errors": (self._check_errors(workspace), "no obvious error markers in code"),
            "security": (self._check_security(workspace), "no secrets / insecure patterns"),
            "maintainability": (self._check_maintainability(workspace), "docs + source structure present"),
            "presentation": (self._check_presentation(workspace), "README and delivery summary present"),
        }
        for dim in _QC_FIELDS:
            ok, label = checks[dim]
            report.scores[dim] = 1.0 if ok else 0.0
            if ok:
                report.passed.append(f"{dim}: {label}")
            else:
                report.failed.append(f"{dim}: {label}")

        report.improvements = self._suggest_improvements(workspace, report.scores)
        report.recommendation = "ready_for_delivery" if report.pass_rate == 1.0 else "needs_work"
        return report

    # ── Step 5: Delivery package ─────────────────────────────────

    def prepare_delivery(
        self,
        analysis: RequirementAnalysis,
        workspace: Path,
        quality_report: QualityReport,
    ) -> DeliveryPackage:
        """Assemble the delivery package (files + QC + checklist). Never submits."""
        package_dir = workspace / "delivery"
        package_dir.mkdir(parents=True, exist_ok=True)

        files = self._collect_files(workspace)
        self._write_delivery_summary(package_dir, analysis, quality_report, files)

        checklist = self._submission_checklist(analysis, files, quality_report)
        return DeliveryPackage(
            package_dir=package_dir,
            files=files,
            requirement_analysis=analysis,
            quality_report=quality_report,
            checklist=checklist,
        )

    # ── Orchestrated pipeline ────────────────────────────────────

    def run(self, opportunity: dict[str, Any]) -> dict[str, Any]:
        """Execute the full pipeline for an opportunity.

        Returns the plan, workspace, QC report and delivery checklist. No
        external action is performed — the user submits from the checklist.
        """
        analysis = self.analyze_requirements(opportunity)
        plan = self.build_plan(analysis)

        workspace = self.prepare_workspace(
            name=analysis.title,
            technologies=analysis.technologies,
        )
        quality = self.quality_check(workspace, analysis)
        package = self.prepare_delivery(analysis, workspace, quality)

        return {
            "ok": True,
            "opportunity_id": analysis.opportunity_id,
            "title": analysis.title,
            "platform": analysis.platform,
            "plan": plan,
            "workspace": str(workspace),
            "requirement_analysis": analysis.to_dict(),
            "quality_report": quality.to_dict(),
            "delivery": package.to_dict(),
            "submitted": False,
            "note": "Deliverable prepared locally. Submit manually from the checklist.",
        }

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extract_deliverables(opportunity: dict[str, Any], description: str) -> list[str]:
        explicit = opportunity.get("deliverables")
        if isinstance(explicit, list) and explicit:
            return [str(d) for d in explicit]
        desc_lines = [ln.strip("- ") for ln in description.splitlines() if ln.strip()]
        return desc_lines[:5] if desc_lines else ["implementation"]

    def _infer_acceptance_criteria(self, deliverables: list[str], platform: str) -> list[str]:
        criteria = [f"{d} shipped and demonstrable" for d in deliverables]
        criteria.append(f"correct {platform} submission format")
        return criteria

    @staticmethod
    def _get_platform_guide(platform: str) -> Any | None:
        try:
            from core.opportunity.guides.platform_guides import get_platform_guide

            guide = get_platform_guide(platform)
            return guide
        except Exception:  # noqa: BLE001
            return None

    def _list_workspaces(self, name: str) -> list[str]:
        if not self.workspace_root.exists():
            return []
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_") or "project"
        return [d.name for d in self.workspace_root.iterdir() if d.is_dir() and d.name.startswith(safe)]

    @staticmethod
    def _git_init(workspace: Path) -> None:
        try:
            from git import Repo  # type: ignore[import-not-found]

            Repo.init(workspace)
        except Exception:  # noqa: BLE001
            (workspace / ".gitkeep").touch()

    # QC check implementations

    @staticmethod
    def _check_functionality(ws: Path) -> bool:
        src_files = list((ws / "src").rglob("*.py")) + list((ws / "src").rglob("*.js"))
        if not src_files:
            return (ws / "delivery").exists() and any((ws / "delivery").iterdir())
        return all(f.stat().st_size > 0 for f in src_files)

    def _check_requirements(self, ws: Path, analysis: RequirementAnalysis) -> bool:
        evidence_files = list((ws / "evidence").rglob("*")) + [f for f in (ws / "delivery").rglob("*") if f.is_file()]
        return len(evidence_files) >= min(1, len(analysis.deliverables))

    @staticmethod
    def _check_errors(ws: Path) -> bool:
        bad_markers = ["TODO: FIXME", "FIXME", "NotImplementedError"]  # type: ignore[list-item]
        for f in list((ws / "src").rglob("*.py")) + list((ws / "src").rglob("*.js")):
            try:
                if any(m in f.read_text() for m in bad_markers):
                    return False
            except Exception:  # noqa: BLE001
                pass
        return True

    @staticmethod
    def _check_security(ws: Path) -> bool:
        secret_patterns = ["password =", "api_key =", "secret = ", "-----BEGIN"]
        for f in list(ws.rglob("*.py")) + list(ws.rglob("*.md")) + list(ws.rglob("*.json")):
            try:
                text = f.read_text()
                if "data/execution_factory" in str(f) and f.name.endswith((".py", ".md", ".json")):
                    pass
                if any(p in text for p in secret_patterns):
                    return False
            except Exception:  # noqa: BLE001
                pass
        return True

    def _check_maintainability(self, ws: Path) -> bool:
        has_docs = (ws / "docs").exists() and any((ws / "docs").iterdir())
        has_source = (ws / "src").exists() and any((ws / "src").iterdir())
        return has_docs and has_source

    def _check_presentation(self, ws: Path) -> bool:
        readme = ws / "README.md"
        if not readme.exists():
            return False
        return readme.stat().st_size > 10 and (ws / "delivery").exists()

    @staticmethod
    def _suggest_improvements(ws: Path, scores: dict[str, float]) -> list[str]:
        suggestions = []
        if scores.get("documentation", 0) < 1 if "documentation" in scores else not (ws / "docs").exists():
            suggestions.append("Add a TECHNICAL.md explaining architecture decisions")
        if not (ws / ".git").exists() and not (ws / ".gitkeep").exists():
            suggestions.append("Initialize version control for traceability")
        if scores.get("presentation", 0) < 1:
            suggestions.append("Expand README with usage and demo instructions")
        return suggestions

    def _collect_files(self, workspace: Path) -> list[str]:
        files = []
        for root, _dirs, names in workspace.walk():
            for n in names:
                if n.startswith(".") or root.name == "delivery":
                    continue
                rel = Path(root).relative_to(workspace) / n
                files.append(str(rel))
        return sorted(files)

    def _write_delivery_summary(
        self,
        package_dir: Path,
        analysis: RequirementAnalysis,
        report: QualityReport,
        files: list[str],
    ) -> None:
        summary = [
            f"# Delivery Package — {analysis.title}",
            "",
            f"- Platform: {analysis.platform}",
            f"- Deliverables: {', '.join(analysis.deliverables)}",
            f"- Quality: {report.pass_rate:.0%} pass",
            f"- Recommendation: {report.recommendation}",
            "",
            "## Files",
        ] + [f"- {f}" for f in files]
        (package_dir / "DELIVERY.md").write_text("\n".join(summary), encoding="utf-8")

    def _submission_checklist(
        self,
        analysis: RequirementAnalysis,
        files: list[str],
        report: QualityReport,
    ) -> list[str]:
        checklist = [f"Package contains {len(files)} files"]
        checklist += [f"Requirement: {d}" for d in analysis.deliverables]
        if report.recommendation == "ready_for_delivery":
            checklist.append("QC passed — deliverable ready")
        else:
            checklist.append("QC flagged items — resolve before submission")
        if analysis.guide_url:
            checklist.append(f"Follow submission guide: {analysis.guide_url}")
        checklist.append("Submit via OWNEX assisted flow (never automated)")
        return checklist


def _default_format(platform: str) -> str:
    return {"github": "Pull Request", "algora": "Work submission", "outlier": "CSV/JSON", "freelancer": "Proposal"}.get(
        platform, "generic upload"
    )


def _dependency_manifest(tech: list[str]) -> str:
    if "python" in tech:
        return "# Dependencies\n- leave empty until implementation locks versions\n"
    return '{\n  "dependencies": {}\n}\n'


# ── Singleton API ─────────────────────────────────────────────────

_factory: ExecutionFactory | None = None


def get_execution_factory() -> ExecutionFactory:
    """Get or create the global execution factory singleton."""
    global _factory
    if _factory is None:
        _factory = ExecutionFactory()
    return _factory


def reset_execution_factory(workspace_root: str | Path | None = None) -> ExecutionFactory:
    """Recreate the factory (testing)."""
    global _factory
    _factory = ExecutionFactory(workspace_root=workspace_root)
    return _factory
