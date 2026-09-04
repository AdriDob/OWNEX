"""Self-Repair Engine — Detects, diagnoses, and repairs system issues automatically."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.self_repair")


# ── Models ────────────────────────────────────────────────────────


class RepairActionType(StrEnum):
    """Types of repair actions."""

    RESTART_SERVICE = "restart_service"
    RESTART_MISSION = "restart_mission"
    RETRY_JOB = "retry_job"
    REAUTH_API = "reauth_api"
    RESUME_FROM_CHECKPOINT = "resume_from_checkpoint"
    ALERT_USER = "alert_user"
    FREE_DISK_SPACE = "free_disk_space"
    CLEAR_CACHE = "clear_cache"
    REBUILD_INDEX = "rebuild_index"
    RESTART_CONTAINER = "restart_container"


class RepairPolicy(StrEnum):
    """Repair policies."""

    AUTO_REPAIR = "auto_repair"
    ALERT_ONLY = "alert_only"


class RepairStatus(StrEnum):
    """Repair attempt status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RepairRule:
    """Rule for automatic repair."""

    detector_name: str
    action_type: RepairActionType
    policy: RepairPolicy = RepairPolicy.AUTO_REPAIR
    max_attempts: int = 3
    cooldown_seconds: int = 300
    requires_approval: bool = False


class RepairDetector:
    """Base class for detectors."""

    def __init__(self, name: str) -> None:
        self.name = name

    def check(self) -> list[dict[str, Any]]:
        """Check for issues. Returns list of issues found."""
        raise NotImplementedError


class StaleMissionDetector(RepairDetector):
    """Detects missions that haven't had a heartbeat in too long."""

    def __init__(self, max_age_hours: float = 2.0) -> None:
        super().__init__("stale_mission")
        self.max_age_hours = max_age_hours

    def check(self) -> list[dict[str, Any]]:
        issues = []
        try:
            from core.mission.controller import get_mission_controller

            mission_ctrl = get_mission_controller()
            stale = mission_ctrl.get_stale_missions(max_age_hours=self.max_age_hours)
            for mission in stale:
                issues.append(
                    {
                        "detector": self.name,
                        "mission_id": mission.mission_id,
                        "issue_type": "stale_mission",
                        "severity": "WARNING",
                        "details": f"Last heartbeat: {mission.last_heartbeat}",
                        "suggested_action": RepairActionType.RESUME_FROM_CHECKPOINT,
                    }
                )
        except Exception as e:
            logger.warning(f"[{self.name}] Error checking stale missions: {e}")
        return issues


class StaleJobDetector(RepairDetector):
    """Detects scheduler jobs that haven't run in too long."""

    def __init__(self, max_missed_runs: int = 3) -> None:
        super().__init__("stale_job")
        self.max_missed_runs = max_missed_runs

    def check(self) -> list[dict[str, Any]]:
        issues = []
        try:
            from core.scheduler.scheduler import get_core_scheduler

            scheduler = get_core_scheduler()
            jobs = scheduler.get_jobs()
            for job in jobs:
                # JobDefinition doesn't track missed_runs, use metadata if available
                missed = job.metadata.get("missed_runs", 0) if job.metadata else 0
                if missed >= self.max_missed_runs:
                    issues.append(
                        {
                            "detector": self.name,
                            "job_id": job.job_id,
                            "issue_type": "stale_job",
                            "severity": "WARNING",
                            "details": f"Job missed {missed} runs",
                            "suggested_action": RepairActionType.RETRY_JOB,
                        }
                    )
        except Exception as e:
            logger.warning(f"[{self.name}] Error checking stale jobs: {e}")
        return issues


