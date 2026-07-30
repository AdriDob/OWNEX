"""PlatformBrowserWorkers — Playwright-based workers for AI task platforms."""

from core.automation.workers.dataannotation_worker import DataAnnotationWorker
from core.automation.workers.mindrift_browser_worker import MindriftBrowserWorker
from core.automation.workers.outlier_worker import OutlierWorker
from core.automation.workers.remotasks_worker import RemotasksWorker

__all__ = [
    "DataAnnotationWorker",
    "OutlierWorker",
    "RemotasksWorker",
    "MindriftBrowserWorker",
]


def get_browser_workers() -> dict[str, object]:
    return {
        "dataannotation": DataAnnotationWorker(),
        "outlier": OutlierWorker(),
        "remotasks": RemotasksWorker(),
        "mindrift_browser": MindriftBrowserWorker(),
    }
