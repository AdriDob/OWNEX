"""Continuous Thinking System — Daily Planning, Research, and Improvement loops.

This system implements the continuous cognitive cycles that enable OWNEX to:
- Plan daily work based on goals and opportunities
- Research new platforms, techniques, and trends
- Learn from every task completion to improve future performance
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from core.events.event_bus import get_core_event_bus
from core.sensors.observation_engine import ObservationEngine
from cores.discovery_engine import DiscoveryEngine, RankedOpportunity
from cores.prometheus_metrics import (
    LEARNING_CONFIDENCE,
    LEARNING_PATTERNS_EXTRACTED,
    THINKING_CYCLE_DURATION,
    THINKING_CYCLES_COMPLETED,
)

logger = logging.getLogger("ownex.thinking_system")


class ThinkingMode(Enum):
    """Thinking system operating modes."""
    DAILY_PLANNING = "daily_planning"
    RESEARCH = "research"
    IMPROVEMENT = "improvement"
    ALL = "all"


@dataclass
class Goal:
    """A high-level goal for the system."""
    id: str
    name: str
    description: str
    category: str                    # revenue, learning, security, growth
    target_metric: str               # e.g., "monthly_revenue_usd"
    target_value: float
    current_value: float = 0.0
    priority: int = 1                # 1=highest, 5=lowest
    deadline: datetime | None = None
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DailyPlan:
    """Daily execution plan."""
    date: str
    goals: list[Goal]
    prioritized_opportunities: list[RankedOpportunity]
    allocated_time_hours: dict[str, float]  # category -> hours
    expected_revenue: float
    expected_learning: float
    risk_assessment: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    executed: bool = False
    actual_results: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchTopic:
    """A research topic to investigate."""
    id: str
    name: str
    description: str
    category: str                    # platform, technique, tool, market
    priority: int
    status: str = "pending"          # pending, in_progress, completed, archived
    findings: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    actionable_insights: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningRecord:
    """A learning extracted from task execution."""
    id: str
    task_id: str
    task_type: str
    platform: str
    what_worked: list[str]
    what_failed: list[str]
    improvements: list[str]
    confidence: float                # 0-1
    pattern_type: str                # success, failure, optimization, discovery
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    applied_count: int = 0
    last_applied: datetime | None = None


@dataclass
class ThinkingConfig:
    """Configuration for the thinking system."""
    # Daily Planning
    planning_hour: int = 6           # UTC hour to run daily planning
    planning_enabled: bool = True
    max_opportunities_per_day: int = 20
    max_daily_hours: float = 8.0

    # Research
    research_enabled: bool = True
    research_interval_hours: int = 6
    max_concurrent_research: int = 3
    research_sources: list[str] = field(default_factory=lambda: [
        "github_trending", "hackerone_reports", "bugcrowd_writeups",
        "dev_post_mortems", "ai_papers", "crypto_alpha"
    ])

    # Improvement
    improvement_enabled: bool = True
    improvement_interval_hours: int = 24
    min_tasks_for_pattern: int = 3
    learning_confidence_threshold: float = 0.7

    # General
    mode: ThinkingMode = ThinkingMode.ALL
    persist_state: bool = True
    state_file: str = "data/thinking_state.json"


@dataclass
class ThinkingMetrics:
    """Runtime metrics for thinking system."""
    planning_cycles: int = 0
    research_cycles: int = 0
    improvement_cycles: int = 0
    plans_created: int = 0
    topics_researched: int = 0
    patterns_learned: int = 0
    patterns_applied: int = 0
    last_planning: datetime | None = None
    last_research: datetime | None = None
    last_improvement: datetime | None = None
    errors: list[str] = field(default_factory=list)


class ThinkingSystem:
    """
    Continuous Thinking System for OWNEX.
    
    Runs three continuous loops:
    1. Daily Planning - Plan work based on goals and opportunities
    2. Research - Continuously study platforms, techniques, trends
    3. Improvement - Learn from every task to improve future performance
    """

    def __init__(
        self,
        config: ThinkingConfig | None = None,
        discovery_engine: DiscoveryEngine | None = None,
        observation_engine: ObservationEngine | None = None,
    ):
        self.config = config or ThinkingConfig()
        self.discovery_engine = discovery_engine
        self.observation_engine = observation_engine
        self.event_bus = get_core_event_bus()

        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}
        self._metrics = ThinkingMetrics()

        # State storage
        self._goals: dict[str, Goal] = {}
        self._daily_plans: list[DailyPlan] = []
        self._research_topics: dict[str, ResearchTopic] = {}
        self._learning_records: list[LearningRecord] = []

        # Callbacks
        self._on_plan_created: list[Callable[[DailyPlan], Any]] = []
        self._on_research_complete: list[Callable[[ResearchTopic], Any]] = []
        self._on_learning_extracted: list[Callable[[LearningRecord], Any]] = []

        logger.info("ThinkingSystem initialized: mode=%s", self.config.mode.value)

    def register_plan_callback(self, callback: Callable[[DailyPlan], Any]) -> None:
        self._on_plan_created.append(callback)

    def register_research_callback(self, callback: Callable[[ResearchTopic], Any]) -> None:
        self._on_research_complete.append(callback)

    def register_learning_callback(self, callback: Callable[[LearningRecord], Any]) -> None:
        self._on_learning_extracted.append(callback)

    # ── Goal Management ───────────────────────────────────────────────

    def add_goal(self, goal: Goal) -> None:
        """Add a high-level goal."""
        self._goals[goal.id] = goal
        logger.info("Added goal: %s (%s)", goal.name, goal.id)

    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal."""
        if goal_id in self._goals:
            del self._goals[goal_id]
            return True
        return False

    def get_active_goals(self) -> list[Goal]:
        """Get all active goals sorted by priority."""
        active = [g for g in self._goals.values() if g.active]
        active.sort(key=lambda g: (g.priority, -g.target_value))
        return active

    def update_goal_progress(self, goal_id: str, current_value: float) -> None:
        """Update goal progress."""
        if goal_id in self._goals:
            self._goals[goal_id].current_value = current_value

    # ── Daily Planning Loop ──────────────────────────────────────────

    async def _planning_loop(self) -> None:
        """Daily planning loop - runs at configured hour."""
        while self._running:
            try:
                # Calculate time until next planning hour
                now = datetime.now(UTC)
                next_planning = now.replace(
                    hour=self.config.planning_hour,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                if next_planning <= now:
                    next_planning += timedelta(days=1)

                wait_seconds = (next_planning - now).total_seconds()
                logger.info("Next daily planning in %.1f hours", wait_seconds / 3600)
                await asyncio.sleep(wait_seconds)

                if not self._running:
                    break

                await self._run_daily_planning()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in planning loop: %s", e)
                self._metrics.errors.append(f"{datetime.now(UTC).isoformat()}: planning: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def _run_daily_planning(self) -> DailyPlan:
        """Execute daily planning cycle."""
        logger.info("Starting daily planning cycle")
        cycle_start = time.time()

        # Get active goals
        goals = self.get_active_goals()

        # Get queued opportunities from discovery engine
        opportunities = []
        if self.discovery_engine:
            opportunities = await self.discovery_engine.get_queued_opportunities(
                limit=self.config.max_opportunities_per_day
            )

        # Prioritize opportunities by goal alignment
        prioritized = self._prioritize_for_goals(opportunities, goals)

        # Allocate time budget
        time_allocation = self._allocate_time(prioritized, goals)

        # Calculate expected outcomes
        expected_revenue = sum(
            opp.evh * time_allocation.get(opp.opportunity.cycle, 0)
            for opp in prioritized
        )
        expected_learning = len(prioritized) * 0.1  # Heuristic

        # Assess risk
        risk = self._assess_risk(prioritized)

        # Create plan
        plan = DailyPlan(
            date=datetime.now(UTC).date().isoformat(),
            goals=goals,
            prioritized_opportunities=prioritized[:self.config.max_opportunities_per_day],
            allocated_time_hours=time_allocation,
            expected_revenue=expected_revenue,
            expected_learning=expected_learning,
            risk_assessment=risk,
        )

        self._daily_plans.append(plan)
        self._metrics.planning_cycles += 1
        self._metrics.plans_created += 1
        self._metrics.last_planning = datetime.now(UTC)

        # Prometheus
        THINKING_CYCLES_COMPLETED.labels(cycle_type="planning").inc()
        THINKING_CYCLE_DURATION.labels(cycle_type="planning").observe(time.time() - cycle_start)

        # Emit event
        self.event_bus.publish("thinking:plan_created", {
            "date": plan.date,
            "opportunities": len(plan.prioritized_opportunities),
            "expected_revenue": plan.expected_revenue,
            "allocated_hours": plan.allocated_time_hours,
            "risk": plan.risk_assessment,
        })

        # Trigger callbacks
        for callback in self._on_plan_created:
            try:
                await callback(plan)
            except Exception as e:
                logger.error("Plan callback failed: %s", e)

        logger.info(
            "Daily plan created: %d opportunities, $%.2f expected, %s risk",
            len(plan.prioritized_opportunities), plan.expected_revenue, plan.risk_assessment
        )

        return plan

    def _prioritize_for_goals(
        self,
        opportunities: list[RankedOpportunity],
        goals: list[Goal]
    ) -> list[RankedOpportunity]:
        """Re-rank opportunities based on goal alignment."""
        if not goals:
            return opportunities

        # Score each opportunity against goals
        scored = []
        for opp in opportunities:
            goal_score = 0.0
            for goal in goals:
                # Match opportunity category to goal category
                if opp.opportunity.cycle == goal.category:
                    goal_score += (1.0 / goal.priority) * (goal.target_value / max(goal.target_value, 1))
                # Revenue goals match any revenue-generating opportunity
                if goal.category == "revenue" and opp.evh > 0:
                    goal_score += opp.evh / 100.0

            # Combined score: original EVH + goal alignment
            combined = opp.evh + goal_score * 10
            scored.append((combined, opp))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [opp for _, opp in scored]

    def _allocate_time(
        self,
        opportunities: list[RankedOpportunity],
        goals: list[Goal]
    ) -> dict[str, float]:
        """Allocate time budget across opportunity categories."""
        allocation: dict[str, float] = {}
        remaining_hours = self.config.max_daily_hours

        for opp in opportunities:
            if remaining_hours <= 0:
                break

            cycle = opp.opportunity.cycle
            effort = getattr(opp.opportunity, 'effort_hours', 4)
            allocated = min(effort, remaining_hours)

            allocation[cycle] = allocation.get(cycle, 0) + allocated
            remaining_hours -= allocated

        return allocation

    def _assess_risk(self, opportunities: list[RankedOpportunity]) -> str:
        """Assess overall risk of the plan."""
        if not opportunities:
            return "none"

        high_effort = sum(1 for o in opportunities if getattr(o.opportunity, 'effort_hours', 4) > 8)
        low_score = sum(1 for o in opportunities if o.score < 0.5)
        new_platforms = len(set(o.opportunity.source_name for o in opportunities))

        risk_factors = high_effort + low_score + (new_platforms > 3)

        if risk_factors >= 3:
            return "high"
        elif risk_factors >= 1:
            return "medium"
        return "low"

    # ── Research Loop ────────────────────────────────────────────────

    async def _research_loop(self) -> None:
        """Continuous research loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.research_interval_hours * 3600)

                if not self._running:
                    break

                await self._run_research_cycle()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in research loop: %s", e)
                self._metrics.errors.append(f"{datetime.now(UTC).isoformat()}: research: {e}")
                await asyncio.sleep(3600)

    async def _run_research_cycle(self) -> list[ResearchTopic]:
        """Execute research cycle - investigate pending topics."""
        logger.info("Starting research cycle")
        cycle_start = time.time()

        # Get pending topics
        pending = [t for t in self._research_topics.values() if t.status == "pending"]
        pending.sort(key=lambda t: t.priority)

        # Limit concurrent research
        to_research = pending[:self.config.max_concurrent_research]

        completed = []
        for topic in to_research:
            try:
                topic.status = "in_progress"
                findings = await self._research_topic(topic)
                topic.findings.extend(findings)
                topic.status = "completed"
                topic.completed_at = datetime.now(UTC)

                # Extract actionable insights
                insights = self._extract_insights(topic)
                topic.actionable_insights.extend(insights)

                completed.append(topic)
                self._metrics.topics_researched += 1

                # Trigger callbacks
                for callback in self._on_research_complete:
                    try:
                        await callback(topic)
                    except Exception as e:
                        logger.error("Research callback failed: %s", e)

            except Exception as e:
                logger.error("Failed to research topic %s: %s", topic.id, e)
                topic.status = "pending"  # Retry later

        self._metrics.research_cycles += 1
        self._metrics.last_research = datetime.now(UTC)

        THINKING_CYCLES_COMPLETED.labels(cycle_type="research").inc()
        THINKING_CYCLE_DURATION.labels(cycle_type="research").observe(time.time() - cycle_start)

        logger.info("Research cycle complete: %d topics completed", len(completed))
        return completed

    async def _research_topic(self, topic: ResearchTopic) -> list[str]:
        """Research a specific topic using available sources."""
        findings = []

        # Simulate research based on topic category
        if topic.category == "platform":
            findings.extend(await self._research_platform(topic.name))
        elif topic.category == "technique":
            findings.extend(await self._research_technique(topic.name))
        elif topic.category == "tool":
            findings.extend(await self._research_tool(topic.name))
        elif topic.category == "market":
            findings.extend(await self._research_market(topic.name))

        # Store sources
        topic.sources.extend([
            f"internal_analysis:{topic.category}",
            f"observation_engine:{len(self.observation_engine._sensors) if self.observation_engine else 0}_sensors",
        ])

        return findings

    async def _research_platform(self, platform: str) -> list[str]:
        """Research a work platform."""
        # In production, this would query APIs, scrape docs, analyze reports
        return [
            f"Platform {platform}: Analyzed API endpoints and authentication flow",
            f"Platform {platform}: Identified rate limits and pagination patterns",
            f"Platform {platform}: Found {len(self._research_topics)} related opportunities in history",
        ]

    async def _research_technique(self, technique: str) -> list[str]:
        """Research a technique/methodology."""
        return [
            f"Technique {technique}: Reviewed latest best practices and case studies",
            f"Technique {technique}: Identified automation opportunities",
        ]

    async def _research_tool(self, tool: str) -> list[str]:
        """Research a tool."""
        return [
            f"Tool {tool}: Evaluated integration complexity and maintenance burden",
            f"Tool {tool}: Checked compatibility with existing stack",
        ]

    async def _research_market(self, market: str) -> list[str]:
        """Research a market/trend."""
        return [
            f"Market {market}: Analyzed demand trends and pricing",
            f"Market {market}: Identified emerging opportunities",
        ]

    def _extract_insights(self, topic: ResearchTopic) -> list[str]:
        """Extract actionable insights from research findings."""
        insights = []

        for finding in topic.findings:
            if "automation" in finding.lower():
                insights.append(f"Automate: {finding}")
            if "rate limit" in finding.lower():
                insights.append(f"Optimize rate limiting for {topic.name}")
            if "opportunit" in finding.lower():
                insights.append(f"New opportunity pattern: {finding}")

        return insights

    def add_research_topic(self, topic: ResearchTopic) -> None:
        """Add a research topic."""
        self._research_topics[topic.id] = topic
        logger.info("Added research topic: %s", topic.name)

    # ── Improvement Loop ─────────────────────────────────────────────

    async def _improvement_loop(self) -> None:
        """Continuous improvement loop - learns from task history."""
        while self._running:
            try:
                await asyncio.sleep(self.config.improvement_interval_hours * 3600)

                if not self._running:
                    break

                await self._run_improvement_cycle()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in improvement loop: %s", e)
                self._metrics.errors.append(f"{datetime.now(UTC).isoformat()}: improvement: {e}")
                await asyncio.sleep(3600)

    async def _run_improvement_cycle(self) -> list[LearningRecord]:
        """Analyze recent task history and extract patterns."""
        logger.info("Starting improvement cycle")
        cycle_start = time.time()

        # In production, this would query task history from database
        # For now, simulate learning from available learning from recent events
        new_learnings = await self._analyze_task_history()

        for learning in new_learnings:
            self._learning_records.append(learning)
            self._metrics.patterns_learned += 1

            # Prometheus
            LEARNING_PATTERNS_EXTRACTED.inc()
            LEARNING_CONFIDENCE.observe(learning.confidence)

            # Trigger callbacks
            for callback in self._on_learning_extracted:
                try:
                    await callback(learning)
                except Exception as e:
                    logger.error("Learning callback failed: %s", e)

        self._metrics.improvement_cycles += 1
        self._metrics.last_improvement = datetime.now(UTC)

        THINKING_CYCLES_COMPLETED.labels(cycle_type="improvement").inc()
        THINKING_CYCLE_DURATION.labels(cycle_type="improvement").observe(time.time() - cycle_start)

        logger.info("Improvement cycle complete: %d new patterns learned", len(new_learnings))
        return new_learnings

    async def _analyze_task_history(self) -> list[LearningRecord]:
        """Analyze task history for patterns (placeholder for DB integration)."""
        # In production, query task completion events from EventBus/database
        # This is a placeholder that would be replaced with real analysis
        learnings = []

        # Example patterns that would be extracted:
        # - "High EVH bug bounty reports on Fridays have 20% better acceptance"
        # - "Using Playwright for Dev Bounty reduces time by 40%"
        # - "AI work platforms prefer Python solutions with tests"

        # For now, return empty - real implementation needs task history storage
        return learnings

    def record_task_result(
        self,
        task_id: str,
        task_type: str,
        platform: str,
        success: bool,
        details: dict[str, Any]
    ) -> None:
        """Record a task result for learning."""
        learning = LearningRecord(
            id=f"learning_{task_id}_{int(time.time())}",
            task_id=task_id,
            task_type=task_type,
            platform=platform,
            what_worked=details.get("what_worked", []) if success else [],
            what_failed=details.get("what_failed", []) if not success else [],
            improvements=details.get("improvements", []),
            confidence=details.get("confidence", 0.7),
            pattern_type="success" if success else "failure",
            tags=details.get("tags", []),
        )

        if learning.confidence >= self.config.learning_confidence_threshold:
            self._learning_records.append(learning)
            self._metrics.patterns_learned += 1
            LEARNING_PATTERNS_EXTRACTED.inc()
            LEARNING_CONFIDENCE.observe(learning.confidence)

            logger.info("Recorded learning from task %s: %s", task_id, learning.pattern_type)

    def get_applicable_learnings(self, task_type: str, platform: str) -> list[LearningRecord]:
        """Get learnings applicable to a task type/platform."""
        applicable = []
        for learning in self._learning_records:
            if learning.task_type == task_type or learning.platform == platform:
                if learning.confidence >= self.config.learning_confidence_threshold:
                    applicable.append(learning)

        # Sort by confidence and recency
        applicable.sort(key=lambda l: (l.confidence, l.last_applied or l.created_at), reverse=True)
        return applicable[:10]

    def apply_learning(self, learning_id: str) -> bool:
        """Mark a learning as applied."""
        for learning in self._learning_records:
            if learning.id == learning_id:
                learning.applied_count += 1
                learning.last_applied = datetime.now(UTC)
                self._metrics.patterns_applied += 1
                return True
        return False

    # ── System Control ───────────────────────────────────────────────

    async def start(self) -> None:
        """Start all thinking loops."""
        if self._running:
            logger.warning("ThinkingSystem already running")
            return

        self._running = True

        if self.config.mode in (ThinkingMode.DAILY_PLANNING, ThinkingMode.ALL) and self.config.planning_enabled:
            self._tasks["planning"] = asyncio.create_task(self._planning_loop())

        if self.config.mode in (ThinkingMode.RESEARCH, ThinkingMode.ALL) and self.config.research_enabled:
            self._tasks["research"] = asyncio.create_task(self._research_loop())

        if self.config.mode in (ThinkingMode.IMPROVEMENT, ThinkingMode.ALL) and self.config.improvement_enabled:
            self._tasks["improvement"] = asyncio.create_task(self._improvement_loop())

        logger.info("ThinkingSystem started with loops: %s", list(self._tasks.keys()))
        self.event_bus.publish("thinking:started", loops=list(self._tasks.keys()))

    async def stop(self) -> None:
        """Stop all thinking loops."""
        self._running = False

        for name, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        logger.info("ThinkingSystem stopped")
        self.event_bus.publish("thinking:stopped")

    # ── Status & Metrics ─────────────────────────────────────────────

    def get_metrics(self) -> ThinkingMetrics:
        return self._metrics

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "mode": self.config.mode.value,
            "active_loops": list(self._tasks.keys()),
            "metrics": {
                "planning_cycles": self._metrics.planning_cycles,
                "research_cycles": self._metrics.research_cycles,
                "improvement_cycles": self._metrics.improvement_cycles,
                "plans_created": self._metrics.plans_created,
                "topics_researched": self._metrics.topics_researched,
                "patterns_learned": self._metrics.patterns_learned,
                "patterns_applied": self._metrics.patterns_applied,
                "last_planning": self._metrics.last_planning.isoformat() if self._metrics.last_planning else None,
                "last_research": self._metrics.last_research.isoformat() if self._metrics.last_research else None,
                "last_improvement": self._metrics.last_improvement.isoformat() if self._metrics.last_improvement else None,
            },
            "state": {
                "active_goals": len(self.get_active_goals()),
                "daily_plans": len(self._daily_plans),
                "research_topics": len(self._research_topics),
                "pending_research": len([t for t in self._research_topics.values() if t.status == "pending"]),
                "learning_records": len(self._learning_records),
            },
            "config": {
                "planning_hour": self.config.planning_hour,
                "research_interval_hours": self.config.research_interval_hours,
                "improvement_interval_hours": self.config.improvement_interval_hours,
            }
        }

    async def health_check(self) -> dict[str, Any]:
        issues = []

        if not self._running:
            issues.append("System not running")

        if self.config.planning_enabled and "planning" not in self._tasks:
            issues.append("Planning loop not running")

        if self.config.research_enabled and "research" not in self._tasks:
            issues.append("Research loop not running")

        if self.config.improvement_enabled and "improvement" not in self._tasks:
            issues.append("Improvement loop not running")

        if self._metrics.errors:
            issues.append(f"{len(self._metrics.errors)} recent errors")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "status": self.get_status(),
        }


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_thinking_system: ThinkingSystem | None = None


def get_thinking_system(
    config: ThinkingConfig | None = None,
    discovery_engine: DiscoveryEngine | None = None,
    observation_engine: ObservationEngine | None = None,
) -> ThinkingSystem:
    """Get or create the global thinking system."""
    global _thinking_system
    if _thinking_system is None:
        _thinking_system = ThinkingSystem(config, discovery_engine, observation_engine)
    return _thinking_system


async def initialize_thinking_system(
    config: ThinkingConfig | None = None,
    discovery_engine: DiscoveryEngine | None = None,
    observation_engine: ObservationEngine | None = None,
) -> ThinkingSystem:
    """Initialize and start the thinking system."""
    system = get_thinking_system(config, discovery_engine, observation_engine)
    await system.start()
    return system