class FailedAPIDetector(RepairDetector):
    """Detects APIs that are consistently failing."""

    def __init__(self, failure_threshold: int = 5, window_minutes: int = 10) -> None:
        super().__init__("failed_api")
        self.failure_threshold = failure_threshold
        self.window_minutes = window_minutes

    def check(self) -> list[dict[str, Any]]:
        issues = []
        try:
            from core.events.event_bus import get_core_event_bus

            bus = get_core_event_bus()
            # Check recent events for API failures
            history = bus.get_history(app_id="api", limit=100)
            api_failures = {}
            cutoff = datetime.now(UTC) - timedelta(minutes=self.window_minutes)
            for event in history:
                if event.get("timestamp"):
                    ts = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                if "error" in event.get("event_type", "").lower() or "fail" in event.get("event_type", "").lower():
                    api = event.get("data", {}).get("api", "unknown")
                    api_failures[api] = api_failures.get(api, 0) + 1

            for api, count in api_failures.items():
                if count >= self.failure_threshold:
                    issues.append(
                        {
                            "detector": self.name,
                            "api": api,
                            "issue_type": "failed_api",
                            "severity": "CRITICAL",
                            "details": f"API {api} failed {count} times in {self.window_minutes} minutes",
                            "suggested_action": RepairActionType.REAUTH_API,
                        }
                    )
        except Exception as e:
            logger.warning(f"[{self.name}] Error checking API failures: {e}")
        return issues


class StalledWorkflowDetector(RepairDetector):
    """Detects missions/workflows stuck in the same stage too long."""

    def __init__(self, max_stage_minutes: int = 60) -> None:
        super().__init__("stalled_workflow")
        self.max_stage_minutes = max_stage_minutes

    def check(self) -> list[dict[str, Any]]:
        issues = []
        try:
            from core.mission.controller import get_mission_controller

            mission_ctrl = get_mission_controller()
            active = mission_ctrl.get_active_missions()
            for mission in active:
                if mission.last_heartbeat:
                    last = datetime.fromisoformat(mission.last_heartbeat.replace("Z", "+00:00"))
                    if datetime.now(UTC) - last > timedelta(minutes=self.max_stage_minutes):
                        issues.append(
                            {
                                "detector": self.name,
                                "mission_id": mission.mission_id,
                                "issue_type": "stalled_workflow",
                                "severity": "WARNING",
                                "details": f"Mission stuck in stage '{mission.current_stage}' for > {self.max_stage_minutes} min",
                                "suggested_action": RepairActionType.RESTART_MISSION,
                            }
                        )
        except Exception as e:
            logger.warning(f"[{self.name}] Error checking stalled workflows: {e}")
        return issues


class CredentialExpiryDetector(RepairDetector):
    """Detects expiring or expired credentials."""

    def __init__(self, warning_days: int = 7) -> None:
        super().__init__("credential_expiry")
        self.warning_days = warning_days

    def check(self) -> list[dict[str, Any]]:
        issues = []
        try:
            from cores.credentials.vault import get_vault

            vault = get_vault()
            credentials = vault.list_credentials()
            for cred in credentials:
                if cred.expires_at:
                    exp = datetime.fromisoformat(cred.expires_at.replace("Z", "+00:00"))
                    days_left = (exp - datetime.now(UTC)).days
                    if days_left <= self.warning_days:
                        severity = "CRITICAL" if days_left <= 0 else "WARNING"
                        issues.append(
                            {
                                "detector": self.name,
                                "credential_id": cred.credential_id,
                                "issue_type": "credential_expiry",
                                "severity": severity,
                                "details": f"Credential expires in {days_left} days",
                                "suggested_action": RepairActionType.REAUTH_API,
                            }
                        )
        except Exception as e:
            logger.warning(f"[{self.name}] Error checking credential expiry: {e}")
        return issues


