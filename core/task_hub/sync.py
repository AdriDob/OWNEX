"""Task Hub Sync — Connect accounts and sync tasks from all platforms."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.task_hub.models import PlatformConnection, TaskStatus, UnifiedTask

logger = logging.getLogger("ownex.task_hub.sync")


class TaskSync:
    """Sync tasks from all connected platforms."""

    def __init__(self):
        self._connections: dict[str, PlatformConnection] = {}
        self._tasks: dict[str, UnifiedTask] = {}

    async def sync_platform(self, platform: str) -> PlatformConnection:
        """Sync tasks from a specific platform."""
        logger.info(f"[TASK_HUB] Syncing tasks from {platform}")

        try:
            if platform == "algora":
                return await self._sync_algora()
            elif platform == "freelancer":
                return await self._sync_freelancer()
            elif platform == "github":
                return await self._sync_github()
            elif platform == "outlier":
                return await self._sync_outlier()
            else:
                return PlatformConnection(
                    platform=platform,
                    connected=False,
                    error=f"Platform {platform} not supported for sync",
                )
        except Exception as e:
            logger.error(f"[TASK_HUB] Failed to sync {platform}: {e}")
            return PlatformConnection(
                platform=platform,
                connected=False,
                error=str(e),
            )

    async def _sync_algora(self) -> PlatformConnection:
        """Sync tasks from Algora."""
        creds = get_platform_credentials("algora")
        if not creds.get("api_key"):
            return PlatformConnection(
                platform="algora",
                connected=False,
                error="API key not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                # Fetch bounties (actual API call would go here)
                # For now, simulate with mock data
                mock_tasks = [
                    UnifiedTask(
                        id="algora_123",
                        platform="algora",
                        platform_id="123",
                        title="Fix authentication bug",
                        description="Implement OAuth2 flow",
                        status=TaskStatus.PENDING,
                        priority=TaskPriority.HIGH,
                        reward=500.0,
                        estimated_hours=8.0,
                        platform_url="https://algora.io/bounties/123",
                    ),
                    UnifiedTask(
                        id="algora_456",
                        platform="algora",
                        platform_id="456",
                        title="Add dark mode",
                        description="Implement dark mode UI",
                        status=TaskStatus.PENDING,
                        priority=TaskPriority.MEDIUM,
                        reward=300.0,
                        estimated_hours=4.0,
                        platform_url="https://algora.io/bounties/456",
                    ),
                ]

                for task in mock_tasks:
                    self._tasks[task.id] = task

                return PlatformConnection(
                    platform="algora",
                    connected=True,
                    last_sync=datetime.now(UTC).isoformat(),
                    total_tasks=len(mock_tasks),
                    pending_tasks=len(mock_tasks),
                )
        except Exception as e:
            return PlatformConnection(
                platform="algora",
                connected=False,
                error=str(e),
            )

    async def _sync_freelancer(self) -> PlatformConnection:
        """Sync tasks from Freelancer."""
        creds = get_platform_credentials("freelancer")
        if not creds.get("api_key"):
            return PlatformConnection(
                platform="freelancer",
                connected=False,
                error="API key not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                # Fetch projects (actual API call would go here)
                mock_tasks = [
                    UnifiedTask(
                        id="freelancer_789",
                        platform="freelancer",
                        platform_id="789",
                        title="Build React dashboard",
                        description="Create dashboard with charts",
                        status=TaskStatus.PENDING,
                        priority=TaskPriority.HIGH,
                        reward=1500.0,
                        estimated_hours=40.0,
                        platform_url="https://freelancer.com/projects/789",
                    ),
                ]

                for task in mock_tasks:
                    self._tasks[task.id] = task

                return PlatformConnection(
                    platform="freelancer",
                    connected=True,
                    last_sync=datetime.now(UTC).isoformat(),
                    total_tasks=len(mock_tasks),
                    pending_tasks=len(mock_tasks),
                )
        except Exception as e:
            return PlatformConnection(
                platform="freelancer",
                connected=False,
                error=str(e),
            )

    async def _sync_github(self) -> PlatformConnection:
        """Sync tasks from GitHub (issues/PRs)."""
        creds = get_platform_credentials("github")
        if not creds.get("token"):
            return PlatformConnection(
                platform="github",
                connected=False,
                error="Token not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"token {creds['token']}"}

                # Fetch issues from watched repos (actual API call would go here)
                mock_tasks = [
                    UnifiedTask(
                        id="github_abc",
                        platform="github",
                        platform_id="abc",
                        title="Fix memory leak",
                        description="Memory leak in component X",
                        status=TaskStatus.PENDING,
                        priority=TaskPriority.URGENT,
                        reward=0.0,  # GitHub issues don't have direct reward
                        estimated_hours=12.0,
                        platform_url="https://github.com/user/repo/issues/abc",
                    ),
                ]

                for task in mock_tasks:
                    self._tasks[task.id] = task

                return PlatformConnection(
                    platform="github",
                    connected=True,
                    last_sync=datetime.now(UTC).isoformat(),
                    total_tasks=len(mock_tasks),
                    pending_tasks=len(mock_tasks),
                )
        except Exception as e:
            return PlatformConnection(
                platform="github",
                connected=False,
                error=str(e),
            )

    async def _sync_outlier(self) -> PlatformConnection:
        """Sync tasks from Outlier."""
        creds = get_platform_credentials("outlier")
        if not creds.get("api_key"):
            return PlatformConnection(
                platform="outlier",
                connected=False,
                error="API key not configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                # Fetch jobs (actual API call would go here)
                mock_tasks = [
                    UnifiedTask(
                        id="outlier_def",
                        platform="outlier",
                        platform_id="def",
                        title="Label training data",
                        description="Label 1000 images",
                        status=TaskStatus.PENDING,
                        priority=TaskPriority.MEDIUM,
                        reward=50.0,
                        estimated_hours=2.0,
                        platform_url="https://platform.outlier.ai/jobs/def",
                    ),
                ]

                for task in mock_tasks:
                    self._tasks[task.id] = task

                return PlatformConnection(
                    platform="outlier",
                    connected=True,
                    last_sync=datetime.now(UTC).isoformat(),
                    total_tasks=len(mock_tasks),
                    pending_tasks=len(mock_tasks),
                )
        except Exception as e:
            return PlatformConnection(
                platform="outlier",
                connected=False,
                error=str(e),
            )

    async def sync_all(self) -> dict[str, PlatformConnection]:
        """Sync all platforms."""
        platforms = ["algora", "freelancer", "github", "outlier"]
        results = {}

        for platform in platforms:
            results[platform] = await self.sync_platform(platform)

        return results

    def get_all_tasks(self, status: TaskStatus | None = None) -> list[UnifiedTask]:
        """Get all tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_task(self, task_id: str) -> UnifiedTask | None:
        """Get a specific task by ID."""
        return self._tasks.get(task_id)

    def update_task_status(self, task_id: str, new_status: TaskStatus) -> bool:
        """Update task status."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = new_status
        task.updated_at = datetime.now(UTC).isoformat()
        return True

    def get_connections(self) -> dict[str, PlatformConnection]:
        """Get all platform connections."""
        return self._connections


_sync_instance: TaskSync | None = None


def get_task_sync() -> TaskSync:
    """Get singleton TaskSync instance."""
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = TaskSync()
    return _sync_instance
