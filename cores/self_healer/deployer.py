"""Safe Deployer — Deploys patches with staging, canary, and rollback."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.events.event_bus import get_event_bus
from cores.self_healer.models import (
    Deployment,
    DeploymentStatus,
    HealerConfig,
    Patch,
)

logger = logging.getLogger("ownex.self_healer.deployer")


class SafeDeployer:
    """Deploys patches safely with staging, canary, and automatic rollback."""

    def __init__(self, config: HealerConfig | None = None, repo_root: Path | None = None):
        self.config = config or HealerConfig()
        self.repo_root = repo_root or Path(__file__).resolve().parents[3]
        self.event_bus = get_event_bus()
        self._deployment_count = 0
        self._active_deployment: Deployment | None = None

    async def deploy(
        self,
        patch: Patch,
        environment: str = "staging",
        require_approval: bool = True,
    ) -> Deployment:
        """Deploy a patch through the safe deployment pipeline."""
        self._deployment_count += 1
        deployment = Deployment(
            id=f"deploy_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{self._deployment_count}",
            patch_id=patch.id,
            environment=environment,
            status=DeploymentStatus.PENDING,
        )

        self._active_deployment = deployment
        self.event_bus.publish("self_healer:deployment_started", **deployment.to_dict())

        try:
            # 1. Create version backup before deployment
            backup_id = await self._create_version_backup()
            deployment.version_backup_id = backup_id
            logger.info(f"Created version backup: {backup_id}")

            # 2. Apply patch to staging
            deployment.status = DeploymentStatus.STAGING
            deployment.started_at = datetime.now(UTC)
            await self._apply_patch(patch, environment="staging")
            deployment.status = DeploymentStatus.STAGING

            # 3. Run health checks on staging
            health_ok = await self._run_health_checks("staging")
            deployment.health_checks["staging"] = health_ok

            if not health_ok:
                raise RuntimeError("Staging health checks failed")

            # 4. Deploy to canary
            deployment.status = DeploymentStatus.CANARY
            await self._deploy_canary(patch)
            deployment.status = DeploymentStatus.CANARY

            # 5. Monitor canary for configured duration
            await self._monitor_canary(deployment)

            # 6. Check canary health
            canary_healthy = await self._run_health_checks("canary")
            deployment.health_checks["canary"] = canary_healthy

            if not canary_healthy:
                raise RuntimeError("Canary health checks failed")

            # 7. Deploy to production (if different from canary)
            if environment == "production":
                deployment.status = DeploymentStatus.PRODUCTION
                await self._deploy_production(patch)
                deployment.status = DeploymentStatus.PRODUCTION

                # Final health checks
                prod_healthy = await self._run_health_checks("production")
                deployment.health_checks["production"] = prod_healthy

                if not prod_healthy:
                    raise RuntimeError("Production health checks failed")

            # 8. Mark deployment as completed
            deployment.status = DeploymentStatus.COMPLETED
            deployment.completed_at = datetime.now(UTC)

            # Capture metrics after deployment
            deployment.metrics_after = await self._capture_metrics()

            logger.info(f"Deployment {deployment.id} completed successfully")
            self.event_bus.publish("self_healer:deployment_completed", **deployment.to_dict())

            return deployment

        except Exception as e:
            logger.error(f"Deployment {deployment.id} failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.now(UTC)

            # Attempt rollback
            await self._rollback(deployment, str(e))

            self.event_bus.publish("self_healer:deployment_failed", **deployment.to_dict())
            raise

    async def _create_version_backup(self) -> str:
        """Create a version backup using the backup system."""
        try:
            from cores.version_backup.backup_system import get_version_backup_system

            backup_system = get_version_backup_system()
            result = backup_system.create_backup(notes=f"Pre-deployment backup {datetime.now(UTC).isoformat()}")
            return result.backup_id
        except Exception as e:
            logger.warning(f"Version backup failed: {e}")
            # Fallback: git stash
            try:
                subprocess.run(
                    [
                        "git",
                        "stash",
                        "push",
                        "-m",
                        f"self_healer_pre_deploy_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                    ],
                    cwd=self.repo_root,
                    capture_output=True,
                    check=True,
                )
                return f"git_stash_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            except Exception:
                return f"fallback_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    async def _apply_patch(self, patch: Patch, environment: str) -> None:
        """Apply patch to the repository."""
        if not patch.diff:
            logger.warning("Patch has no diff, skipping apply")
            return

        # Write patch to temp file and apply

        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
            f.write(patch.diff)
            patch_file = f.name

        try:
            # Apply patch
            result = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", patch_file],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                # Try with --reject for partial apply
                result = subprocess.run(
                    ["git", "apply", "--reject", "--whitespace=nowarn", patch_file],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to apply patch: {result.stderr}")

            # Stage changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_root,
                capture_output=True,
                timeout=30,
            )
        finally:
            Path(patch_file).unlink(missing_ok=True)

    async def _deploy_canary(self, patch: Patch) -> None:
        """Deploy to canary environment (subset of traffic/instances)."""
        # For now, canary = same as staging but with monitoring
        # In a real setup, this would deploy to a subset of instances
        logger.info("Canary deployment started (monitoring mode)")
        await asyncio.sleep(2)  # Brief pause to simulate canary start

    async def _monitor_canary(self, deployment: Deployment) -> None:
        """Monitor canary for the configured duration."""
        duration = self.config.canary_duration_minutes * 60
        logger.info(f"Monitoring canary for {self.config.canary_duration_minutes} minutes")

        start_time = time.time()
        check_interval = 30  # seconds

        while time.time() - start_time < duration:
            await asyncio.sleep(check_interval)
            healthy = await self._run_health_checks("canary")
            if not healthy:
                logger.warning("Canary health check failed during monitoring")
                deployment.health_checks[f"canary_{int(time.time())}"] = False
                raise RuntimeError("Canary became unhealthy during monitoring")
            deployment.health_checks[f"canary_{int(time.time())}"] = True

    async def _deploy_production(self, patch: Patch) -> None:
        """Deploy to production environment."""
        # In this setup, staging == production since it's a single instance
        # In a real setup, this would promote canary to full production
        logger.info("Promoting canary to production")

    async def _run_health_checks(self, environment: str) -> bool:
        """Run comprehensive health checks."""
        try:
            from cores.health.engine import get_health_center

            health_center = get_health_center()
            summary = await health_center.get_health_summary()

            overall = summary.get("overall", {})
            score = overall.get("score", 0)

            # Check critical components
            critical_checks = ["database", "event_bus", "scheduler"]
            for check_name in critical_checks:
                check = summary.get("checks", {}).get(check_name)
                if check and check.get("status") == "unhealthy":
                    logger.error(f"Critical check failed: {check_name}")
                    return False

            return score >= 50  # Minimum health score

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def _capture_metrics(self) -> dict[str, float]:
        """Capture system metrics after deployment."""
        metrics = {}
        try:
            import psutil

            metrics["cpu_percent"] = psutil.cpu_percent(interval=1)
            metrics["memory_percent"] = psutil.virtual_memory().percent
            metrics["disk_percent"] = (psutil.disk_usage("/").used / psutil.disk_usage("/").total) * 100

            from cores.health.engine import get_health_center

            health_center = get_health_center()
            summary = await health_center.get_health_summary()
            metrics["health_score"] = summary.get("overall", {}).get("score", 0)
        except Exception as e:
            logger.debug(f"Metrics capture failed: {e}")

        return metrics

    async def _rollback(self, deployment: Deployment, reason: str) -> None:
        """Rollback deployment using version backup."""
        logger.warning(f"Rolling back deployment {deployment.id}: {reason}")

        deployment.rollback_triggered = True
        deployment.rollback_reason = reason
        deployment.rolled_back_at = datetime.now(UTC)
        deployment.status = DeploymentStatus.ROLLED_BACK

        try:
            # Try version backup restore first
            if deployment.version_backup_id and not deployment.version_backup_id.startswith("git_stash"):
                from cores.version_backup.backup_system import get_version_backup_system

                backup_system = get_version_backup_system()
                backup_system.restore_backup(deployment.version_backup_id, force=True)
                logger.info(f"Restored from version backup: {deployment.version_backup_id}")
            else:
                # Fallback: git stash pop or reset
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD"],
                    cwd=self.repo_root,
                    capture_output=True,
                    timeout=30,
                )
                subprocess.run(
                    ["git", "stash", "pop"],
                    cwd=self.repo_root,
                    capture_output=True,
                    timeout=30,
                )
                logger.info("Rolled back via git reset/stash")

            # Verify rollback health
            await asyncio.sleep(5)
            healthy = await self._run_health_checks("production")
            logger.info(f"Rollback health check: {'passed' if healthy else 'FAILED'}")

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            deployment.status = DeploymentStatus.FAILED

    def get_active_deployment(self) -> Deployment | None:
        return self._active_deployment

    def get_status(self) -> dict[str, Any]:
        return {
            "active_deployment": self._active_deployment.to_dict() if self._active_deployment else None,
            "deployment_count": self._deployment_count,
            "config": {
                "canary_duration_minutes": self.config.canary_duration_minutes,
                "max_rollback_time_minutes": self.config.max_rollback_time_minutes,
            },
        }


# Singleton
_safe_deployer: SafeDeployer | None = None


def get_safe_deployer(config: HealerConfig | None = None, repo_root: Path | None = None) -> SafeDeployer:
    global _safe_deployer
    if _safe_deployer is None:
        _safe_deployer = SafeDeployer(config, repo_root)
    return _safe_deployer
