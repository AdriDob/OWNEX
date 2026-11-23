"""CoderAgent — Main orchestrator for autonomous code fixing.

The CoderAgent is the "brain" that:
1. Clones repository into a unique per-task workspace
2. Analyzes issue
3. Generates fix and applies it BEFORE validation
4. Runs tests inside a verified sandbox (fail-closed, no host fallback)
5. Builds a local delivery package and waits for owner approval
6. ``publish_delivery`` creates the PR only after explicit owner action
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.autonomy.code_generator import CodeChange, CodeGenerator, GenerationPlan
from core.autonomy.issue_analyzer import IssueAnalysis, IssueAnalyzer
from core.autonomy.pr_builder import PRBuilder, PRResult, create_pr_from_plan
from core.autonomy.repo_analyzer import RepoAnalyzer, RepoInfo
from core.autonomy.test_runner import TestRunner, TestRunSummary
from core.security.sandbox import Sandbox

logger = logging.getLogger("ownex.autonomy.coder_agent")

# Sandbox images per detected language. Anything unmapped falls back to the
# configured default; a missing toolchain surfaces as an honest test failure.
_SANDBOX_IMAGES = {
    "python": "python:3.12-slim",
    "javascript": "node:22-slim",
    "typescript": "node:22-slim",
    "go": "golang:1.23",
    "rust": "rust:1.85",
}


def _default_delivery_dir() -> Path:
    """Data-dir aware delivery packages root (same pattern as the queue)."""
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "delivery_packages"


def _safe_name(value: str) -> str:
    """Filesystem-safe single path component."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "task"


@dataclass
class CoderAgentResult:
    """Result of a full CoderAgent run."""

    success: bool
    issue_id: str
    platform: str

    # Phase results
    repo_cloned: bool = False
    repo_info: RepoInfo | None = None
    issue_analysis: IssueAnalysis | None = None
    generation_plan: GenerationPlan | None = None
    test_results: TestRunSummary | None = None
    pr_result: PRResult | None = None

    # Delivery package (local, pre-approval). pr_result stays None until
    # publish_delivery() runs after explicit owner approval.
    delivery_package: str | None = None
    workspace_path: str | None = None
    patch_path: str | None = None

    # Metrics
    total_duration_seconds: float = 0.0
    phases_duration: dict[str, float] = field(default_factory=dict)

    # Learning
    verdict: str | None = None  # merged, rejected, tests_failed, error
    feedback: str | None = None

    error: str | None = None


@dataclass
class CoderAgentConfig:
    """Configuration for CoderAgent."""

    # Model to use for code generation
    model: str = "claude-sonnet-4"

    # Timeouts
    clone_timeout: int = 120
    analysis_timeout: int = 60
    generation_timeout: int = 120
    test_timeout: int = 300
    pr_timeout: int = 60

    # Behavior
    max_iterations: int = 3  # Retry fix if tests fail
    min_confidence_for_pr: float = 0.6
    # Workspaces are preserved for owner review by default; the delivery
    # package (patch + evidence) lives outside the clone.
    cleanup_repo: bool = False
    run_lint: bool = True

    # Security: untrusted repo code NEVER runs on the host. When no verified
    # Docker daemon is available the task ends BLOCKED, not degraded.
    require_sandbox: bool = True
    sandbox_image: str | None = None  # override; else per-language map/default
    delivery_dir: Path | None = None

    # Platform-specific
    platform_configs: dict[str, dict[str, Any]] = field(default_factory=dict)