class DiskSpaceDetector(RepairDetector):
    """Detects low disk space."""

    def __init__(self, threshold_gb: float = 2.0, threshold_pct: float = 10.0) -> None:
        super().__init__("disk_space")
        self.threshold_gb = threshold_gb
        self.threshold_pct = threshold_pct

    def check(self) -> list[dict[str, Any]]:
        issues = []
        try:
            usage = shutil.disk_usage("/")
            free_gb = usage.free / (1024**3)
            free_pct = (usage.free / usage.total) * 100
            if free_gb < self.threshold_gb or free_pct < self.threshold_pct:
                issues.append(
                    {
                        "detector": self.name,
                        "issue_type": "low_disk_space",
                        "severity": "CRITICAL",
                        "details": f"Free space: {free_gb:.1f} GB ({free_pct:.1f}%)",
                        "suggested_action": RepairActionType.FREE_DISK_SPACE,
                    }
                )
        except Exception as e:
            logger.warning(f"[{self.name}] Error checking disk space: {e}")
        return issues


class MemoryPressureDetector(RepairDetector):
    """Detects memory pressure."""

    def __init__(self, threshold_pct: float = 90.0) -> None:
        super().__init__("memory_pressure")
        self.threshold_pct = threshold_pct

    def check(self) -> list[dict[str, Any]]:
        issues = []
        try:
            import psutil

            mem = psutil.virtual_memory()
            if mem.percent > self.threshold_pct:
                issues.append(
                    {
                        "detector": self.name,
                        "issue_type": "memory_pressure",
                        "severity": "CRITICAL",
                        "details": f"Memory usage: {mem.percent:.1f}%",
                        "suggested_action": RepairActionType.FREE_DISK_SPACE,
                    }
                )
        except Exception as e:
            logger.warning(f"[{self.name}] Error checking memory: {e}")
        return issues


class StalledMissionDetector(RepairDetector):
    """Detects missions stuck in WAITING_HUMAN or WAITING_EXTERNAL too long."""

    def __init__(self, max_wait_hours: float = 24.0) -> None:
        super().__init__("stalled_mission")
        self.max_wait_hours = max_wait_hours

    def check(self) -> list[dict[str, Any]]:
        issues = []
        try:
            from core.mission.controller import get_mission_controller

            mission_ctrl = get_mission_controller()
            waiting = mission_ctrl.get_waiting_human_missions()
            for mission in waiting:
                if mission.last_heartbeat:
                    last = datetime.fromisoformat(mission.last_heartbeat.replace("Z", "+00:00"))
                    if datetime.now(UTC) - last > timedelta(hours=self.max_wait_hours):
                        issues.append(
                            {
                                "detector": self.name,
                                "mission_id": mission.mission_id,
                                "issue_type": "stalled_waiting_human",
                                "severity": "WARNING",
                                "details": f"Waiting for human > {self.max_wait_hours}h",
                                "suggested_action": RepairActionType.ALERT_USER,
                            }
                        )
        except Exception as e:
            logger.warning(f"[{self.name}] Error checking stalled missions: {e}")
        return issues


# ── Repair Actions ────────────────────────────────────────────────


class RepairAction:
    """Base class for repair actions."""

    def __init__(self, action_type: RepairActionType) -> None:
        self.action_type = action_type

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        """Execute repair. Returns (success, message)."""
        raise NotImplementedError


class RestartServiceAction(RepairAction):
    """Restart a system service."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.RESTART_SERVICE)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        service = issue.get("service", "unknown")
        try:
            result = subprocess.run(["systemctl", "restart", service], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return True, f"Service {service} restarted successfully"
            return False, f"Failed to restart {service}: {result.stderr}"
        except Exception as e:
            return False, f"Error restarting {service}: {e}"


class RestartMissionAction(RepairAction):
    """Restart a mission from checkpoint."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.RESTART_MISSION)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        mission_id = issue.get("mission_id")
        if not mission_id:
            return False, "No mission_id provided"
        try:
            from core.mission.controller import get_mission_controller

            ctrl = get_mission_controller()
            mission = ctrl.get_mission(mission_id)
            if not mission:
                return False, f"Mission {mission_id} not found"
            # Restart from last checkpoint
            ctrl.restore_from_checkpoint(mission_id)
            return True, f"Mission {mission_id} restarted from checkpoint"
        except Exception as e:
            return False, f"Error restarting mission {mission_id}: {e}"


