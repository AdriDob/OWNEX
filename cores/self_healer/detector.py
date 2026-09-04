"""Problem Detector — Detects anomalies and system health issues."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from cores.events.event_bus import get_event_bus
from cores.health.engine import get_system_health_engine
from cores.self_healer.models import (
    HealerConfig,
    Problem,
    ProblemCategory,
    ProblemSeverity,
)

logger = logging.getLogger("ownex.self_healer.detector")

# Thresholds for anomaly detection
DEFAULT_THRESHOLDS = {
    "health_score_drop": 15.0,  # points drop in health score
    "error_rate_spike": 0.05,  # 5% error rate
    "latency_p99_increase": 2.0,  # 2x latency increase
    "test_failure_rate": 0.1,  # 10% test failure
    "memory_usage_percent": 85.0,  # 85% memory
    "cpu_usage_percent": 90.0,  # 90% CPU
    "disk_usage_percent": 90.0,  # 90% disk
    "scheduler_job_failures": 3,  # 3 consecutive failures
}


class ProblemDetector:
    """Detects system problems from health metrics, events, and logs."""

    def __init__(self, config: HealerConfig | None = None):
        self.config = config or HealerConfig()
        self.event_bus = get_event_bus()
        self.health_center = get_system_health_engine()
        self._thresholds = DEFAULT_THRESHOLDS.copy()
        self._baselines: dict[str, float] = {}
        self._last_health_score: float | None = None
        self._error_counts: dict[str, int] = defaultdict(int)
        self._last_scan: datetime | None = None
        self._scan_count = 0

        # Subscribe to relevant events
        self._subscribe_events()

    def _subscribe_events(self) -> None:
        """Subscribe to event bus for real-time anomaly detection."""
        self.event_bus.subscribe("health:score_changed", self._on_health_change)
        self.event_bus.subscribe("scheduler:job_failed", self._on_job_failure)
        self.event_bus.subscribe("api:error", self._on_api_error)
        self.event_bus.subscribe("test:failed", self._on_test_failure)

    def _on_health_change(self, **data) -> None:
        score = data.get("score", 0)
        if self._last_health_score is not None:
            drop = self._last_health_score - score
            if drop >= self._thresholds["health_score_drop"]:
                self._create_problem(
                    category=ProblemCategory.HEALTH_DEGRADATION,
                    severity=ProblemSeverity.HIGH if drop > 30 else ProblemSeverity.MEDIUM,
                    title=f"Health score dropped {drop:.1f} points",
                    description=f"Health score decreased from {self._last_health_score:.1f} to {score:.1f}",
                    metrics={"previous_score": self._last_health_score, "current_score": score, "drop": drop},
                )
        self._last_health_score = score

    def _on_job_failure(self, **data) -> None:
        job_name = data.get("job", "unknown")
        self._error_counts[f"job:{job_name}"] += 1
        if self._error_counts[f"job:{job_name}"] >= self._thresholds["scheduler_job_failures"]:
            self._create_problem(
                category=ProblemCategory.DEPENDENCY_FAILURE,
                severity=ProblemSeverity.HIGH,
                title=f"Scheduler job '{job_name}' failing repeatedly",
                description=f"Job has failed {self._error_counts[f'job:{job_name}']} times consecutively",
                metrics={"job_name": job_name, "failure_count": self._error_counts[f"job:{job_name}"]},
                affected_components=["scheduler", job_name],
            )

    def _on_api_error(self, **data) -> None:
        endpoint = data.get("endpoint", "unknown")
        self._error_counts[f"api:{endpoint}"] += 1

    def _on_test_failure(self, **data) -> None:
        test_name = data.get("test", "unknown")
        self._error_counts[f"test:{test_name}"] += 1

    def _create_problem(
        self,
        category: ProblemCategory,
        severity: ProblemSeverity,
        title: str,
        description: str,
        metrics: dict[str, Any] | None = None,
        affected_components: list[str] | None = None,
    ) -> Problem:
        problem = Problem(
            category=category,
            severity=severity,
            title=title,
            description=description,
            metrics=metrics or {},
            affected_components=affected_components or [],
        )
        logger.warning(f"[DETECTOR] Problem detected: {problem.title} ({problem.severity.value})")
        self.event_bus.publish("self_healer:problem_detected", **problem.to_dict())
        return problem

    async def scan(self) -> list[Problem]:
        """Run full system scan for problems."""
        problems = []
        self._scan_count += 1
        self._last_scan = datetime.now(UTC)

        try:
            # 1. Health Center checks
            health_problems = await self._scan_health()
            problems.extend(health_problems)

            # 2. Resource usage
            resource_problems = await self._scan_resources()
            problems.extend(resource_problems)

            # 3. Scheduler health
            scheduler_problems = await self._scan_scheduler()
            problems.extend(scheduler_problems)

            # 4. Test failures (recent)
            test_problems = await self._scan_tests()
            problems.extend(test_problems)

            # 5. Dependency health
            dep_problems = await self._scan_dependencies()
            problems.extend(dep_problems)

        except Exception as e:
            logger.error(f"[DETECTOR] Scan error: {e}")

        logger.info(f"[DETECTOR] Scan #{self._scan_count} completed: {len(problems)} problems found")
        return problems

    async def _scan_health(self) -> list[Problem]:
        problems = []
        try:
            health_summary = await self.health_center.get_health_summary()
            overall = health_summary.get("overall", {})
            score = overall.get("score", 100)

            if score < 50:
                problems.append(
                    self._create_problem(
                        category=ProblemCategory.HEALTH_DEGRADATION,
                        severity=ProblemSeverity.CRITICAL if score < 20 else ProblemSeverity.HIGH,
                        title=f"System health critical: {score:.0f}/100",
                        description=f"Overall health score is {score:.0f}/100",
                        metrics={"health_score": score, "details": overall},
                    )
                )

            # Check individual components
            for component, check in health_summary.get("checks", {}).items():
                if check.get("status") == "unhealthy":
                    problems.append(
                        self._create_problem(
                            category=ProblemCategory.HEALTH_DEGRADATION,
                            severity=ProblemSeverity.HIGH,
                            title=f"Component unhealthy: {component}",
                            description=check.get("message", "Health check failed"),
                            metrics={"component": component, "check": check},
                            affected_components=[component],
                        )
                    )
        except Exception as e:
            logger.debug(f"Health scan error: {e}")
        return problems

    async def _scan_resources(self) -> list[Problem]:
        problems = []
        try:
            import psutil

            # Memory
            mem = psutil.virtual_memory()
            if mem.percent >= self._thresholds["memory_usage_percent"]:
                problems.append(
                    self._create_problem(
                        category=ProblemCategory.RESOURCE_EXHAUSTION,
                        severity=ProblemSeverity.HIGH if mem.percent > 95 else ProblemSeverity.MEDIUM,
                        title=f"High memory usage: {mem.percent:.1f}%",
                        description=f"System memory at {mem.percent:.1f}% ({mem.used / 1e9:.1f}GB / {mem.total / 1e9:.1f}GB)",
                        metrics={"memory_percent": mem.percent, "used_gb": mem.used / 1e9, "total_gb": mem.total / 1e9},
                        affected_components=["system", "memory"],
                    )
                )

            # CPU
            cpu = psutil.cpu_percent(interval=1)
            if cpu >= self._thresholds["cpu_usage_percent"]:
                problems.append(
                    self._create_problem(
                        category=ProblemCategory.RESOURCE_EXHAUSTION,
                        severity=ProblemSeverity.HIGH if cpu > 95 else ProblemSeverity.MEDIUM,
                        title=f"High CPU usage: {cpu:.1f}%",
                        description=f"CPU usage at {cpu:.1f}%",
                        metrics={"cpu_percent": cpu},
                        affected_components=["system", "cpu"],
                    )
                )

            # Disk
            disk = psutil.disk_usage("/")
            disk_pct = (disk.used / disk.total) * 100
            if disk_pct >= self._thresholds["disk_usage_percent"]:
                problems.append(
                    self._create_problem(
                        category=ProblemCategory.RESOURCE_EXHAUSTION,
                        severity=ProblemSeverity.CRITICAL if disk_pct > 95 else ProblemSeverity.HIGH,
                        title=f"Disk space critical: {disk_pct:.1f}% used",
                        description=f"Disk usage at {disk_pct:.1f}% ({disk.free / 1e9:.1f}GB free)",
                        metrics={"disk_percent": disk_pct, "free_gb": disk.free / 1e9},
                        affected_components=["system", "disk"],
                    )
                )
        except Exception as e:
            logger.debug(f"Resource scan error: {e}")
        return problems

    async def _scan_scheduler(self) -> list[Problem]:
        problems = []
        try:
            from core.scheduler.scheduler import get_scheduler

            scheduler = get_scheduler()
            status = scheduler.get_status()

            if not status.get("running", False):
                problems.append(
                    self._create_problem(
                        category=ProblemCategory.DEPENDENCY_FAILURE,
                        severity=ProblemSeverity.CRITICAL,
                        title="Scheduler not running",
                        description="Core scheduler is stopped",
                        metrics={"scheduler_status": status},
                        affected_components=["scheduler"],
                    )
                )

            # Check for stuck jobs
            for job in status.get("jobs", []):
                if job.get("status") == "stuck":
                    problems.append(
                        self._create_problem(
                            category=ProblemCategory.DEPENDENCY_FAILURE,
                            severity=ProblemSeverity.HIGH,
                            title=f"Scheduler job stuck: {job.get('name')}",
                            description=f"Job {job.get('name')} appears to be stuck",
                            metrics={"job": job},
                            affected_components=["scheduler", job.get("name", "unknown")],
                        )
                    )
        except Exception as e:
            logger.debug(f"Scheduler scan error: {e}")
        return problems

    async def _scan_tests(self) -> list[Problem]:
        problems = []
        # Check recent test results from pytest runs
        # This would integrate with CI/test infrastructure
        return problems

    async def _scan_dependencies(self) -> list[Problem]:
        problems = []
        try:
            # Check external dependencies (APIs, databases, etc.)
            from cores.health.engine import get_health_center

            hc = get_health_center()
            summary = await hc.get_health_summary()

            for check in summary.get("checks", {}).values():
                if check.get("status") == "degraded":
                    problems.append(
                        self._create_problem(
                            category=ProblemCategory.DEPENDENCY_FAILURE,
                            severity=ProblemSeverity.MEDIUM,
                            title=f"Dependency degraded: {check.get('name', 'unknown')}",
                            description=check.get("message", "Dependency check degraded"),
                            metrics={"check": check},
                        )
                    )
        except Exception as e:
            logger.debug(f"Dependency scan error: {e}")
        return problems

    def get_status(self) -> dict[str, Any]:
        return {
            "scan_count": self._scan_count,
            "last_scan": self._last_scan.isoformat() if self._last_scan else None,
            "baselines": self._baselines,
            "error_counts": dict(self._error_counts),
            "thresholds": self._thresholds,
        }


# Singleton
_problem_detector: ProblemDetector | None = None


def get_problem_detector(config: HealerConfig | None = None) -> ProblemDetector:
    global _problem_detector
    if _problem_detector is None:
        _problem_detector = ProblemDetector(config)
    return _problem_detector
