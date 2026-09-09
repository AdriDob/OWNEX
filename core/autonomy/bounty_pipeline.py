"""Bounty Pipeline E2E — CoderAgent + Executor integration.

Autonomous end-to-end bounty execution:
1. Discover bounty (OpportunityEngine)
2. Analyze issue (IssueAnalyzer)
3. Clone repo (RepoAnalyzer)
4. Generate fix (CodeGenerator)
5. Run tests (TestRunner)
6. Create PR (PRBuilder)
7. Claim bounty (AlgoraExecutor)
8. Submit PR (AlgoraExecutor)
9. Learn from outcome (FeedbackLoop)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from core.autonomy.code_generator import CodeGenerator, GenerationPlan
from core.autonomy.issue_analyzer import IssueAnalysis, IssueAnalyzer
from core.autonomy.pr_builder import PRBuilder, PRResult
from core.autonomy.repo_analyzer import RepoAnalyzer, RepoInfo
from core.autonomy.test_runner import TestRunner, TestRunSummary
from core.opportunity.executors import ExecutionResult
from core.opportunity.executors.algora_executor import AlgoraExecutor
from cores.opportunity.feedback import FeedbackOutcome, get_feedback_loop

logger = logging.getLogger("ownex.autonomy.bounty_pipeline")


@dataclass
class BountyPipelineConfig:
    """Configuration for bounty pipeline."""

    # Execution timeouts
    clone_timeout: int = 120
    analysis_timeout: int = 60
    generation_timeout: int = 120
    test_timeout: int = 300
    pr_timeout: int = 60
    claim_timeout: int = 30
    submit_timeout: int = 30

    # Quality gates
    min_test_pass_rate: float = 0.8
    min_confidence_for_pr: float = 0.6
    max_iterations: int = 3

    # Platform config
    algora_token: str = ""
    github_token: str = ""

    # Behavior
    auto_claim: bool = True
    auto_submit: bool = False  # Requires manual approval initially
    cleanup_repo: bool = True


@dataclass
class BountyPipelineResult:
    """Result of bounty pipeline execution."""

    success: bool
    bounty_id: str
    platform: str

    # Phase results
    repo_info: RepoInfo | None = None
    issue_analysis: IssueAnalysis | None = None
    generation_plan: GenerationPlan | None = None
    test_results: TestRunSummary | None = None
    pr_result: PRResult | None = None
    claim_result: ExecutionResult | None = None
    submit_result: ExecutionResult | None = None

    # Metrics
    total_duration_seconds: float = 0.0
    phases: dict[str, float] = field(default_factory=dict)

    # Learning
    verdict: str = ""  # submitted, rejected, failed, error
    feedback: str = ""

    error: str | None = None


class BountyPipeline:
    """End-to-end autonomous bounty execution pipeline."""

    def __init__(self, config: BountyPipelineConfig | None = None) -> None:
        self.config = config or BountyPipelineConfig()
        self.repo_analyzer = RepoAnalyzer()
        self.issue_analyzer = IssueAnalyzer()
        self.code_generator = CodeGenerator()
        self.test_runner = TestRunner()
        self.pr_builder = PRBuilder()
        self.algora_executor = AlgoraExecutor(
            config={"token": self.config.algora_token, "github_token": self.config.github_token}
        )
        self.feedback_loop = get_feedback_loop()

    async def execute_bounty(
        self,
        bounty_id: str,
        repo: str,
        issue_number: int,
        issue_url: str,
        title: str,
        description: str,
    ) -> BountyPipelineResult:
        """Execute full bounty pipeline end-to-end."""
        start_time = asyncio.get_event_loop().time()
        result = BountyPipelineResult(
            success=False,
            bounty_id=bounty_id,
            platform="algora",
        )

        try:
            # Phase 1: Clone and analyze repo
            logger.info("[BountyPipeline] Phase 1: Clone and analyze repo %s", repo)
            phase_start = asyncio.get_event_loop().time()

            repo_info = await self.repo_analyzer.analyze_repo(repo, timeout=self.config.clone_timeout)
            result.repo_info = repo_info
            result.phases["repo_analysis"] = asyncio.get_event_loop().time() - phase_start

            if not repo_info.clone_success:
                result.error = f"Failed to clone repo: {repo_info.error}"
                result.verdict = "error"
                return result

            # Phase 2: Analyze issue
            logger.info("[BountyPipeline] Phase 2: Analyze issue %s", issue_number)
            phase_start = asyncio.get_event_loop().time()

            issue_analysis = await self.issue_analyzer.analyze_issue(
                repo_url=issue_url,
                issue_number=issue_number,
                title=title,
                description=description,
                repo_info=repo_info,
                timeout=self.config.analysis_timeout,
            )
            result.issue_analysis = issue_analysis
            result.phases["issue_analysis"] = asyncio.get_event_loop().time() - phase_start

            if not issue_analysis.success:
                result.error = f"Failed to analyze issue: {issue_analysis.error}"
                result.verdict = "error"
                return result

            # Phase 3: Generate fix
            logger.info("[BountyPipeline] Phase 3: Generate fix")
            phase_start = asyncio.get_event_loop().time()

            generation_plan = await self.code_generator.generate_fix(
                issue_analysis=issue_analysis,
                repo_info=repo_info,
                timeout=self.config.generation_timeout,
            )
            result.generation_plan = generation_plan
            result.phases["generation"] = asyncio.get_event_loop().time() - phase_start

            if not generation_plan.success or generation_plan.confidence < self.config.min_confidence_for_pr:
                result.error = f"Low confidence fix: {generation_plan.confidence}"
                result.verdict = "rejected"
                self._record_feedback(bounty_id, "algora", "web3", ["oss"], FeedbackOutcome.REJECTED, result.error)
                return result

            # Phase 4: Run tests
            logger.info("[BountyPipeline] Phase 4: Run tests")
            phase_start = asyncio.get_event_loop().time()

            test_results = await self.test_runner.run_tests(
                repo_path=repo_info.local_path,
                timeout=self.config.test_timeout,
            )
            result.test_results = test_results
            result.phases["tests"] = asyncio.get_event_loop().time() - phase_start

            if test_results.pass_rate < self.config.min_test_pass_rate:
                result.error = f"Test pass rate too low: {test_results.pass_rate}"
                result.verdict = "failed"
                self._record_feedback(bounty_id, "algora", "web3", ["oss"], FeedbackOutcome.REJECTED, result.error)
                return result

            # Phase 5: Create PR
            logger.info("[BountyPipeline] Phase 5: Create PR")
            phase_start = asyncio.get_event_loop().time()

            branch_name = f"fix-{issue_number}-{bounty_id[:8]}"
            pr_result = await self.pr_builder.create_pr(
                repo=repo,
                branch=branch_name,
                base=repo_info.default_branch,
                title=f"Fix: {title}",
                body=f"Fix for issue #{issue_number}\n\n{generation_plan.summary}",
                files=generation_plan.files,
                timeout=self.config.pr_timeout,
            )
            result.pr_result = pr_result
            result.phases["pr"] = asyncio.get_event_loop().time() - phase_start

            if not pr_result.success:
                result.error = f"Failed to create PR: {pr_result.error}"
                result.verdict = "failed"
                self._record_feedback(bounty_id, "algora", "web3", ["oss"], FeedbackOutcome.REJECTED, result.error)
                return result

            # Phase 6: Claim bounty
            if self.config.auto_claim:
                logger.info("[BountyPipeline] Phase 6: Claim bounty")
                phase_start = asyncio.get_event_loop().time()

                claim_result = await self.algora_executor.execute(
                    "claim_issue",
                    bounty_id=bounty_id,
                    repo=repo,
                    issue_number=issue_number,
                )
                result.claim_result = claim_result
                result.phases["claim"] = asyncio.get_event_loop().time() - phase_start

                if not claim_result.success:
                    result.error = f"Failed to claim bounty: {claim_result.error}"
                    result.verdict = "failed"
                    self._record_feedback(bounty_id, "algora", "web3", ["oss"], FeedbackOutcome.REJECTED, result.error)
                    return result

            # Phase 7: Submit PR
            if self.config.auto_submit:
                logger.info("[BountyPipeline] Phase 7: Submit PR")
                phase_start = asyncio.get_event_loop().time()

                submit_result = await self.algora_executor.execute(
                    "submit_pr",
                    bounty_id=bounty_id,
                    pr_url=pr_result.pr_url,
                )
                result.submit_result = submit_result
                result.phases["submit"] = asyncio.get_event_loop().time() - phase_start

                if not submit_result.success:
                    result.error = f"Failed to submit PR: {submit_result.error}"
                    result.verdict = "failed"
                    self._record_feedback(bounty_id, "algora", "web3", ["oss"], FeedbackOutcome.REJECTED, result.error)
                    return result
            else:
                # Create mobile approval request for manual approval
                logger.info("[BountyPipeline] Phase 7: Requesting mobile approval for PR submission")
                phase_start = asyncio.get_event_loop().time()

                try:
                    import json

                    from database.db import SessionLocal
                    from database.models import MobileApproval

                    db = SessionLocal()
                    try:
                        # Check if approval already exists
                        existing = (
                            db.query(MobileApproval)
                            .filter(
                                MobileApproval.entity_type == "bounty",
                                MobileApproval.entity_id == bounty_id,
                                MobileApproval.status == "pending",
                            )
                            .first()
                        )

                        if not existing:
                            approval = MobileApproval(
                                entity_type="bounty",
                                entity_id=bounty_id,
                                title=f"Submit PR for bounty {bounty_id}",
                                description=f"Ready to submit PR for issue #{issue_number}: {title}",
                                metadata_json=json.dumps(
                                    {
                                        "pr_url": pr_result.pr_url,
                                        "repo": repo,
                                        "issue_number": issue_number,
                                        "issue_url": issue_url,
                                    }
                                ),
                                priority="high",
                                status="pending",
                            )
                            db.add(approval)
                            db.commit()
                            logger.info(
                                "[BountyPipeline] Created mobile approval %s for bounty %s", approval.id, bounty_id
                            )
                            result.phases["approval_request"] = asyncio.get_event_loop().time() - phase_start
                        else:
                            logger.info("[BountyPipeline] Approval already exists for bounty %s", bounty_id)
                            result.phases["approval_request"] = asyncio.get_event_loop().time() - phase_start
                    finally:
                        db.close()
                except Exception as e:
                    logger.warning("[BountyPipeline] Failed to create mobile approval: %s", e)
                    result.phases["approval_request"] = asyncio.get_event_loop().time() - phase_start

                # Mark as awaiting approval
                result.success = True
                result.verdict = "awaiting_approval"
                result.feedback = f"PR created and awaiting mobile approval for bounty {bounty_id}"
                result.total_duration_seconds = asyncio.get_event_loop().time() - start_time

                logger.info(
                    "[BountyPipeline] Bounty %s awaiting mobile approval in %.1fs",
                    bounty_id,
                    result.total_duration_seconds,
                )

                return result

            # Success
            result.success = True
            result.verdict = "submitted"
            result.feedback = f"Successfully submitted PR for bounty {bounty_id}"
            result.total_duration_seconds = asyncio.get_event_loop().time() - start_time

            self._record_feedback(
                bounty_id,
                "algora",
                "web3",
                ["oss"],
                FeedbackOutcome.ACCEPTED,
                result.feedback,
                estimated_payout=issue_analysis.estimated_reward,
            )

            logger.info(
                "[BountyPipeline] Bounty %s completed successfully in %.1fs",
                bounty_id,
                result.total_duration_seconds,
            )

            return result

        except Exception as e:
            logger.error("[BountyPipeline] Bounty %s failed with exception: %s", bounty_id, e)
            result.error = str(e)
            result.verdict = "error"
            result.total_duration_seconds = asyncio.get_event_loop().time() - start_time
            return result

        finally:
            # Cleanup
            if self.config.cleanup_repo and result.repo_info and result.repo_info.local_path:
                try:
                    import shutil

                    shutil.rmtree(result.repo_info.local_path, ignore_errors=True)
                    logger.debug("[BountyPipeline] Cleaned up repo: %s", result.repo_info.local_path)
                except Exception:
                    pass

    def _record_feedback(
        self,
        bounty_id: str,
        platform: str,
        category: str,
        technology_tags: list[str],
        outcome: FeedbackOutcome,
        reasoning: str,
        estimated_payout: float = 0.0,
    ) -> None:
        """Record feedback for learning."""
        try:
            self.feedback_loop.record_feedback(
                opportunity_id=bounty_id,
                outcome=outcome,
                category=category,
                platform=platform,
                technology_tags=technology_tags,
                estimated_payout=estimated_payout,
                reasoning=reasoning,
            )
        except Exception as e:
            logger.warning("[BountyPipeline] Failed to record feedback: %s", e)


_global_pipeline: BountyPipeline | None = None


def get_bounty_pipeline(config: BountyPipelineConfig | None = None) -> BountyPipeline:
    global _global_pipeline
    if _global_pipeline is None:
        _global_pipeline = BountyPipeline(config)
        logger.info("BountyPipeline initialized")
    return _global_pipeline