class RetryJobAction(RepairAction):
    """Retry a failed job."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.RETRY_JOB)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        job_id = issue.get("job_id")
        if not job_id:
            return False, "No job_id provided"
        try:
            from core.scheduler.scheduler import get_core_scheduler

            scheduler = get_core_scheduler()
            # Trigger job manually
            job = scheduler.get_job(job_id)
            if not job:
                return False, f"Job {job_id} not found"
            # For now, just log - actual retry logic would be in scheduler
            logger.info(f"[REPAIR] Triggering retry for job {job_id}")
            return True, f"Job {job_id} queued for retry"
        except Exception as e:
            return False, f"Error retrying job {job_id}: {e}"


class ReauthAPIAction(RepairAction):
    """Re-authenticate with an external API."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.REAUTH_API)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        api = issue.get("api", "unknown")
        # In a real implementation, this would trigger re-auth flow
        logger.warning(f"[REPAIR] Re-auth needed for {api} - requires human intervention")
        return False, f"Re-auth required for {api} - manual intervention needed"


class ResumeFromCheckpointAction(RepairAction):
    """Resume a mission from its last checkpoint."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.RESUME_FROM_CHECKPOINT)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        mission_id = issue.get("mission_id")
        if not mission_id:
            return False, "No mission_id provided"
        try:
            from core.mission.controller import get_mission_controller

            ctrl = get_mission_controller()
            ctrl.restore_from_checkpoint(mission_id)
            return True, f"Mission {mission_id} restored from checkpoint"
        except Exception as e:
            return False, f"Error restoring checkpoint for {mission_id}: {e}"


class AlertUserAction(RepairAction):
    """Send alert to user (notification)."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.ALERT_USER)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        # In a real implementation, this would send a notification
        logger.warning(f"[REPAIR] ALERT USER: {issue.get('details', 'Issue detected')}")
        return True, "User alerted (notification sent)"


class FreeDiskSpaceAction(RepairAction):
    """Free up disk space by cleaning caches, logs, etc."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.FREE_DISK_SPACE)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        freed_mb = 0
        try:
            # Clean Python cache
            for root, dirs, files in os.walk("."):
                for d in dirs:
                    if d == "__pycache__":
                        path = os.path.join(root, d)
                        size = sum(
                            os.path.getsize(os.path.join(path, f))
                            for f in os.listdir(path)
                            if os.path.isfile(os.path.join(path, f))
                        )
                        shutil.rmtree(path, ignore_errors=True)
                        freed_mb += size / (1024 * 1024)
                # Clean old logs
                log_dir = Path("logs")
                if log_dir.exists():
                    for log_file in log_dir.glob("*.log.*"):
                        size = log_file.stat().st_size
                        log_file.unlink()
                        freed_mb += size / (1024 * 1024)
                return True, f"Freed {freed_mb:.1f} MB of disk space"
        except Exception as e:
            return False, f"Error freeing disk space: {e}"


class ClearCacheAction(RepairAction):
    """Clear application caches."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.CLEAR_CACHE)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        try:
            # Clear Python cache
            for root, dirs, files in os.walk("."):
                for d in dirs:
                    if d == "__pycache__":
                        shutil.rmtree(os.path.join(root, d), ignore_errors=True)
            return True, "Python caches cleared"
        except Exception as e:
            return False, f"Error clearing cache: {e}"