class CoderAgent:
    """Main orchestrator for autonomous code fixing."""

    def __init__(self, config: CoderAgentConfig | None = None):
        self.config = config or CoderAgentConfig()

        # Initialize sub-components
        self.repo_analyzer = RepoAnalyzer()
        self.issue_analyzer = IssueAnalyzer()
        self.code_generator = CodeGenerator()
        self.pr_builder = PRBuilder()

        # Work directory
        self.work_dir = Path(tempfile.gettempdir()) / "ownex_coder_agent"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        # Verified sandbox for all untrusted-code execution (B6: fail closed)
        self._sandbox = Sandbox()
        self.test_runner = TestRunner(sandbox=self._sandbox if self.config.require_sandbox else None)

    async def solve_issue(
        self,
        issue_data: dict[str, Any],
        repo_url: str | None = None,
        platform: str = "unknown",
    ) -> CoderAgentResult:
        """Main entry point: solve an issue end-to-end.

        Args:
            issue_data: Raw issue data from platform (Algora, Opire, GitHub, etc.)
            repo_url: Repository URL (if not in issue_data)
            platform: Platform name (algora, opire, issuehunt, github, freelancer, etc.)

        Returns:
            CoderAgentResult with all phase results
        """
        start_time = time.time()
        result = CoderAgentResult(
            success=False,
            issue_id=issue_data.get("id", issue_data.get("number", "unknown")),
            platform=platform,
        )

        repo_path = None

        try:
            # ============================================================
            # PHASE 0: SANDBOX GATE (fail closed — B6)
            # ============================================================
            # Untrusted repository code must never execute on the host. If no
            # verified container runtime is available the task is BLOCKED for
            # manual review instead of degrading to a host subprocess.
            if self.config.require_sandbox and not await self._sandbox.is_ready():
                result.error = (
                    "sandbox_unavailable: no verified container runtime; "
                    "external code execution refused (fail-closed)"
                )
                result.verdict = "blocked"
                return self._finalize_result(result, start_time, repo_path)

            # ============================================================
            # PHASE 1: CLONE REPOSITORY (unique per-task workspace — B3)
            # ============================================================
            phase_start = time.time()
            repo_url = repo_url or issue_data.get("repository_url") or issue_data.get("repo_url")
            if not repo_url:
                raise ValueError("No repository URL provided")

            ws_name = _safe_name(f"{result.issue_id}_{uuid.uuid4().hex[:8]}")
            clone_result = await self.repo_analyzer.clone_repo(repo_url, dest_name=ws_name)
            result.phases_duration["clone"] = time.time() - phase_start

            if not clone_result.success:
                raise RuntimeError(f"Clone failed: {clone_result.error}")

            # The clone result path is the SOLE source of truth (B3).
            clone_path = (clone_result.data or {}).get("path")
            if not clone_path:
                raise RuntimeError("Clone succeeded but returned no path")
            repo_path = Path(clone_path)
            work_root = self.repo_analyzer.work_dir.resolve()
            if not repo_path.resolve().is_relative_to(work_root) or not repo_path.is_dir():
                raise RuntimeError(f"Clone path outside workspace root: {repo_path}")

            result.repo_cloned = True
            result.workspace_path = str(repo_path)
            result.repo_info = await self.repo_analyzer.analyze_repo(repo_path)
            self._configure_sandbox_image(result.repo_info)

            # ============================================================
            # PHASE 2: ANALYZE ISSUE
            # ============================================================
            phase_start = time.time()
            # Add platform to issue data
            issue_data["platform"] = platform
            analysis_result = self.issue_analyzer.analyze_issue(issue_data, result.repo_info)
            result.phases_duration["analysis"] = time.time() - phase_start

            if not analysis_result.success:
                raise RuntimeError(f"Issue analysis failed: {analysis_result.error}")

            issue_analysis = analysis_result.data.get("analysis")
            if issue_analysis is None:
                raise RuntimeError("Issue analysis returned no data")
            result.issue_analysis = issue_analysis

            # ============================================================
            # PHASE 3: GENERATE FIX
            # ============================================================
            phase_start = time.time()
            gen_result = await self.code_generator.generate_fix(
                result.issue_analysis,
                result.repo_info,
            )
            result.phases_duration["generation"] = time.time() - phase_start

            if not gen_result.success:
                raise RuntimeError(f"Code generation failed: {gen_result.error}")

            generation_plan = gen_result.data.get("plan")
            if generation_plan is None:
                raise RuntimeError("Code generation returned no plan")
            result.generation_plan = generation_plan

            # Check confidence threshold
            if result.generation_plan.estimated_confidence < self.config.min_confidence_for_pr:
                result.error = f"Confidence too low: {result.generation_plan.estimated_confidence:.0%} < {self.config.min_confidence_for_pr:.0%}"
                result.verdict = "low_confidence"
                return self._finalize_result(result, start_time, repo_path)

            # ============================================================
            # PHASE 3b: APPLY PATCH BEFORE VALIDATION (B4)
            # ============================================================
            # Tests must run against the MODIFIED workspace, not the pristine
            # clone. Path traversal / escapes outside the repo root are
            # rejected before anything is written.
            await self._apply_plan_changes(repo_path, result.generation_plan)
            patch_path = self._snapshot_patch(repo_path, result)
            result.patch_path = str(patch_path) if patch_path else None

            # ============================================================
            # PHASE 4: RUN TESTS (iterative, sandboxed — B6)
            # ============================================================
            phase_start = time.time()
            test_success = await self._run_tests_with_retries(
                repo_path,
                result.repo_info,
                result.generation_plan,
                result,
            )
            result.phases_duration["testing"] = time.time() - phase_start

            if not test_success:
                result.error = "Tests failed after retries"
                result.verdict = "tests_failed"
                return self._finalize_result(result, start_time, repo_path)

            # ============================================================
            # PHASE 5: LOCAL DELIVERY PACKAGE — NO EXTERNAL PR (B5)
            # ============================================================
            # External publication (PR / bounty claim / submission) requires
            # explicit owner approval via publish_delivery(). The autonomous
            # stage ends at WAITING_HUMAN-equivalent: package ready for review.
            phase_start = time.time()
            delivery_dir = self._build_delivery_package(result, repo_path)
            result.phases_duration["delivery_package"] = time.time() - phase_start
            result.delivery_package = str(delivery_dir)

            # ============================================================
            # SUCCESS (review-ready, NOT submitted)
            # ============================================================
            result.success = True
            result.verdict = "ready_for_owner_review"
            result.feedback = f"Delivery package ready: {delivery_dir} — awaiting owner approval to publish"

            return self._finalize_result(result, start_time, repo_path)

        except Exception as e:
            result.error = str(e)
            result.verdict = "error"
            return self._finalize_result(result, start_time, repo_path)

    def _configure_sandbox_image(self, repo_info: RepoInfo) -> None:
        """Pick the container image for the detected language (best effort)."""
        language = (repo_info.language or "unknown").lower()
        image = self.config.sandbox_image or _SANDBOX_IMAGES.get(language)
        if image:
            self._sandbox.config.DOCKER_IMAGE = image

    async def _install_dependencies_sandbox(self, repo_path: Path, repo_info: RepoInfo) -> bool:
        """Install deps inside the sandbox. Network is enabled ONLY here —
        package registries are unreachable otherwise. Returns success."""
        command = repo_info.build_command
        if not command:
            return True  # nothing to install
        result = await self._sandbox.execute(
            repo_path,
            ["sh", "-c", command],
            timeout=600,
            writable=True,
            network=True,
        )
        return result.success

    async def _run_tests_with_retries(
        self,
        repo_path: Path,
        repo_info: RepoInfo,
        plan: GenerationPlan,
        result: CoderAgentResult,
    ) -> bool:
        """Run tests with retries, regenerating fix if needed."""
        for iteration in range(self.config.max_iterations):
            # Install dependencies first (sandboxed; untrusted code — B6).
            # Failure is not necessarily fatal — deps may already be present.
            await self._install_dependencies_sandbox(repo_path, repo_info)

            # Run tests (sandboxed via TestRunner when configured)
            test_summary = await self.test_runner.run_tests(repo_path, repo_info=repo_info)
            result.test_results = test_summary

            if test_summary.overall_success:
                return True

            # Sandbox-level failure (no runtime) is not a code failure —
            # surface it as blocked instead of burning retries on the patch.
            best = test_summary.best_result
            if best and "fail-closed" in (best.stderr or ""):
                result.error = f"sandbox_unavailable: {best.stderr[:300]}"
                result.verdict = "blocked"
                return False

            # Tests failed - try to regenerate fix with test feedback
            if iteration < self.config.max_iterations - 1:
                # Add test failure info to issue analysis for next iteration
                failure_info = self._extract_test_failures(test_summary)
                if failure_info:
                    result.issue_analysis.body += f"\n\n--- Test Failures (iteration {iteration + 1}) ---\n{failure_info}"
                    # Regenerate
                    gen_result = await self.code_generator.generate_fix(
                        result.issue_analysis,
                        repo_info,
                    )
                    if gen_result.success:
                        plan = gen_result.data["plan"]
                        result.generation_plan = plan
                        # Apply new changes (same traversal guard)
                        await self._apply_plan_changes(repo_path, plan)
                        self._snapshot_patch(repo_path, result)

        return False

    def _extract_test_failures(self, test_summary: TestRunSummary) -> str:
        """Extract useful failure information from test results."""
        if not test_summary.results:
            return ""

        result = test_summary.results[0]
        output = result.stdout + "\n" + result.stderr

        # Keep last 2000 chars of output (most relevant)
        return output[-2000:]

    async def _apply_plan_changes(self, repo_path: Path, plan: GenerationPlan) -> None:
        """Apply all changes from a generation plan.

        Every target must resolve INSIDE the repository root — absolute paths
        and ``..`` traversal are rejected before anything is written (B4).
        """
        repo_root = repo_path.resolve()
        for change in (*plan.changes, *plan.test_changes):
            raw = Path(change.file_path)
            target = raw if raw.is_absolute() else repo_root / raw
            resolved = target.resolve()
            if not resolved.is_relative_to(repo_root):
                raise ValueError(f"plan change escapes repository root: {change.file_path}")
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(change.new_content, encoding="utf-8")

    def _snapshot_patch(self, repo_path: Path, result: CoderAgentResult) -> Path | None:
        """Persist the applied patch + changed-file list as review evidence.

        Runs ``git add -A`` + ``git diff --cached`` on the clone BEFORE tests
        run, so test artifacts (caches, pycache) never pollute the patch.
        Returns the patch file path or None when git is unavailable.
        """
        try:
            subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True, capture_output=True, timeout=60)
            diff = subprocess.run(
                ["git", "diff", "--cached", "--binary"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                timeout=60,
            ).stdout.decode("utf-8", errors="replace")
            names = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                timeout=60,
            ).stdout.decode().split()
        except Exception as e:
            logger.warning("patch snapshot failed for %s: %s", result.issue_id, e)
            return None

        if not diff.strip():
            return None

        out_dir = self._delivery_root() / _safe_name(f"{result.issue_id}_{result.platform}")
        out_dir.mkdir(parents=True, exist_ok=True)
        patch_path = out_dir / "patch.diff"
        patch_path.write_text(diff, encoding="utf-8")
        (out_dir / "changed_files.json").write_text(json.dumps(names, indent=2))
        result.patch_path = str(patch_path)
        return patch_path

    def _delivery_root(self) -> Path:
        return self.config.delivery_dir or _default_delivery_dir()

    def _build_delivery_package(self, result: CoderAgentResult, repo_path: Path) -> Path:
        """Assemble the local review package: patch, plan, test evidence, metadata."""
        pkg_dir = self._delivery_root() / _safe_name(
            f"{result.issue_id}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"
        )
        pkg_dir.mkdir(parents=True, exist_ok=True)

        plan = result.generation_plan
        if plan is not None:
            (pkg_dir / "plan.json").write_text(
                json.dumps(self._serialize_plan(plan), indent=2, default=str),
                encoding="utf-8",
            )
        if result.test_results is not None:
            (pkg_dir / "test_results.json").write_text(
                json.dumps(dataclasses.asdict(result.test_results), indent=2, default=str),
                encoding="utf-8",
            )

        metadata = {
            "issue_id": result.issue_id,
            "platform": result.platform,
            "workspace_path": str(repo_path),
            "patch_path": result.patch_path,
            "repo_info": self._serialize_repo_info(result.repo_info) if result.repo_info else None,
            "phases_duration": result.phases_duration,
            "created_at": datetime.now(UTC).isoformat(),
            "verdict": result.verdict,
            "approval_required": True,
            "note": "Local package only. No PR/claim/submission performed. "
            "Run publish_delivery() after explicit owner approval.",
        }
        (pkg_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return pkg_dir

    # ── Serialization helpers for publish_delivery ──

    @staticmethod
    def _serialize_change(change: CodeChange) -> dict[str, Any]:
        return {
            "file_path": str(change.file_path),
            "original_content": change.original_content,
            "new_content": change.new_content,
            "change_type": change.change_type,
            "description": change.description,
            "confidence": change.confidence,
        }

    @staticmethod
    def _deserialize_change(data: dict[str, Any]) -> CodeChange:
        return CodeChange(
            file_path=Path(data["file_path"]),
            original_content=data.get("original_content", ""),
            new_content=data["new_content"],
            change_type=data.get("change_type", "fix"),
            description=data.get("description", ""),
            confidence=data.get("confidence", 0.8),
        )

    @classmethod
    def _serialize_plan(cls, plan: GenerationPlan) -> dict[str, Any]:
        return {
            "issue_analysis": dataclasses.asdict(plan.issue_analysis),
            "repo_info": cls._serialize_repo_info(plan.repo_info),
            "changes": [cls._serialize_change(c) for c in plan.changes],
            "test_changes": [cls._serialize_change(c) for c in plan.test_changes],
            "summary": plan.summary,
            "estimated_confidence": plan.estimated_confidence,
        }

    @staticmethod
    def _serialize_repo_info(info: RepoInfo) -> dict[str, Any]:
        return {
            "path": str(info.path),
            "language": info.language,
            "package_manager": info.package_manager,
            "test_command": info.test_command,
            "build_command": info.build_command,
            "dev_command": info.dev_command,
            "framework": info.framework,
            "entry_points": info.entry_points,
            "test_files": [str(p) for p in info.test_files],
            "config_files": {k: str(v) for k, v in info.config_files.items()},
            "git_remote": info.git_remote,
            "default_branch": info.default_branch,
        }

    @staticmethod
    def _deserialize_repo_info(data: dict[str, Any]) -> RepoInfo:
        return RepoInfo(
            path=Path(data["path"]),
            language=data.get("language", "unknown"),
            package_manager=data.get("package_manager"),
            test_command=data.get("test_command"),
            build_command=data.get("build_command"),
            dev_command=data.get("dev_command"),
            framework=data.get("framework"),
            entry_points=data.get("entry_points", []),
            test_files=[Path(p) for p in data.get("test_files", [])],
            config_files={k: Path(v) for k, v in data.get("config_files", {}).items()},
            git_remote=data.get("git_remote"),
            default_branch=data.get("default_branch", "main"),
        )

    @classmethod
    def _deserialize_plan(cls, data: dict[str, Any]) -> GenerationPlan:
        issue_data = data["issue_analysis"]
        return GenerationPlan(
            issue_analysis=IssueAnalysis(**issue_data),
            repo_info=cls._deserialize_repo_info(data["repo_info"]),
            changes=[cls._deserialize_change(c) for c in data.get("changes", [])],
            test_changes=[cls._deserialize_change(c) for c in data.get("test_changes", [])],
            summary=data.get("summary", ""),
            estimated_confidence=data.get("estimated_confidence", 0.5),
        )

    async def publish_delivery(self, delivery_dir: str | Path, approved_by: str = "owner") -> PRResult:
        """Publish a reviewed delivery package — OWNER-APPROVED ACTION ONLY.

        This is the single external-commitment boundary: it creates/pushes a
        PR (or platform submission) for a package that already passed local
        validation. Callers MUST record explicit owner approval first.
        """
        pkg = Path(delivery_dir)
        plan_data = json.loads((pkg / "plan.json").read_text(encoding="utf-8"))
        metadata = json.loads((pkg / "metadata.json").read_text(encoding="utf-8"))

        plan = self._deserialize_plan(plan_data)
        repo_info = plan.repo_info
        if not repo_info.path.is_dir():
            return PRResult(success=False, error=f"workspace gone: {repo_info.path}")

        platform = metadata.get("platform") or "github"
        result = await create_pr_from_plan(plan, repo_info, platform=platform)
        if result.success:
            (pkg / "PUBLISHED.json").write_text(
                json.dumps(
                    {
                        "pr_url": result.pr_url,
                        "pr_number": result.pr_number,
                        "branch_name": result.branch_name,
                        "approved_by": approved_by,
                        "published_at": datetime.now(UTC).isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        return result

    def _finalize_result(
        self,
        result: CoderAgentResult,
        start_time: float,
        repo_path: Path | None,
    ) -> CoderAgentResult:
        """Finalize result with timing and cleanup."""
        result.total_duration_seconds = time.time() - start_time

        # Cleanup
        if self.config.cleanup_repo and repo_path and repo_path.exists():
            with contextlib.suppress(Exception):
                shutil.rmtree(repo_path, ignore_errors=True)

        return result

    async def solve_batch(
        self,
        issues: list[dict[str, Any]],
        platform: str = "unknown",
    ) -> list[CoderAgentResult]:
        """Solve multiple issues in parallel (limited concurrency)."""
        semaphore = asyncio.Semaphore(2)  # Max 2 concurrent

        async def solve_one(issue: dict[str, Any]) -> CoderAgentResult:
            async with semaphore:
                return await self.solve_issue(issue, platform=platform)

        tasks = [solve_one(issue) for issue in issues]
        return await asyncio.gather(*tasks, return_exceptions=True)


# Convenience function for simple usage
async def solve_issue(
    issue_data: dict[str, Any],
    repo_url: str | None = None,
    platform: str = "unknown",
    config: CoderAgentConfig | None = None,
) -> CoderAgentResult:
    """Simple function to solve an issue."""
    agent = CoderAgent(config)
    return await agent.solve_issue(issue_data, repo_url, platform)


# Platform-specific entry points
async def solve_algora_issue(
    issue_data: dict[str, Any],
    config: CoderAgentConfig | None = None,
) -> CoderAgentResult:
    """Solve an Algora bounty issue."""
    repo_url = issue_data.get("repository", {}).get("html_url") or issue_data.get("repo_url")
    return await solve_issue(issue_data, repo_url, "algora", config)


async def solve_opire_issue(
    issue_data: dict[str, Any],
    config: CoderAgentConfig | None = None,
) -> CoderAgentResult:
    """Solve an Opire bounty issue."""
    repo_url = issue_data.get("repository", {}).get("url") or issue_data.get("repo_url")
    return await solve_issue(issue_data, repo_url, "opire", config)


async def solve_github_issue(
    issue_data: dict[str, Any],
    repo_url: str,
    config: CoderAgentConfig | None = None,
) -> CoderAgentResult:
    """Solve a GitHub issue."""
    return await solve_issue(issue_data, repo_url, "github", config)


async def solve_freelancer_project(
    project_data: dict[str, Any],
    repo_url: str,
    config: CoderAgentConfig | None = None,
) -> CoderAgentResult:
    """Solve a Freelancer project (treat as issue)."""
    # Convert project data to issue-like format
    issue_data = {
        "id": project_data.get("id", "freelancer-project"),
        "title": project_data.get("title", ""),
        "body": project_data.get("description", ""),
        "platform": "freelancer",
        "url": project_data.get("url", ""),
    }
    return await solve_issue(issue_data, repo_url, "freelancer", config)
