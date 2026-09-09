"""Dev Bounty Pipeline E2E — Autonomous freelance/dev bounty execution.

Autonomous end-to-end dev bounty execution:
1. Discover bounty (OpportunityEngine - Opire, IssueHunt, Freelancer, etc.)
2. Analyze issue (IssueAnalyzer)
3. Clone repo (RepoAnalyzer)
4. Generate fix (CodeGenerator)
5. Run tests (TestRunner)
6. Create PR (PRBuilder)
7. Submit work (OpireExecutor, IssueHuntExecutor, FreelancerExecutor)
8. Verify delivery (Executor-specific)
9. Learn from outcome (FeedbackLoop)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from core.autonomy.code_generator import CodeGenerator, GenerationPlan
from core.autonomy.issue_analyzer import IssueAnalysis, IssueAnalyzer
from core.autonomy.pr_builder import PRBuilder, PRResult
from core.autonomy.repo_analyzer import RepoAnalyzer, RepoInfo
from core.autonomy.test_runner import TestRunner, TestRunSummary
from core.opportunity.executors import ExecutionResult
from core.opportunity.executors.freelancer_executor import FreelancerExecutor
from core.opportunity.executors.issuehunt_executor import IssueHuntExecutor
from core.opportunity.executors.mindrift_executor import MindriftExecutor
from core.opportunity.executors.opire_executor import OpireExecutor
from core.opportunity.executors.outlier_executor import OutlierExecutor
from cores.opportunity.feedback import get_feedback_loop

logger = logging.getLogger("ownex.autonomy.dev_bounty_pipeline")


@dataclass
class DevBountyPipelineConfig:
    """Configuration for dev bounty pipeline."""

    # Execution timeouts
    clone_timeout: int = 120
    analysis_timeout: int = 60
    generation_timeout: int = 120
    test_timeout: int = 300
    pr_timeout: int = 60
    submit_timeout: int = 30

    # Quality gates
    min_test_pass_rate: float = 0.8
    min_confidence_for_pr: float = 0.6
    max_iterations: int = 3

    # Platform config
    freelancer_token: str = ""
    opire_token: str = ""
    issuehunt_token: str = ""
    mindrift_token: str = ""
    outlier_token: str = ""

    # Behavior
    auto_submit: bool = True  # Auto-submit for Opire/IssueHunt (low risk, PR-based)
    cleanup_repo: bool = True


@dataclass
class DevBountyPipelineResult:
    """Result of dev bounty pipeline execution."""

    success: bool
    bounty_id: str
    platform: str  # freelancer, opire, issuehunt, mindrift, outlier

    # Phase results
    repo_info: RepoInfo | None = None
    issue_analysis: IssueAnalysis | None = None
    generation_plan: GenerationPlan | None = None
    test_results: TestRunSummary | None = None
    pr_result: PRResult | None = None
    submit_result: ExecutionResult | None = None

    # Metrics
    total_duration_seconds: float = 0.0
    phases: dict[str, float] = field(default_factory=dict)

    # Learning
    verdict: str = ""  # submitted, rejected, failed, error
    feedback: str = ""

    error: str | None = None


class DevBountyPipeline:
    """End-to-end autonomous dev bounty execution pipeline."""

    def __init__(self, config: DevBountyPipelineConfig | None = None) -> None:
        self.config = config or DevBountyPipelineConfig()
        self.repo_analyzer = RepoAnalyzer()
        self.issue_analyzer = IssueAnalyzer()
        self.code_generator = CodeGenerator()
        self.test_runner = TestRunner()
        self.pr_builder = PRBuilder()

        # Initialize platform-specific executors
        self.executors = {
            "freelancer": FreelancerExecutor(config={"api_token": self.config.freelancer_token}),
            "opire": OpireExecutor(config={"token": self.config.opire_token}),
            "issuehunt": IssueHuntExecutor(config={"token": self.config.issuehunt_token}),
            "mindrift": MindriftExecutor(config={"token": self.config.mindrift_token}),
            "outlier": OutlierExecutor(config={"token": self.config.outlier_token}),
        }
        self.feedback_loop = get_feedback_loop()

    async def execute_dev_bounty(
        self,
        bounty_id: str,
        platform: str,  # freelancer, opire, issuehunt, mindrift, outlier
        repo_url: str,
        issue_number: int,
        issue_url: str,
        title: str,
        description: str,
    ) -> DevBountyPipelineResult:
        """Execute full dev bounty pipeline end-to-end."""
        start_time = asyncio.get_event_loop().time()
        result = DevBountyPipelineResult(
            success=False,
            bounty_id=bounty_id,
            platform=platform,
        )

        try:
            # Phase 1: Clone and analyze repo
            logger.info("[DevBountyPipeline] Phase 1: Clone and analyze repo %s", repo_url)
            phase_start = asyncio.get_event_loop().time()

            clone_result = await self.repo_analyzer.clone_repo(
                repo_url,
                shallow=True,
            )
            if not clone_result.success or not clone_result.data:
                result.error = f"Failed to clone repo: {clone_result.error or 'No data returned'}"
                result.verdict = "error"
                return result

            repo_path = Path(clone_result.data["path"])
            repo_info = await self.repo_analyzer.analyze_repo(repo_path)
            result.repo_info = repo_info
            result.phases["repo_analysis"] = asyncio.get_event_loop().time() - phase_start

            # Phase 2: Analyze issue
            logger.info("[DevBountyPipeline] Phase 2: Analyze issue %s", issue_number)
            phase_start = asyncio.get_event_loop().time()

            issue_data = {
                "id": str(issue_number),
                "number": issue_number,
                "title": title,
                "body": description,
                "url": issue_url,
                "platform": platform,
            }
            analysis_result = self.issue_analyzer.analyze_issue(issue_data, repo_info)
            if not analysis_result.success or not analysis_result.data:
                result.error = f"Failed to analyze issue: {analysis_result.error or 'No data returned'}"
                result.verdict = "error"
                return result

            issue_analysis = analysis_result.data["analysis"]
            result.issue_analysis = issue_analysis
            result.phases["issue_analysis"] = asyncio.get_event_loop().time() - phase_start

            # Phase 3: Generate fix
            logger.info("[DevBountyPipeline] Phase 3: Generate fix")
            phase_start = asyncio.get_event_loop().time()

            gen_result = await self.code_generator.generate_fix(
                issue_analysis=issue_analysis,
                repo_info=repo_info,
            )
            if not gen_result.success or not gen_result.data:
                result.error = f"Failed to generate fix: {gen_result.error or 'No data returned'}"
                result.verdict = "rejected"
                return result

            generation_plan = gen_result.data["plan"]
            result.generation_plan = generation_plan
            result.phases["generation"] = asyncio.get_event_loop().time() - phase_start

            if generation_plan.estimated_confidence < self.config.min_confidence_for_pr:
                result.error = f"Low confidence fix: {generation_plan.estimated_confidence}"
                result.verdict = "rejected"
                return result

            # Phase 4: Run tests
            logger.info("[DevBountyPipeline] Phase 4: Run tests")
            phase_start = asyncio.get_event_loop().time()

            test_results = await self.test_runner.run_tests(
                repo_path=repo_info.path,
                repo_info=repo_info,
            )
            result.test_results = test_results
            result.phases["tests"] = asyncio.get_event_loop().time() - phase_start

            if not test_results.overall_success:
                result.error = (
                    f"Tests failed: {test_results.best_result.stderr if test_results.best_result else 'Unknown error'}"
                )
                result.verdict = "failed"
                return result

            # Phase 5: Create PR
            logger.info("[DevBountyPipeline] Phase 5: Create PR")
            phase_start = asyncio.get_event_loop().time()

            pr_result = await self.pr_builder.create_pr(
                plan=generation_plan,
                repo_info=repo_info,
                platform="github",
            )
            result.pr_result = pr_result
            result.phases["pr"] = asyncio.get_event_loop().time() - phase_start

            if not pr_result.success:
                result.error = f"Failed to create PR: {pr_result.error}"
                result.verdict = "failed"
                return result

            # Phase 6: Submit work via platform-specific executor
            logger.info("[DevBountyPipeline] Phase 6: Submit work via %s executor", platform)
            phase_start = asyncio.get_event_loop().time()

            executor = self._get_executor(platform)
            if not executor:
                result.error = f"No executor for platform: {platform}"
                result.verdict = "error"
                return result

            submit_result = await self._submit_via_executor(bounty_id, platform, executor, pr_result)
            result.submit_result = submit_result
            result.phases["submit"] = asyncio.get_event_loop().time() - phase_start

            if not submit_result.success:
                result.error = f"Failed to submit work: {submit_result.error}"
                result.verdict = "failed"
                return result

            # Success
            result.success = True
            result.verdict = "submitted"
            result.feedback = f"Successfully submitted work for bounty {bounty_id}"
            result.total_duration_seconds = asyncio.get_event_loop().time() - start_time

            logger.info(
                "[DevBountyPipeline] Dev bounty %s completed successfully in %.1fs",
                bounty_id,
                result.total_duration_seconds,
            )
            return result

        except Exception as e:
            logger.error("[DevBountyPipeline] Bounty %s failed with exception: %s", bounty_id, e)
            result.error = str(e)
            result.verdict = "error"
            result.total_duration_seconds = asyncio.get_event_loop().time() - start_time
            return result

    def _get_executor(self, platform: str):
        """Get executor for platform."""
        platform_lower = platform.lower()
        return self.executors.get(platform_lower)

    async def _submit_via_executor(
        self,
        bounty_id: str,
        platform: str,
        executor,
        pr_result: PRResult,
    ) -> ExecutionResult:
        """Submit work via platform-specific executor."""
        if platform == "freelancer":
            result = await self._submit_freelancer(executor, pr_result)
        elif platform in ("opire", "issuehunt"):
            # Auto-submit for OSS platforms (Opire, IssueHunt) if enabled
            if self.config.auto_submit:
                result = await self._submit_oss(executor, platform, bounty_id, pr_result)
            else:
                return ExecutionResult(
                    True,
                    "submit",
                    bounty_id,
                    "PR created; manual submission required (auto_submit disabled)",
                    data={"pr_url": pr_result.pr_url, "action_required": "manual_submit"},
                )
        elif platform in ("mindrift", "outlier"):
            result = await self._submit_ai_training(executor, platform, bounty_id)
        else:
            return ExecutionResult(False, "submit", "", error=f"Unsupported platform: {platform}")

        # If API submission failed, try Computer Use fallback
        if not result.success and self._should_try_computer_use(platform):
            logger.info("[DevBountyPipeline] API failed for %s, trying Computer Use fallback", platform)
            fallback = await self._submit_via_computer_use(bounty_id, platform, pr_result)
            if fallback.success:
                return fallback

        return result

    async def _submit_freelancer(self, executor: FreelancerExecutor, pr_result: PRResult) -> ExecutionResult:
        """Submit deliverable via Freelancer executor."""
        # For freelancer, we need project_id and deliverable files
        # This requires the project_id from the bounty data
        return ExecutionResult(
            False, "submit", "", error="Freelancer submission requires project_id and files from bounty data"
        )

    async def _submit_oss(
        self,
        executor,
        platform: str,
        bounty_id: str,
        pr_result: PRResult,
    ) -> ExecutionResult:
        """Submit PR via Opire/IssueHunt executor."""
        if not pr_result.pr_url:
            return ExecutionResult(False, "submit", bounty_id, error="No PR URL available")

        if platform == "opire":
            return await executor.submit_work(
                bounty_id, pr_result.pr_url, "Automated submission via OWNEX Dev Bounty Pipeline"
            )
        elif platform == "issuehunt":
            return await executor.submit_pr(bounty_id, pr_result.pr_url)
        return ExecutionResult(False, "submit", bounty_id, error=f"Unsupported OSS platform: {platform}")

    def _should_try_computer_use(self, platform: str) -> bool:
        """Check if Computer Use fallback should be attempted."""
        try:
            from cores.computer_use.submission_executor import should_use_computer_use

            return should_use_computer_use(platform, api_submission_failed=True)
        except ImportError:
            return False

    async def _submit_via_computer_use(self, bounty_id: str, platform: str, pr_result: PRResult) -> ExecutionResult:
        """Submit via Computer Use (desktop form filling) as fallback."""
        try:
            from cores.computer_use.submission_executor import get_computer_use_executor

            executor = get_computer_use_executor()
            if not executor.can_handle(platform):
                return ExecutionResult(False, "submit", bounty_id, error=f"Computer Use cannot handle {platform}")

            work_data = {
                "pr_url": pr_result.pr_url or "",
                "description": f"Automated submission via OWNEX Dev Bounty Pipeline for bounty {bounty_id}",
            }

            result = await executor.submit(
                platform=platform,
                work_data=work_data,
                work_item_id=bounty_id,
            )

            return ExecutionResult(
                success=result.success,
                phase="submit",
                output=f"Computer Use: {result.error or 'Form filled successfully'}",
                data={"method": "computer_use", "duration_ms": result.duration_ms},
                error=result.error,
            )
        except Exception as exc:
            logger.warning("[DevBountyPipeline] Computer Use fallback failed: %s", exc)
            return ExecutionResult(False, "submit", bounty_id, error=f"Computer Use fallback failed: {exc}")

    async def _submit_ai_training(self, executor, platform: str, bounty_id: str) -> ExecutionResult:
        """Submit work for AI training platforms."""
        # Try Computer Use fallback for AI training platforms
        if self._should_try_computer_use(platform):
            logger.info("[DevBountyPipeline] AI training platform %s — trying Computer Use", platform)
            return await self._submit_via_computer_use(bounty_id, platform, PRResult(success=False, error=""))
        return ExecutionResult(False, "submit", bounty_id, error=f"{platform} submission requires specific data format")


# Global instance
_global_dev_pipeline: DevBountyPipeline | None = None


def get_dev_bounty_pipeline(config: DevBountyPipelineConfig | None = None) -> DevBountyPipeline:
    """Get or create the global DevBountyPipeline instance."""
    global _global_dev_pipeline
    if _global_dev_pipeline is None:
        _global_dev_pipeline = DevBountyPipeline()
    return _global_dev_pipeline
