"""CoderAgent — Main orchestrator for autonomous code fixing.

The CoderAgent is the "brain" that:
1. Clones repository
2. Analyzes issue
3. Generates fix
4. Runs tests
5. Creates PR
6. Learns from outcome
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.autonomy.code_generator import CodeGenerator, GenerationPlan
from core.autonomy.issue_analyzer import IssueAnalysis, IssueAnalyzer
from core.autonomy.pr_builder import PRBuilder, PRResult, create_pr_from_plan
from core.autonomy.repo_analyzer import RepoAnalyzer, RepoInfo
from core.autonomy.test_runner import TestRunner, TestRunSummary


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

    # Timeouts
    clone_timeout: int = 120
    analysis_timeout: int = 60
    generation_timeout: int = 120
    test_timeout: int = 300
    pr_timeout: int = 60

    # Behavior
    max_iterations: int = 3  # Retry fix if tests fail
    min_confidence_for_pr: float = 0.6
    cleanup_repo: bool = True
    run_lint: bool = True

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
        self.test_runner = TestRunner()
        self.pr_builder = PRBuilder()

        # Work directory
        self.work_dir = Path(tempfile.gettempdir()) / "ownex_coder_agent"
        self.work_dir.mkdir(parents=True, exist_ok=True)

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
            # PHASE 1: CLONE REPOSITORY
            # ============================================================
            phase_start = time.time()
            repo_url = repo_url or issue_data.get("repository_url") or issue_data.get("repo_url")
            if not repo_url:
                raise ValueError("No repository URL provided")

            repo_path = self.work_dir / f"repo_{result.issue_id}"
            if repo_path.exists():
                shutil.rmtree(repo_path)

            clone_result = await self.repo_analyzer.clone_repo(repo_url)
            result.phases_duration["clone"] = time.time() - phase_start

            if not clone_result.success:
                raise RuntimeError(f"Clone failed: {clone_result.error}")

            result.repo_cloned = True
            result.repo_info = await self.repo_analyzer.analyze_repo(repo_path)

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
                return self._finalize_result(result, start_time, repo_path)

            # ============================================================
            # PHASE 4: RUN TESTS (iterative)
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
            # PHASE 5: CREATE PR
            # ============================================================
            phase_start = time.time()
            pr_result = await create_pr_from_plan(
                result.generation_plan,
                result.repo_info,
                platform="github",  # Most bounty platforms use GitHub
            )
            result.phases_duration["pr_creation"] = time.time() - phase_start

            result.pr_result = pr_result

            if not pr_result.success:
                raise RuntimeError(f"PR creation failed: {pr_result.error}")

            # ============================================================
            # SUCCESS
            # ============================================================
            result.success = True
            result.verdict = "pr_created"
            result.feedback = f"PR created: {pr_result.pr_url}"

            return self._finalize_result(result, start_time, repo_path)

        except Exception as e:
            result.error = str(e)
            result.verdict = "error"
            return self._finalize_result(result, start_time, repo_path)

    async def _run_tests_with_retries(
        self,
        repo_path: Path,
        repo_info: RepoInfo,
        plan: GenerationPlan,
        result: CoderAgentResult,
    ) -> bool:
        """Run tests with retries, regenerating fix if needed."""
        for iteration in range(self.config.max_iterations):
            # Install dependencies first
            install_result = await self.repo_analyzer.install_dependencies(repo_path)
            if not install_result.success:
                # Not necessarily fatal - maybe deps already installed
                pass

            # Run tests
            test_summary = await self.test_runner.run_tests(repo_path, repo_info=repo_info)
            result.test_results = test_summary

            if test_summary.overall_success:
                return True

            # Tests failed - try to regenerate fix with test feedback
            if iteration < self.config.max_iterations - 1:
                # Add test failure info to issue analysis for next iteration
                failure_info = self._extract_test_failures(test_summary)
                if failure_info:
                    result.issue_analysis.body += (
                        f"\n\n--- Test Failures (iteration {iteration + 1}) ---\n{failure_info}"
                    )
                    # Regenerate
                    gen_result = await self.code_generator.generate_fix(
                        result.issue_analysis,
                        repo_info,
                    )
                    if gen_result.success:
                        plan = gen_result.data["plan"]
                        result.generation_plan = plan
                        # Apply new changes
                        await self._apply_plan_changes(repo_path, plan)

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
        """Apply all changes from a generation plan."""
        for change in plan.changes:
            file_path = change.file_path
            if not file_path.is_absolute():
                file_path = repo_path / file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(change.new_content, encoding="utf-8")

        for change in plan.test_changes:
            file_path = change.file_path
            if not file_path.is_absolute():
                file_path = repo_path / file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(change.new_content, encoding="utf-8")

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
