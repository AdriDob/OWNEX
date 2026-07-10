from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class JobDefinition:
    """A job registered by an app plugin."""

    def __init__(
        self,
        job_id: str,
        app_id: str,
        handler: Callable[..., Any],
        trigger: str = "interval",
        seconds: int = 3600,
        **kwargs: Any,
    ) -> None:
        self.job_id = job_id
        self.app_id = app_id
        self.handler = handler
        self.trigger = trigger
        self.seconds = seconds
        self.kwargs = kwargs


class IScheduler(ABC):
    """Pluggable scheduler — Core orchestrates, apps execute via events."""

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    @abstractmethod
    def add_job(self, job: JobDefinition) -> str:
        """Register a job. Returns job_id."""

    @abstractmethod
    def remove_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    def get_jobs(self, app_id: str | None = None) -> list[JobDefinition]:
        ...

    @abstractmethod
    def pause_job(self, job_id: str) -> bool:
        ...

    @abstractmethod
    def resume_job(self, job_id: str) -> bool:
        ...
