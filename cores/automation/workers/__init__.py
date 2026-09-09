"""PlatformBrowserWorkers — Playwright-based workers for AI task platforms."""

from cores.automation.workers.dataannotation_worker import DataAnnotationWorker
from cores.automation.workers.mindrift_browser_worker import MindriftBrowserWorker
from cores.automation.workers.outlier_worker import OutlierWorker
from cores.automation.workers.remotasks_worker import RemotasksWorker

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