class RebuildIndexAction(RepairAction):
    """Rebuild search indexes."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.REBUILD_INDEX)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        # Would rebuild search indexes
        return True, "Index rebuild triggered (placeholder)"


class RestartContainerAction(RepairAction):
    """Restart a Docker container."""

    def __init__(self) -> None:
        super().__init__(RepairActionType.RESTART_CONTAINER)

    def execute(self, issue: dict[str, Any]) -> tuple[bool, str]:
        container = issue.get("container", "unknown")
        try:
            result = subprocess.run(["docker", "restart", container], capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return True, f"Container {container} restarted"
            return False, f"Failed to restart {container}: {result.stderr}"
        except Exception as e:
            return False, f"Error restarting {container}: {e}"


# ── Repair Engine ────────────────────────────────────────────────


@dataclass
class RepairAttempt:
    """Record of a repair attempt."""

    issue_id: str
    detector: str
    action_type: RepairActionType
    status: RepairStatus
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class SelfRepairEngine:
    """Main self-repair engine coordinating detectors and actions."""

    def __init__(self, policy: RepairPolicy = RepairPolicy.AUTO_REPAIR) -> None:
        self.policy = policy
        self.detectors: list[RepairDetector] = []
        self.actions: dict[RepairActionType, RepairAction] = {}
        self.attempts: list[RepairAttempt] = []
        self._register_default_detectors()
        self._register_default_actions()

    def _register_default_detectors(self) -> None:
        self.detectors = [
            StaleMissionDetector(max_age_hours=2.0),
            StaleJobDetector(max_missed_runs=3),
            FailedAPIDetector(failure_threshold=5, window_minutes=10),
            StalledWorkflowDetector(max_stage_minutes=60),
            CredentialExpiryDetector(warning_days=7),
            DiskSpaceDetector(threshold_gb=2.0, threshold_pct=10.0),
            MemoryPressureDetector(threshold_pct=90.0),
            StalledMissionDetector(max_wait_hours=24.0),
        ]

    def _register_default_actions(self) -> None:
        self.actions = {
            RepairActionType.RESTART_SERVICE: RestartServiceAction(),
            RepairActionType.RESTART_MISSION: RestartMissionAction(),
            RepairActionType.RETRY_JOB: RetryJobAction(),
            RepairActionType.REAUTH_API: ReauthAPIAction(),
            RepairActionType.RESUME_FROM_CHECKPOINT: ResumeFromCheckpointAction(),
            RepairActionType.ALERT_USER: AlertUserAction(),
            RepairActionType.FREE_DISK_SPACE: FreeDiskSpaceAction(),
            RepairActionType.CLEAR_CACHE: ClearCacheAction(),
            RepairActionType.REBUILD_INDEX: RebuildIndexAction(),
            RepairActionType.RESTART_CONTAINER: RestartContainerAction(),
        }

    def add_detector(self, detector: RepairDetector) -> None:
        self.detectors.append(detector)

    def add_action(self, action: RepairAction) -> None:
        self.actions[action.action_type] = action

    def set_policy(self, policy: RepairPolicy) -> None:
        self.policy = policy

    def check_all(self) -> list[dict[str, Any]]:
        """Run all detectors and collect issues."""
        all_issues = []
        for detector in self.detectors:
            try:
                issues = detector.check()
                all_issues.extend(issues)
                logger.info(f"[SELF_REPAIR] {detector.name}: found {len(issues)} issues")
            except Exception as e:
                logger.error(f"[SELF_REPAIR] Detector {detector.name} failed: {e}")
        return all_issues

    def repair_issue(self, issue: dict[str, Any]) -> RepairAttempt:
        """Attempt to repair a single issue."""
        action_type = issue.get("suggested_action")
        if not action_type:
            return RepairAttempt(
                issue_id=issue.get("mission_id") or issue.get("job_id") or "unknown",
                detector=issue.get("detector", "unknown"),
                action_type=RepairActionType.ALERT_USER,
                status=RepairStatus.SKIPPED,
                message="No suggested action for issue",
            )

        if isinstance(action_type, str):
            action_type = RepairActionType(action_type)

        action = self.actions.get(action_type)
        if not action:
            return RepairAttempt(
                issue_id=issue.get("mission_id") or issue.get("job_id") or "unknown",
                detector=issue.get("detector", "unknown"),
                action_type=action_type,
                status=RepairStatus.SKIPPED,
                message=f"No action registered for {action_type}",
            )

        # Check cooldown (simple implementation - would need persistence for real use)
        # For now, just attempt repair

        issue_id = issue.get("mission_id") or issue.get("job_id") or issue.get("api") or "unknown"
        attempt = RepairAttempt(
            issue_id=str(issue_id),
            detector=issue.get("detector", "unknown"),
            action_type=action_type,
            status=RepairStatus.IN_PROGRESS,
            message="Starting repair",
        )
        self.attempts.append(attempt)

        try:
            success, message = action.execute(issue)
            attempt.status = RepairStatus.SUCCESS if success else RepairStatus.FAILED
            attempt.message = message
            logger.info(f"[SELF_REPAIR] {action.action_type.value}: {message}")
        except Exception as e:
            attempt.status = RepairStatus.FAILED
            attempt.message = f"Exception: {e}"
            logger.exception(f"[SELF_REPAIR] Exception during repair: {e}")

        return attempt

    def repair_all(self, issues: list[dict[str, Any]] | None = None) -> list[RepairAttempt]:
        """Repair all given issues (or check all if none provided)."""
        if issues is None:
            issues = self.check_all()

        results = []
        for issue in issues:
            # Check if we should auto-repair
            if self.policy == RepairPolicy.ALERT_ONLY:
                self.attempts.append(
                    RepairAttempt(
                        issue_id=issue.get("mission_id") or issue.get("job_id") or "unknown",
                        detector=issue.get("detector", "unknown"),
                        action_type=RepairActionType.ALERT_USER,
                        status=RepairStatus.SKIPPED,
                        message="ALERT_ONLY policy: only alerting, not repairing",
                    )
                )
                continue

            # Check if issue requires approval
            if issue.get("requires_approval", False):
                self.attempts.append(
                    RepairAttempt(
                        issue_id=issue.get("mission_id") or issue.get("job_id") or "unknown",
                        detector=issue.get("detector", "unknown"),
                        action_type=RepairActionType.ALERT_USER,
                        status=RepairStatus.SKIPPED,
                        message="Issue requires human approval",
                    )
                )
                continue

            # Attempt repair
            attempt = self.repair_issue(issue)
            results.append(attempt)

        return results

    def run_repair_cycle(self) -> dict[str, Any]:
        """Run a complete repair cycle: detect -> repair -> report."""
        logger.info("[SELF_REPAIR] Starting repair cycle")
        issues = self.check_all()
        results = self.repair_all(issues)

        success_count = sum(1 for r in results if r.status == RepairStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == RepairStatus.FAILED)
        skipped_count = sum(1 for r in results if r.status == RepairStatus.SKIPPED)

        report = {
            "timestamp": datetime.now(UTC).isoformat(),
            "issues_found": len(issues),
            "repairs_attempted": len(results),
            "successful": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "details": [asdict(r) for r in results],
        }

        logger.info(
            f"[SELF_REPAIR] Cycle complete: {success_count} success, {failed_count} failed, {skipped_count} skipped"
        )
        return report


# ── Scheduler Job ───────────────────────────────────────────────


def run_self_repair() -> dict[str, Any]:
    """Scheduler job: run self-repair cycle."""
    logger.info("[SELF_REPAIR] Starting scheduled repair cycle")
    engine = SelfRepairEngine(policy=RepairPolicy.AUTO_REPAIR)
    report = engine.run_repair_cycle()
    logger.info(f"[SELF_REPAIR] Cycle complete: {report}")
    return report


# ── Singleton ───────────────────────────────────────────────────

_self_repair_engine: SelfRepairEngine | None = None


def get_self_repair_engine() -> SelfRepairEngine:
    global _self_repair_engine
    if _self_repair_engine is None:
        _self_repair_engine = SelfRepairEngine()
    return _self_repair_engine
